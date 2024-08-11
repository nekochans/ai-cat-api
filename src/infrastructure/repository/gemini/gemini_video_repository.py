import os
import json
import base64
from domain.repository.video_repository_interface import (
    VideoRepositoryInterface,
    AnalysisVideoDto,
    AnalysisVideoResult,
)
from google.cloud import storage
from google.oauth2 import service_account
import vertexai
from vertexai.generative_models import GenerativeModel, Part


class GeminiVideoRepository(VideoRepositoryInterface):
    def __init__(self) -> None:
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
            動画の内容を確認して要約の作成をお願いします。
            
            # 制約条件
            - 以下のJSON形式で返すようにお願いします。
              - {"summary": "動画の要約文章をここに設定"}
                - "summary" には動画の要約文章を設定します。
            - ハルシネーションを起こさないでください。
            """,
        ]

        generation_config = {
            "response_mime_type": "application/json",
        }

        response = await model.generate_content_async(
            contents,
            generation_config=generation_config,
        )

        response_content = response.text

        result: AnalysisVideoResult = json.loads(response_content)

        return result
