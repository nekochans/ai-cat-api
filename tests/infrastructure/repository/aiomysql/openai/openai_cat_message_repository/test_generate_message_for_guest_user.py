import pytest
import sys
from src.infrastructure.repository.openai.openai_cat_message_repository import (
    OpenAiCatMessageRepository,
)
from domain.repository.cat_message_repository_interface import (
    GenerateMessageForGuestUserDto,
)
from domain.cat import get_prompt_by_cat_id


@pytest.fixture(scope="session", autouse=True)
def setup(worker_id: str) -> None:
    sys.stdout = sys.stderr


@pytest.mark.skip(reason="APIの課金が発生する、実行時間が非常に長いため普段はスキップ")
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "user_message, expected_ai_message",
    [
        (
            "こんにちは！もこちゃんの好きな食べ物を教えて！",
            "はじめましてなのだ🐱もこはチキン味のカリカリが好きなのだ🐱",
        ),
        (
            "もこちゃんはチュールは好き？",
            "もこはねこだけどチュールが苦手だにゃん🐱",
        ),
    ],
)
async def test_generate_message_for_guest_user(
    user_message: str, expected_ai_message: str
) -> None:
    repository = OpenAiCatMessageRepository()

    dto = GenerateMessageForGuestUserDto(
        user_id="0e9633ca-1002-47d3-92d4-45a322e7eba1",
        chat_messages=[
            {"role": "system", "content": get_prompt_by_cat_id("moko")},
            {"role": "user", "content": user_message},
        ],
    )

    ai_response_id = ""
    message = ""

    async for results in repository.generate_message_for_guest_user(dto):
        ai_response_id = results.get("ai_response_id")
        message = message + results.get("message")

    assert ai_response_id.startswith(
        "chatcmpl-"
    ), "ai_response_id does not start with 'chatcmpl-'"
