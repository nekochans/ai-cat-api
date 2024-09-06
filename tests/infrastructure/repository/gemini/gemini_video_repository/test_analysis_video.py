import pytest
import sys
from src.infrastructure.repository.gemini.gemini_video_repository import (
    GeminiVideoRepository,
)
from domain.repository.video_repository_interface import (
    AnalysisVideoDto,
    AnalysisVideoResult,
)


@pytest.fixture(scope="session", autouse=True)
def setup(worker_id: str) -> None:
    sys.stdout = sys.stderr


@pytest.mark.skip(reason="APIの課金が発生する、実行時間が非常に長いため普段はスキップ")
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "video_url, expected",
    [
        (
            "gs://test-ai-cat/video-files/2024/neighborhood-cat.mp4",
            {"summary": "This is a summary of the video.", "duration_in_seconds": 42},
        ),
        (
            "gs://test-ai-cat/video-files/2024/strawberry-fair.mp4",
            {"summary": "This is a summary of the video.", "duration_in_seconds": 48},
        ),
    ],
)
async def test_analysis_video(video_url: str, expected: AnalysisVideoResult) -> None:
    repository = GeminiVideoRepository()

    dto = AnalysisVideoDto(
        video_url=video_url,
    )

    result = await repository.video_analysis(dto)

    assert "summary" in result, "Result does not contain 'summary' key"
    assert isinstance(result["summary"], str), "'summary' is not a string"
    assert len(result["summary"]) > 0, "'summary' is an empty string"

    assert result["duration_in_seconds"] == expected["duration_in_seconds"]

    # TODO: 後で評価用のLLMを使って expected_message と result["summary"] の類似度を評価する
