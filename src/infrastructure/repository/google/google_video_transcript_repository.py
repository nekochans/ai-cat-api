import os
import json
import base64
import tempfile
import ffmpeg
import time
from pathlib import Path
from google.cloud import storage, speech
from google.oauth2 import service_account
from google.api_core import exceptions as google_exceptions
from domain.repository.video_transcript_repository_interface import (
    CreateVideoTranscriptDto,
    CreateVideoTranscriptResult,
    VideoTranscriptRepositoryInterface,
)
from log.logger import AppLogger, InfoLogExtra
from infrastructure.google.parse_gcs_path import parse_gcs_path


class GoogleVideoTranscriptRepository(VideoTranscriptRepositoryInterface):
    def __init__(self) -> None:
        app_logger = AppLogger()
        self.logger = app_logger.logger

        encoded_service_account_key = os.getenv("GOOGLE_CLOUD_CREDENTIALS")
        if encoded_service_account_key is None:
            raise Exception("GOOGLE_CLOUD_CREDENTIALS is not set.")

        decoded_service_account_key = base64.b64decode(
            encoded_service_account_key
        ).decode("utf-8")
        service_account_info = json.loads(decoded_service_account_key)

        self.google_cloud_storage_client = storage.Client.from_service_account_info(
            service_account_info
        )

        self.credentials = service_account.Credentials.from_service_account_info(
            # service_account_info の型チェックは難しいので type: ignore で回避している
            service_account_info  # type: ignore
        )

        self.speech_client = speech.SpeechClient(credentials=self.credentials)

    def extract_audio_and_transcribe(self, video_uri: str) -> str:
        gcs_path_components = parse_gcs_path(video_uri)
        bucket = self.google_cloud_storage_client.bucket(
            gcs_path_components["bucket_name"]
        )

        with tempfile.NamedTemporaryFile(
            suffix=".mov"
        ) as video_temp, tempfile.NamedTemporaryFile(suffix=".wav") as audio_temp:
            file_path = video_uri.replace(
                f"gs://{gcs_path_components['bucket_name']}/", ""
            )
            blob = bucket.blob(file_path)
            blob.download_to_filename(video_temp.name)

            self.logger.info(
                "GoogleVideoTranscriptRepository.extract_audio_and_transcribe.DownloadedVideo",
                extra=InfoLogExtra(
                    info_message=f"Downloaded {file_path} to {video_temp.name}",
                ),
            )

            try:
                (
                    ffmpeg.input(video_temp.name)
                    .output(audio_temp.name, acodec="pcm_s16le", ac=1, ar="16000")
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True)
                )
            except ffmpeg.Error as e:
                self.logger.error(
                    "GoogleVideoTranscriptRepository.extract_audio_and_transcribe.FFmpegError",
                    extra=InfoLogExtra(
                        info_message=f"FFmpeg error: {str(e)}",
                    ),
                )
                raise

            self.logger.info(
                "GoogleVideoTranscriptRepository.extract_audio_and_transcribe.ExtractedAudio",
                extra=InfoLogExtra(
                    info_message=f"Extracted audio to {audio_temp.name}",
                ),
            )

            audio_file_path = Path(file_path)
            audio_file_name = audio_file_path.stem + ".wav"
            audio_file_path = audio_file_path.parent / audio_file_name

            audio_blob = bucket.blob(str(audio_file_path))
            audio_blob.upload_from_filename(audio_temp.name)

            self.logger.info(
                "GoogleVideoTranscriptRepository.extract_audio_and_transcribe.UploadedExtractedAudio",
                extra=InfoLogExtra(
                    info_message=f"Uploaded extracted audio to gs://{gcs_path_components['bucket_name']}/{audio_file_path}",
                ),
            )

            # Transcribe the audio
            audio = speech.RecognitionAudio(
                uri=f"gs://{gcs_path_components['bucket_name']}/{audio_file_path}"
            )
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                language_code="ja-JP",
            )

            try:
                operation = self.speech_client.long_running_recognize(
                    config=config, audio=audio
                )

                # Increase timeout to 10 minutes (600 seconds)
                timeout = 600
                start_time = time.time()

                while True:
                    if operation.done():
                        break
                    if time.time() - start_time > timeout:
                        raise TimeoutError(
                            f"Transcription operation timed out after {timeout} seconds"
                        )
                    time.sleep(10)  # Poll every 10 seconds

                response = operation.result()

                transcript = ""
                for result in response.results:
                    transcript += result.alternatives[0].transcript + " "

                self.logger.info(
                    "GoogleVideoTranscriptRepository.extract_audio_and_transcribe.TranscriptionComplete",
                    extra=InfoLogExtra(
                        info_message=f"Transcription completed for {file_path}",
                    ),
                )

                return transcript.strip()

            except (google_exceptions.GoogleAPICallError, TimeoutError) as e:
                self.logger.error(
                    "GoogleVideoTranscriptRepository.extract_audio_and_transcribe.TranscriptionError",
                    extra=InfoLogExtra(
                        info_message=f"Transcription error: {str(e)}",
                    ),
                )
                raise

    async def create_video_transcript(
        self, dto: CreateVideoTranscriptDto
    ) -> CreateVideoTranscriptResult:
        try:
            transcript = self.extract_audio_and_transcribe(dto["video_url"])
        except TimeoutError as e:
            self.logger.error(
                "GoogleVideoTranscriptRepository.create_video_transcript.TimeoutError",
                extra=InfoLogExtra(
                    info_message=f"Transcription timed out: {str(e)}",
                ),
            )
            raise

        except Exception as e:
            self.logger.error(
                "GoogleVideoTranscriptRepository.create_video_transcript.Error",
                extra=InfoLogExtra(
                    info_message=f"Error during create video transcript: {str(e)}",
                ),
            )
            raise

        result = {
            "transcript": transcript,
        }

        return result
