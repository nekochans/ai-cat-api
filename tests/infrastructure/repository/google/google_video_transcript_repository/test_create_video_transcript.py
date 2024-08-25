import pytest
import sys
from src.infrastructure.repository.google.google_video_transcript_repository import (
    GoogleVideoTranscriptRepository,
)
from domain.repository.video_transcript_repository_interface import (
    CreateVideoTranscriptDto,
)


@pytest.fixture(scope="session", autouse=True)
def setup(worker_id: str) -> None:
    sys.stdout = sys.stderr


# @pytest.mark.skip(reason="APIの課金が発生する、実行時間が非常に長いため普段はスキップ")
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "video_url, expected_message",
    [
        (
            "gs://test-ai-cat/video-files/Cat.MOV",
            {"summary": "This is a summary of the video.", "transcript": "文字起こし"},
        ),
    ],
)
async def test_create_video_transcript(video_url: str, expected_message: str) -> None:
    repository = GoogleVideoTranscriptRepository()

    dto = CreateVideoTranscriptDto(
        video_url=video_url,
    )

    result = await repository.create_video_transcript(dto)

    print(result)

    assert "transcript" in result, "Result does not contain 'transcript' key"
    assert isinstance(result["transcript"], str), "'transcript' is not a string"
    assert len(result["transcript"]) > 0, "'transcript' is an empty string"
