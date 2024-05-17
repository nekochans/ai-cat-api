from typing import Protocol, List, TypedDict
from collections.abc import AsyncIterator
from domain.message import ChatMessage
from domain.cat import CatId


class GenerateMessageForGuestUserDto(TypedDict):
    cat_id: CatId
    user_id: str
    chat_messages: List[ChatMessage]


class GenerateMessageForGuestUserResult(TypedDict):
    ai_response_id: str
    message: str


class CatMessageRepositoryInterface(Protocol):
    def generate_message_for_guest_user(
        self, dto: GenerateMessageForGuestUserDto
    ) -> AsyncIterator[GenerateMessageForGuestUserResult]: ...
