from typing import List
from domain.message import ChatMessage
from domain.repository.guest_users_conversation_history_repository_interface import (
    GuestUsersConversationHistoryRepositoryInterface,
    CreateMessagesWithConversationHistoryDto,
    SaveGuestUsersConversationHistoryDto,
)


class MockGuestUsersConversationHistoryRepository(
    GuestUsersConversationHistoryRepositoryInterface
):
    async def create_messages_with_conversation_history(
        self, dto: CreateMessagesWithConversationHistoryDto
    ) -> List[ChatMessage]:
        if dto.get("request_message") == "ERROR":
            raise Exception(
                "failed to MockGuestUsersConversationHistoryRepository.create_messages_with_conversation_history"
            )

        return [
            {
                "role": "user",
                "content": "ねこちゃん🐱",
            },
            {
                "role": "assistant",
                "content": "こんにちは人間ちゃん🐱",
            },
            {
                "role": "user",
                "content": dto.get("request_message") or "",
            },
            {
                "role": "assistant",
                "content": "ねこはチュールが好きだけど、たまにチュールが嫌いなねこもいるにゃん🐱",
            },
        ]

    async def save_conversation_history(
        self, dto: SaveGuestUsersConversationHistoryDto
    ) -> None:
        if dto.get("conversation_id") == "ERROR":
            raise Exception(
                "failed to MockGuestUsersConversationHistoryRepository.save_conversation_history"
            )
