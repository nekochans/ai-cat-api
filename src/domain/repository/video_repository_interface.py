from typing import Protocol, TypedDict


class AnalysisVideoDto(TypedDict):
    video_url: str


class AnalysisVideoResult(TypedDict):
    summary: str


class VideoRepositoryInterface(Protocol):
    async def video_analysis(self, dto: AnalysisVideoDto) -> AnalysisVideoResult: ...
