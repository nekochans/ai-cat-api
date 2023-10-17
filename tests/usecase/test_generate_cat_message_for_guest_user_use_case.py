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
        request_id="dummy000-0000-0000-0000-requestid000",
        user_id="dummy000-user-id00-0000-000000000000",
        cat_id="moko",
        message="ねこちゃんこんにちは🐱",
        db_handler=MockDbHandler(),
        guest_users_conversation_history_repository=MockGuestUsersConversationHistoryRepository(),
        cat_message_repository=MockCatMessageRepository(),
    )

    use_case = GenerateCatMessageForGuestUserUseCase(dto)

    expectedMessages = ["はじめましてだにゃん", "🐱", "何かお手伝いできる事はないにゃんか？"]

    async for i, result in asyncstdlib.enumerate(use_case.execute()):
        assert "conversation_id" in result
        assert "message" in result
        assert result["conversation_id"] == "dummy000-0000-0000-0000-requestid000"
        assert result["message"] == expectedMessages[i]


@pytest.mark.asyncio
async def test_execute_success_with_all_params():
    dto = GenerateCatMessageForGuestUserUseCaseDto(
        request_id="dummy000-0000-0000-0000-requestid000",
        user_id="dummy000-user-id00-0000-000000000000",
        cat_id="moko",
        message="ねこちゃんこんにちは🐱",
        db_handler=MockDbHandler(),
        guest_users_conversation_history_repository=MockGuestUsersConversationHistoryRepository(),
        cat_message_repository=MockCatMessageRepository(),
        conversation_id="dummyid0-0000-0000-0000-conversation",
    )

    use_case = GenerateCatMessageForGuestUserUseCase(dto)

    expectedMessages = ["はじめましてだにゃん", "🐱", "何かお手伝いできる事はないにゃんか？"]

    async for i, result in asyncstdlib.enumerate(use_case.execute()):
        assert "conversation_id" in result
        assert "message" in result
        assert result["conversation_id"] == "dummyid0-0000-0000-0000-conversation"
        assert result["message"] == expectedMessages[i]


@pytest.mark.asyncio
async def test_execute_error_failed_to_create_messages_with_conversation_history():
    dto = GenerateCatMessageForGuestUserUseCaseDto(
        request_id="dummy000-0000-0000-0000-requestid000",
        user_id="dummy000-user-id00-0000-000000000000",
        cat_id="moko",
        message="ERROR",
        db_handler=MockDbHandler(),
        guest_users_conversation_history_repository=MockGuestUsersConversationHistoryRepository(),
        cat_message_repository=MockCatMessageRepository(),
        conversation_id="dummyid0-0000-0000-0000-conversation",
    )

    use_case = GenerateCatMessageForGuestUserUseCase(dto)

    async for result in use_case.execute():
        assert "title" in result
        assert "type" in result
        assert result["title"] == "an unexpected error has occurred."
        assert result["type"] == "INTERNAL_SERVER_ERROR"


@pytest.mark.asyncio
async def test_execute_error_failed_to_save_conversation_history():
    dto = GenerateCatMessageForGuestUserUseCaseDto(
        request_id="dummy000-0000-0000-0000-requestid000",
        user_id="dummy000-user-id00-0000-000000000000",
        cat_id="moko",
        message="ねこちゃんこんにちは🐱",
        db_handler=MockDbHandler(),
        guest_users_conversation_history_repository=MockGuestUsersConversationHistoryRepository(),
        cat_message_repository=MockCatMessageRepository(),
        conversation_id="ERROR",
    )

    use_case = GenerateCatMessageForGuestUserUseCase(dto)

    expectedMessages = ["はじめましてだにゃん", "🐱", "何かお手伝いできる事はないにゃんか？"]

    async for i, result in asyncstdlib.enumerate(use_case.execute()):
        if i == 3:
            assert "title" in result
            assert "type" in result
            assert result["title"] == "an unexpected error has occurred."
            assert result["type"] == "INTERNAL_SERVER_ERROR"
        else:
            assert "conversation_id" in result
            assert "message" in result
            assert result["conversation_id"] == "ERROR"
            assert result["message"] == expectedMessages[i]
