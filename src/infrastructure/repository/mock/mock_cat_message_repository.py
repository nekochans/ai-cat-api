import asyncio
from typing import AsyncGenerator
from domain.repository.cat_message_repository_interface import (
    CatMessageRepositoryInterface,
    GenerateMessageForGuestUserDto,
    GenerateMessageForGuestUserResult,
)


class MockCatMessageRepository(CatMessageRepositoryInterface):
    async def generate_message_for_guest_user(  # type: ignore
        self, dto: GenerateMessageForGuestUserDto
    ) -> AsyncGenerator[GenerateMessageForGuestUserResult, None]:
        messages = [
            "はじめましてだにゃん",
            "🐱",
            "何かお手伝いできる事はないにゃんか？",
        ]

        if dto["user_id"] == "dummy999-user-id99-9999-error9999999":
            raise Exception("An error occurred while generating message.")

        for message in messages:
            await asyncio.sleep(0.5)
            yield GenerateMessageForGuestUserResult(
                ai_response_id="chatcmpl-abcdefghijklmnopqrstuvwxyz001", message=message
            )
