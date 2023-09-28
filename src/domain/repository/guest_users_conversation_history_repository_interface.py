from typing import List, TypedDict, Protocol
from domain.cat import CatId
from domain.message import ChatMessage


class CreateMessagesWithConversationHistoryDto(TypedDict):
    conversation_id: str
    request_message: str
    cat_id: CatId


class SaveGuestUsersConversationHistoryDto(TypedDict):
    conversation_id: str
    cat_id: CatId
    user_id: str
    user_message: str
    ai_message: str


class GuestUsersConversationHistoryRepositoryInterface(Protocol):
    async def create_messages_with_conversation_history(
        self, dto: CreateMessagesWithConversationHistoryDto
    ) -> List[ChatMessage]:
        ...

    async def save_conversation_history(
        self, dto: SaveGuestUsersConversationHistoryDto
    ) -> None:
        ...
