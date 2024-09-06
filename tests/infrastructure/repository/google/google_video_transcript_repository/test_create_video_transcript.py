import pytest
import sys
from src.infrastructure.repository.google.google_video_transcript_repository import (
    GoogleVideoTranscriptRepository,
)
from domain.repository.video_transcript_repository_interface import (
    CreateVideoTranscriptDto,
    CreateVideoTranscriptResult,
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
            "gs://test-ai-cat/video-files/Cat.MOV",
            {"transcript": "文字起こし", "duration_in_seconds": 42},
        ),
    ],
)
async def test_create_video_transcript(
    video_url: str, expected: CreateVideoTranscriptResult
) -> None:
    repository = GoogleVideoTranscriptRepository()

    dto = CreateVideoTranscriptDto(
        video_url=video_url,
    )

    result = await repository.create_video_transcript(dto)

    assert "transcript" in result, "Result does not contain 'transcript' key"
    assert isinstance(result["transcript"], str), "'transcript' is not a string"
    assert len(result["transcript"]) > 0, "'transcript' is an empty string"

    assert result["duration_in_seconds"] == expected["duration_in_seconds"]
