import os
import json
import base64
import tempfile
import ffmpeg
from pathlib import Path
from google.cloud import storage
from google.oauth2 import service_account
import vertexai
from vertexai.generative_models import GenerativeModel, Part
from domain.repository.video_repository_interface import (
    VideoRepositoryInterface,
    AnalysisVideoDto,
    AnalysisVideoResult,
)
from log.logger import AppLogger, InfoLogExtra
from infrastructure.google.parse_gcs_path import parse_gcs_path


class GeminiVideoRepository(VideoRepositoryInterface):
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

        vertexai.init(
            project=os.getenv("GOOGLE_CLOUD_PROJECT_ID"),
            location=os.getenv("GOOGLE_CLOUD_REGION"),
            credentials=self.credentials,
        )

    def extract_audio_from_video(self, video_uri: str) -> None:
        gcs_path_components = parse_gcs_path(video_uri)

        bucket = self.google_cloud_storage_client.bucket(
            gcs_path_components["bucket_name"]
        )

        # TODO: 後で .mp4 の動画形式にも対応する
        with tempfile.NamedTemporaryFile(
            suffix=".mov"
        ) as video_temp, tempfile.NamedTemporaryFile(suffix=".wav") as audio_temp:
            # 動画をGCSからダウンロード

            file_path = video_uri.replace(
                f"gs://{gcs_path_components['bucket_name']}/", ""
            )

            blob = bucket.blob(file_path)

            blob.download_to_filename(video_temp.name)

            self.logger.info(
                "GeminiVideoRepository.extract_audio_from_video.DownloadedVideo",
                extra=InfoLogExtra(
                    info_message=f"Downloaded {gcs_path_components["filename"]} to {video_temp.name}",
                ),
            )

            (
                ffmpeg.input(video_temp.name)
                .output(audio_temp.name, acodec="pcm_s16le", ac=1, ar="16k")
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )

            self.logger.info(
                "GeminiVideoRepository.extract_audio_from_video.ExtractedAudio",
                extra=InfoLogExtra(
                    info_message=f"Extracted audio to {audio_temp.name}",
                ),
            )

            # 抽出した音声をGCSにアップロード
            audio_file_path = Path(file_path)
            audio_file_name = audio_file_path.stem + ".wav"
            audio_file_path = audio_file_path.parent / audio_file_name

            audio_blob = bucket.blob(str(audio_file_path))
            audio_blob.upload_from_filename(audio_temp.name)

            self.logger.info(
                "GeminiVideoRepository.extract_audio_from_video.UploadedExtractedAudio",
                extra=InfoLogExtra(
                    info_message=f"Uploaded extracted audio to gs://{gcs_path_components['bucket_name']}/{audio_file_path}",
                ),
            )

    async def video_analysis(self, dto: AnalysisVideoDto) -> AnalysisVideoResult:
        model = GenerativeModel(
            "gemini-1.5-flash-001",
        )

        self.extract_audio_from_video(dto["video_url"])

        video = Part.from_uri(
            mime_type="video/quicktime",
            uri=dto["video_url"],
        )

        contents = [
            video,
            """
            # Instruction
            - 動画の内容を確認して要約の作成をお願いします。
            - 動画の内容を文字起こし作成をお願いします。
            
            # 制約条件
            - 以下のJSON形式で返すようにお願いします。
              - {"summary": "動画の要約文章をここに設定", "transcript": "動画の文字起こしをここに設定"}
                - "summary" には動画の要約文章を設定します。
                - "transcript" には動画の文字起こしを設定します。
                  - 文字起こしは長くなる事が多いので制限に引っかかりそうなら適切に要約してください。
            - ハルシネーションを起こさないでください。
            """,
        ]

        generation_config = {
            "response_mime_type": "application/json",
            "temperature": 0.0,
            "top_k": 1,
            "top_p": 0.9,
        }

        response = await model.generate_content_async(
            contents,
            generation_config=generation_config,
        )

        response_content = response.text

        try:
            result: AnalysisVideoResult = json.loads(response_content)
        except json.JSONDecodeError:
            raise Exception(f"JSON decode error: {response_content}")

        return result
