import pytest
import asyncstdlib
from usecase.generate_cat_message_for_guest_user_use_case import (
    GenerateCatMessageForGuestUserUseCase,
    GenerateCatMessageForGuestUserUseCaseDto,
)
from infrastructure.repository.mock.mock_db_handler import MockDbHandler
from infrastructure.repository.mock.mock_users_conversation_history_repository import (
    MockGuestUsersConversationHistoryRepository,
)
from infrastructure.repository.mock.mock_cat_message_repository import (
    MockCatMessageRepository,
)


@pytest.mark.asyncio
async def test_execute_success_with_only_required_params():
    dto = GenerateCatMessageForGuestUserUseCaseDto(
        request_id="test-request-id",
        user_id="test-user-id",
        cat_id="moko",
        message="test-message",
        db_handler=MockDbHandler(),
        guest_users_conversation_history_repository=MockGuestUsersConversationHistoryRepository(),
        cat_message_repository=MockCatMessageRepository(),
    )

    use_case = GenerateCatMessageForGuestUserUseCase(dto)

    expectedMessages = ["はじめましてだにゃん", "🐱", "何かお手伝いできる事はないにゃんか？"]

    async for i, result in asyncstdlib.enumerate(use_case.execute()):
        assert "conversation_id" in result
        assert "message" in result
        assert result["conversation_id"] == "test-request-id"
        assert result["message"] == expectedMessages[i]
