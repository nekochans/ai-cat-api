import os
from typing import AsyncGenerator
from openai import ChatCompletion
from domain.repository.cat_message_repository_interface import (
    CatMessageRepositoryInterface,
    GenerateMessageForGuestUserDto,
    GenerateMessageForGuestUserResult,
)


class OpenAiCatMessageRepository(CatMessageRepositoryInterface):
    def __init__(self) -> None:
        self.OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

    # TODO: 型は合っているのに型チェックエラーが出る mypy が AsyncGenerator に対応していない可能性がある
    # TODO: https://github.com/nekochans/ai-cat-api/issues/68 で別の型チェックツールを試してみる
    async def generate_message_for_guest_user(  # type: ignore
        self, dto: GenerateMessageForGuestUserDto
    ) -> AsyncGenerator[GenerateMessageForGuestUserResult, None]:
        response = await ChatCompletion.acreate(
            model="gpt-3.5-turbo-1106",
            messages=dto.get("chat_messages"),
            stream=True,
            api_key=self.OPENAI_API_KEY,
            temperature=0.7,
            user=dto.get("user_id"),
        )  # type: ignore

        ai_response_id = ""
        async for chunk in response:
            chunk_message = (
                chunk.get("choices")[0]["delta"].get("content")
                if chunk.get("choices")[0]["delta"].get("content")
                else ""
            )

            if ai_response_id == "":
                ai_response_id = chunk.get("id")

            if chunk_message == "":
                continue

            chunk_body: GenerateMessageForGuestUserResult = {
                "ai_response_id": ai_response_id,
                "message": chunk_message,
            }

            yield chunk_body
