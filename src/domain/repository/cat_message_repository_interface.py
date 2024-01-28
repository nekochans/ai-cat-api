from typing import Protocol, List, TypedDict, AsyncGenerator
from domain.message import ChatMessage


class GenerateMessageForGuestUserDto(TypedDict):
    user_id: str
    chat_messages: List[ChatMessage]


class GenerateMessageForGuestUserResult(TypedDict):
    ai_response_id: str
    message: str


class CatMessageRepositoryInterface(Protocol):
    async def generate_message_for_guest_user(
        self, dto: GenerateMessageForGuestUserDto
    ) -> AsyncGenerator[GenerateMessageForGuestUserResult, None]: ...
