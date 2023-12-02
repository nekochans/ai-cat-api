import pytest
from typing import Tuple
from aiomysql import Connection
from tests.db.setup_test_database import setup_test_database, create_test_db_name
from infrastructure.db import create_db_connection
from infrastructure.repository.aiomysql.aiomysql_guest_users_conversation_history_repository import (
    AiomysqlGuestUsersConversationHistoryRepository,
    SaveGuestUsersConversationHistoryDto,
)


@pytest.fixture
async def create_test_db_connection() -> Tuple[Connection, str]:
    test_db_name = create_test_db_name()

    connection = await create_db_connection()

    await setup_test_database(
        connection,
        test_db_name,
    )

    async with connection.cursor() as cursor:
        await cursor.execute("TRUNCATE TABLE guest_users_conversation_histories")
    await connection.commit()

    return connection, test_db_name


@pytest.mark.asyncio
async def test_save_conversation_history(create_test_db_connection):
    connection, test_db_name = await create_test_db_connection

    conversation_id = "aaaaaaaa-bbbb-cccc-dddd-000000000000"

    user_id = "uuuuuuuu-uuuu-uuuu-dddd-000000000000"

    dto = SaveGuestUsersConversationHistoryDto(
        conversation_id=conversation_id,
        cat_id="moko",
        user_id=user_id,
        user_message="もこちゃん🐱テストだよ🐱",
        ai_message="もこちゃんだにゃん🐱テストメッセージだにゃん🐱",
    )

    repository = AiomysqlGuestUsersConversationHistoryRepository(connection)

    await repository.save_conversation_history(dto)

    async with connection.cursor() as cursor:
        sql = """
        SELECT *
        FROM guest_users_conversation_histories
        WHERE conversation_id = %s
        """

        await cursor.execute(sql, conversation_id)
        result = await cursor.fetchone()

    assert result is not None
    assert result["conversation_id"] == conversation_id
    assert result["cat_id"] == "moko"
    assert result["user_id"] == user_id
    assert result["user_message"] == dto.get("user_message")
    assert result["ai_message"] == dto.get("ai_message")

    create_test_db_connection.close()
