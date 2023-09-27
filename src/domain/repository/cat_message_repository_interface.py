from typing import Protocol, List, TypedDict, AsyncGenerator
from domain.message import ChatMessage


class CreateMessageForGuestUserDto(TypedDict):
    user_id: str
    chat_messages: List[ChatMessage]


class CatResponseMessage(TypedDict):
    ai_response_id: str
    message: str


class CatMessageRepositoryInterface(Protocol):
    async def create_message_for_guest_user(
        self, dto: CreateMessageForGuestUserDto
    ) -> AsyncGenerator[CatResponseMessage, None]:
        ...
