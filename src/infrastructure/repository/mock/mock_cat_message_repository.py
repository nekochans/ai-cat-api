import asyncio
from typing import AsyncGenerator
from domain.repository.cat_message_repository_interface import (
    GenerateMessageForGuestUserDto,
    GenerateMessageForGuestUserResult,
)


class MockCatMessageRepository:
    async def generate_message_for_guest_user(
        self, dto: GenerateMessageForGuestUserDto
    ) -> AsyncGenerator[GenerateMessageForGuestUserResult, None]:
        messages = ["はじめましてだにゃん", "🐱", "何かお手伝いできる事はないにゃんか？"]

        for message in messages:
            await asyncio.sleep(0.5)
            yield GenerateMessageForGuestUserResult(
                ai_response_id="mocked-ai-response-id", message=message
            )