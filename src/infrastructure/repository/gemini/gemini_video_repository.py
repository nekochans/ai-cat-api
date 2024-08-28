import os
import json
import base64

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
from log.logger import AppLogger


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
        except json.JSONDecodeError:
            raise Exception(f"JSON decode error: {response_content}")

        return result
