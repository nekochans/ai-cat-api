from typing import Optional, AsyncGenerator
from fastapi import status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
from presentation.sse import format_sse, generate_error_response
from domain.cat import CatId
from domain.unique_id import is_uuid_format, generate_unique_id
from domain.message import is_message
from domain.repository.cat_message_repository_interface import (
    GenerateMessageForGuestUserDto,
)
from infrastructure.db import create_db_connection
from infrastructure.repository.guest_users_conversation_history_repository import (
    GuestUsersConversationHistoryRepository,
)
from infrastructure.repository.cat_message_repository import (
    CatMessageRepository,
)
from log.logger import AppLogger, SuccessLogExtra, ErrorLogExtra


class GenerateCatMessageForGuestUserRequestBody(BaseModel):
    userId: str
    message: str
    conversationId: Optional[str] = None

    @field_validator("userId", "conversationId")
    @classmethod
    def validate_uuid(cls, v: str) -> str:
        if not is_uuid_format(v):
            raise ValueError(f"'{v}' is not in UUID format")
        return v

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        if not is_message(v):
            raise ValueError(
                "message must be at least 2 character and no more than 5,000 characters"
            )
        return v


class GenerateCatMessageForGuestUserResponseBody(BaseModel):
    conversationId: str
    message: str


class GenerateCatMessageForGuestUserController:
    def __init__(
        self, cat_id: CatId, request_body: GenerateCatMessageForGuestUserRequestBody
    ) -> None:
        app_logger = AppLogger()
        self.logger = app_logger.logger
        self.cat_id = cat_id
        self.request_body = request_body

    async def exec(self) -> StreamingResponse:
        unique_id = generate_unique_id()

        conversation_id = unique_id
        if self.request_body.conversationId is not None and is_uuid_format(
            self.request_body.conversationId
        ):
            conversation_id = self.request_body.conversationId

        response_headers = {"Ai-Meow-Cat-Request-Id": unique_id}

        try:
            connection = await create_db_connection()

            repository = GuestUsersConversationHistoryRepository(connection)

            chat_messages = await repository.create_messages_with_conversation_history(
                {
                    "conversation_id": conversation_id,
                    "request_message": self.request_body.message,
                    "cat_id": self.cat_id,
                }
            )
        except Exception as e:
            self.logger.error(
                f"An error occurred while connecting to the database: {str(e)}",
                exc_info=True,
                extra=ErrorLogExtra(
                    request_id=response_headers["Ai-Meow-Cat-Request-Id"],
                    conversation_id=conversation_id,
                    cat_id=self.cat_id,
                    user_id=self.request_body.userId,
                    user_message=self.request_body.message,
                ).model_dump(),
            )

            db_error_response_body = {
                "type": "INTERNAL_SERVER_ERROR",
                "title": "an unexpected error has occurred.",
                "detail": str(e),
            }

            return StreamingResponse(
                content=generate_error_response(db_error_response_body),
                media_type="text/event-stream",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                headers=response_headers,
            )

        async def generate_cat_message_for_guest_user_stream() -> AsyncGenerator[
            str, None
        ]:
            try:
                # AIの応答を一時的に保存するためのリスト
                ai_responses = []

                # AIの応答を結合するための変数
                ai_response_message = ""

                cat_message_repository = CatMessageRepository()

                create_message_for_guest_user_dto = GenerateMessageForGuestUserDto(
                    user_id=self.request_body.userId,
                    chat_messages=chat_messages,
                )

                ai_response_id = ""
                async for chunk in cat_message_repository.generate_message_for_guest_user(
                    create_message_for_guest_user_dto
                ):
                    # AIの応答を更新
                    ai_response_message += chunk.get("message") or ""

                    if ai_response_id == "":
                        ai_response_id = chunk.get("ai_response_id") or ""

                    chunk_body = GenerateCatMessageForGuestUserResponseBody(
                        conversationId=conversation_id,
                        message=chunk.get("message") or "",
                    )

                    yield format_sse(chunk_body.model_dump())

                ai_responses.append(
                    {"role": "assistant", "content": ai_response_message}
                )

                # ストリーミングが終了したときに会話履歴をDBに保存する
                await connection.begin()

                await repository.save_conversation_history(
                    {
                        "conversation_id": conversation_id,
                        "cat_id": self.cat_id,
                        "user_id": self.request_body.userId,
                        "user_message": self.request_body.message,
                        "ai_message": ai_response_message,
                    }
                )

                await connection.commit()

                self.logger.info(
                    "success",
                    extra=SuccessLogExtra(
                        request_id=response_headers["Ai-Meow-Cat-Request-Id"],
                        conversation_id=conversation_id,
                        cat_id=self.cat_id,
                        user_id=self.request_body.userId,
                        ai_response_id=ai_response_id,
                    ).model_dump(),
                )
            except Exception as e:
                await connection.rollback()

                self.logger.error(
                    f"An error occurred while creating the message: {str(e)}",
                    exc_info=True,
                    extra=ErrorLogExtra(
                        request_id=response_headers["Ai-Meow-Cat-Request-Id"],
                        conversation_id=conversation_id,
                        cat_id=self.cat_id,
                        user_id=self.request_body.userId,
                        user_message=self.request_body.message,
                    ).model_dump(),
                )

                unexpected_error_response_body = {
                    "type": "INTERNAL_SERVER_ERROR",
                    "title": "an unexpected error has occurred.",
                    "detail": str(e),
                }

                yield format_sse(unexpected_error_response_body)
            finally:
                connection.close()

        return StreamingResponse(
            generate_cat_message_for_guest_user_stream(),
            media_type="text/event-stream",
            headers=response_headers,
        )
