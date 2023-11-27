import pytest
import os
from aiomysql import Connection
from domain.cat import get_prompt_by_cat_id
from infrastructure.db import create_db_connection
from infrastructure.repository.aiomysql.aiomysql_guest_users_conversation_history_repository import (
    AiomysqlGuestUsersConversationHistoryRepository,
    CreateMessagesWithConversationHistoryDto,
)


@pytest.fixture
async def create_test_db_connection() -> Connection:
    connection = await create_db_connection()

    async with connection.cursor() as cursor:
        await cursor.execute("TRUNCATE TABLE guest_users_conversation_histories")

        await cursor.executemany(
            """
            INSERT INTO
              guest_users_conversation_histories
              (conversation_id, cat_id, user_id, user_message, ai_message)
            VALUES
              (%s, %s, %s, %s, %s)
            """,
            [
                (
                    "aaaaaaaa-bbbb-cccc-dddd-000000000001",
                    "moko",
                    "uuuuuuuu-uuuu-uuuu-dddd-000000000000",
                    "ねこちゃん🐱",
                    "人間ちゃん🐱",
                ),
                (
                    "aaaaaaaa-bbbb-cccc-dddd-000000000001",
                    "moko",
                    "uuuuuuuu-uuuu-uuuu-dddd-000000000000",
                    "違う、私もねこ🐱",
                    "にゃ🐱！！もこ以外にしゃべる🐱がいるなんて！驚きだにゃ🐱",
                ),
                (
                    "aaaaaaaa-bbbb-cccc-dddd-000000000001",
                    "moko",
                    "uuuuuuuu-uuuu-uuuu-dddd-000000000000",
                    "ふふふ🐱",
                    "あなたの名前は何て言うにゃんか🐱？",
                ),
                (
                    "aaaaaaaa-bbbb-cccc-dddd-000000000001",
                    "moko",
                    "uuuuuuuu-uuuu-uuuu-dddd-000000000000",
                    "私の名前はおもちだにゃ🐱",
                    "おもちちゃんか🐱よろしくにゃ🐱",
                ),
                (
                    "aaaaaaaa-bbbb-cccc-dddd-000000000001",
                    "moko",
                    "uuuuuuuu-uuuu-uuuu-dddd-000000000000",
                    "うそだよ！本当はおもちの飼い主のコメだよ🐱",
                    "にゃんだ🐱人間か、、、びっくしたのにゃ🐱もこ以外にしゃべるねこがいる訳ないのだ！",
                ),
                (
                    "aaaaaaaa-bbbb-cccc-dddd-000000000001",
                    "moko",
                    "uuuuuuuu-uuuu-uuuu-dddd-000000000000",
                    "ふふふ🐱あらためてよろしく、もこちゃん！",
                    "よろしくにゃ🐱コメちゃん🐱",
                ),
                (
                    "aaaaaaaa-bbbb-cccc-dddd-000000000001",
                    "moko",
                    "uuuuuuuu-uuuu-uuuu-dddd-000000000000",
                    "もこちゃんの好きな食べ物は🐱？",
                    "もこはチキン味のカリカリだにゃ🐱それしか食べないにゃ🐱",
                ),
                (
                    "aaaaaaaa-bbbb-cccc-dddd-000000000001",
                    "moko",
                    "uuuuuuuu-uuuu-uuuu-dddd-000000000000",
                    "チュールは🐱？",
                    "チュールは苦手だにゃ🐱",
                ),
                (
                    "aaaaaaaa-bbbb-cccc-dddd-000000000001",
                    "moko",
                    "uuuuuuuu-uuuu-uuuu-dddd-000000000000",
                    "チュール嫌いなねこちゃんもいるんだね！",
                    "もこは苦手だにゃ🐱コメちゃんの好きな食べ物も教えてにゃ🐱",
                ),
                (
                    "aaaaaaaa-bbbb-cccc-dddd-000000000001",
                    "moko",
                    "uuuuuuuu-uuuu-uuuu-dddd-000000000000",
                    "私はコメって名前の通り白いごはんが好きだよ！",
                    "確かに人間は白いごはんをよく食べてるにゃ🐱",
                ),
                (
                    "aaaaaaaa-bbbb-cccc-dddd-000000000001",
                    "moko",
                    "uuuuuuuu-uuuu-uuuu-dddd-000000000000",
                    "そうそう白いごはんは美味しいよ！",
                    "にゃーもこも白いごはん食べたいにゃ🐱",
                ),
            ],
        )
    await connection.commit()

    return connection


@pytest.mark.asyncio
async def test_create_messages_with_conversation_history(create_test_db_connection):
    connection = await create_test_db_connection

    conversation_id = "aaaaaaaa-bbbb-cccc-dddd-000000000001"

    dto = CreateMessagesWithConversationHistoryDto(
        conversation_id=conversation_id,
        request_message="いっしょに白いごはんを食べよう！",
        cat_id="moko",
    )

    repository = AiomysqlGuestUsersConversationHistoryRepository(connection)

    chat_messages = await repository.create_messages_with_conversation_history(dto)

    expected = [
        {"role": "system", "content": get_prompt_by_cat_id(dto.get("cat_id"))},
        {"role": "user", "content": "違う、私もねこ🐱"},
        {"role": "assistant", "content": "にゃ🐱！！もこ以外にしゃべる🐱がいるなんて！驚きだにゃ🐱"},
        {"role": "user", "content": "ふふふ🐱"},
        {"role": "assistant", "content": "あなたの名前は何て言うにゃんか🐱？"},
        {"role": "user", "content": "私の名前はおもちだにゃ🐱"},
        {"role": "assistant", "content": "おもちちゃんか🐱よろしくにゃ🐱"},
        {"role": "user", "content": "うそだよ！本当はおもちの飼い主のコメだよ🐱"},
        {"role": "assistant", "content": "にゃんだ🐱人間か、、、びっくしたのにゃ🐱もこ以外にしゃべるねこがいる訳ないのだ！"},
        {"role": "user", "content": "ふふふ🐱あらためてよろしく、もこちゃん！"},
        {"role": "assistant", "content": "よろしくにゃ🐱コメちゃん🐱"},
        {"role": "user", "content": "もこちゃんの好きな食べ物は🐱？"},
        {"role": "assistant", "content": "もこはチキン味のカリカリだにゃ🐱それしか食べないにゃ🐱"},
        {"role": "user", "content": "チュールは🐱？"},
        {"role": "assistant", "content": "チュールは苦手だにゃ🐱"},
        {"role": "user", "content": "チュール嫌いなねこちゃんもいるんだね！"},
        {"role": "assistant", "content": "もこは苦手だにゃ🐱コメちゃんの好きな食べ物も教えてにゃ🐱"},
        {"role": "user", "content": "私はコメって名前の通り白いごはんが好きだよ！"},
        {"role": "assistant", "content": "確かに人間は白いごはんをよく食べてるにゃ🐱"},
        {"role": "user", "content": "そうそう白いごはんは美味しいよ！"},
        {"role": "assistant", "content": "にゃーもこも白いごはん食べたいにゃ🐱"},
        {"role": "user", "content": "いっしょに白いごはんを食べよう！"},
    ]

    assert len(chat_messages) == len(expected), "Length mismatch"

    for i in range(len(chat_messages)):
        assert (
            chat_messages[i]["role"] == expected[i]["role"]
        ), f"Role mismatch at index {i}"
        assert (
            chat_messages[i]["content"] == expected[i]["content"]
        ), f"Content mismatch at index {i}"

    create_test_db_connection.close()
