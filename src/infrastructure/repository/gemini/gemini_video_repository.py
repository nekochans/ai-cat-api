import os
import json
import base64
import ffmpeg
import tempfile
import math

# TODO: なぜかmypyの型エラーになるので type: ignore で回避している
from google.cloud import storage  # type: ignore
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

    def extract_video_duration(self, video_uri: str) -> float:
        gcs_path_components = parse_gcs_path(video_uri)
        bucket = self.google_cloud_storage_client.bucket(
            gcs_path_components["bucket_name"]
        )

        file_path = video_uri.replace(f"gs://{gcs_path_components['bucket_name']}/", "")
        blob = bucket.blob(file_path)

        with tempfile.NamedTemporaryFile(
            suffix=f".{gcs_path_components['file_extension']}"
        ) as temp_file:
            blob.download_to_filename(temp_file.name)
            self.logger.info(
                "GeminiVideoRepository.extract_video_duration.DownloadedVideo",
                extra=InfoLogExtra(
                    info_message=f"Downloaded {file_path} to {temp_file.name}",
                ),
            )
            try:
                probe = ffmpeg.probe(temp_file.name)
                video_info = next(
                    s for s in probe["streams"] if s["codec_type"] == "video"
                )
                duration = float(video_info["duration"])
                self.logger.info(
                    "GeminiVideoRepository.extract_video_duration.Success",
                    extra=InfoLogExtra(
                        info_message=f"Successfully extracted video duration: {duration} seconds"
                    ),
                )
                return duration
            except ffmpeg.Error as e:
                self.logger.error(
                    "GeminiVideoRepository.extract_video_duration.FFmpegError",
                    extra=InfoLogExtra(info_message=f"FFmpeg error: {str(e)}"),
                )
                raise
            except Exception as e:
                self.logger.error(
                    "GeminiVideoRepository.extract_video_duration.Error",
                    extra=InfoLogExtra(
                        info_message=f"Error retrieving video duration: {str(e)}"
                    ),
                )
                raise

    async def video_analysis(self, dto: AnalysisVideoDto) -> AnalysisVideoResult:
        model = GenerativeModel(
            "gemini-1.5-flash-001",
        )

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
              - {"summary": "動画の要約文章をここに設定"}
                - "summary" には動画の要約文章を設定します。
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
            duration = self.extract_video_duration(dto["video_url"])
            result["duration_in_seconds"] = math.floor(duration)
        except json.JSONDecodeError:
            raise Exception(f"JSON decode error: {response_content}")
        except Exception as e:
            self.logger.error(
                "GeminiVideoRepository.video_analysis.Error",
                extra=InfoLogExtra(
                    info_message=f"Error during video analysis: {str(e)}"
                ),
            )
            raise

        return result
