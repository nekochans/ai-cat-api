import os
from typing import List, TypedDict, AsyncGenerator
from openai import ChatCompletion
from domain.message import ChatMessage


class CreateMessageForGuestUserDto(TypedDict):
    user_id: str
    chat_messages: List[ChatMessage]


class CatResponseMessage(TypedDict):
    ai_response_id: str
    message: str


class CatMessageRepository:
    def __init__(self):
        self.OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

    async def create_message_for_guest_user(
        self, dto: CreateMessageForGuestUserDto
    ) -> AsyncGenerator[CatResponseMessage, None]:
        response = await ChatCompletion.acreate(
            model="gpt-3.5-turbo-0613",
            messages=dto.get("chat_messages"),
            stream=True,
            api_key=self.OPENAI_API_KEY,
            temperature=0.7,
            user=dto.get("user_id"),
        )

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

            chunk_body = {
                "ai_response_id": ai_response_id,
                "message": chunk_message,
            }

            yield chunk_body
