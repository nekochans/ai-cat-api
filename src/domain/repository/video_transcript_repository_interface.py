from typing import Protocol, TypedDict


class CreateVideoTranscriptDto(TypedDict):
    video_url: str


class CreateVideoTranscriptResult(TypedDict):
    transcript: str
    duration_in_seconds: int


class VideoTranscriptRepositoryInterface(Protocol):
    async def create_video_transcript(
        self, dto: CreateVideoTranscriptDto
    ) -> CreateVideoTranscriptResult: ...
