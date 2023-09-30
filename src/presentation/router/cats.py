import uuid
import os
from typing import Optional, AsyncGenerator
from fastapi import APIRouter, status, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
from presentation.sse import format_sse, generate_error_response
from domain.cat import CatId
from domain.unique_id import is_uuid_format
from domain.message import is_message
from infrastructure.db import create_db_connection
from infrastructure.repository.guest_users_conversation_history_repository import (
    GuestUsersConversationHistoryRepository,
)
from infrastructure.repository.cat_message_repository import (
    CatMessageRepository,
    GenerateMessageForGuestUserDto,
)
from infrastructure.logger import AppLogger, SuccessLogExtra, ErrorLogExtra

router = APIRouter()

app_logger = AppLogger()

logger = app_logger.logger


API_CREDENTIAL = os.environ["API_CREDENTIAL"]


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


@router.post(
    "/cats/{cat_id}/messages-for-guest-users",
    tags=["cats"],
    status_code=status.HTTP_200_OK,
)
async def generate_cat_message_for_guest_user(
    request: Request,
    cat_id: CatId,
    request_body: GenerateCatMessageForGuestUserRequestBody,
) -> StreamingResponse:
    unique_id = uuid.uuid4()

    conversation_id: str = (
        str(unique_id)
        if request_body.conversationId is None
        else request_body.conversationId
    )

    response_headers = {"Ai-Meow-Cat-Request-Id": str(unique_id)}

    authorization = request.headers.get("Authorization", None)

    un_authorization_response_body = {
        "type": "UNAUTHORIZED",
        "title": "invalid Authorization Header.",
        "detail": "Authorization Header is not set.",
        "userId": request_body.userId,
        "catId": cat_id,
    }

    if authorization is None:
        return StreamingResponse(
            content=generate_error_response(un_authorization_response_body),
            media_type="text/event-stream",
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers=response_headers,
        )

    authorization_headers = authorization.split(" ")

    if len(authorization_headers) != 2 or authorization_headers[0] != "Basic":
        return StreamingResponse(
            content=generate_error_response(un_authorization_response_body),
            media_type="text/event-stream",
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers=response_headers,
        )

    if authorization_headers[1] != API_CREDENTIAL:
        un_authorization_response_body = {
            "type": "UNAUTHORIZED",
            "title": "invalid Authorization Header.",
            "detail": "invalid credential.",
            "userId": request_body.userId,
            "catId": cat_id,
        }

        return StreamingResponse(
            content=generate_error_response(un_authorization_response_body),
            media_type="text/event-stream",
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers=response_headers,
        )

    try:
        connection = await create_db_connection()

        repository = GuestUsersConversationHistoryRepository(connection)

        chat_messages = await repository.create_messages_with_conversation_history(
            {
                "conversation_id": conversation_id,
                "request_message": request_body.message,
                "cat_id": cat_id,
            }
        )
    except Exception as e:
        logger.error(
            f"An error occurred while connecting to the database: {str(e)}",
            exc_info=True,
            extra=ErrorLogExtra(
                request_id=response_headers["Ai-Meow-Cat-Request-Id"],
                conversation_id=conversation_id,
                cat_id=cat_id,
                user_id=request_body.userId,
                user_message=request_body.message,
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

    async def generate_cat_message_for_guest_user_stream() -> AsyncGenerator[str, None]:
        try:
            # AIの応答を一時的に保存するためのリスト
            ai_responses = []

            # AIの応答を結合するための変数
            ai_response_message = ""

            cat_message_repository = CatMessageRepository()

            create_message_for_guest_user_dto = GenerateMessageForGuestUserDto(
                user_id=request_body.userId,
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

            ai_responses.append({"role": "assistant", "content": ai_response_message})

            # ストリーミングが終了したときに会話履歴をDBに保存する
            await connection.begin()

            await repository.save_conversation_history(
                {
                    "conversation_id": conversation_id,
                    "cat_id": cat_id,
                    "user_id": request_body.userId,
                    "user_message": request_body.message,
                    "ai_message": ai_response_message,
                }
            )

            await connection.commit()

            logger.info(
                "success",
                extra=SuccessLogExtra(
                    request_id=response_headers["Ai-Meow-Cat-Request-Id"],
                    conversation_id=conversation_id,
                    cat_id=cat_id,
                    user_id=request_body.userId,
                    ai_response_id=ai_response_id,
                ).model_dump(),
            )
        except Exception as e:
            await connection.rollback()

            logger.error(
                f"An error occurred while creating the message: {str(e)}",
                exc_info=True,
                extra=ErrorLogExtra(
                    request_id=response_headers["Ai-Meow-Cat-Request-Id"],
                    conversation_id=conversation_id,
                    cat_id=cat_id,
                    user_id=request_body.userId,
                    user_message=request_body.message,
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