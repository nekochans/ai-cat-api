import os
import json
import uvicorn
import uuid
from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Optional, Dict, Any, Generator, AsyncGenerator
from pydantic import BaseModel, field_validator
from infrastructure.logger import AppLogger, SuccessLogExtra, ErrorLogExtra
from infrastructure.db import create_db_connection
from infrastructure.repository.guest_users_conversation_history_repository import (
    GuestUsersConversationHistoryRepository,
)
from infrastructure.repository.cat_message_repository import CatMessageRepository
from domain.unique_id import is_uuid_format
from domain.message import is_message
from domain.cat import CatId
from domain.repository.cat_message_repository_interface import (
    CreateMessageForGuestUserDto,
)
from domain.repository.cat_message_repository_interface import CatResponseMessage

app = FastAPI(
    title="AI Cat API",
)

app_logger = AppLogger()

logger = app_logger.logger

API_CREDENTIAL = os.environ["API_CREDENTIAL"]


class FetchCatMessagesRequestBody(BaseModel):
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


def format_sse(response_body: Dict[str, Any]) -> str:
    json_body = json.dumps(response_body, ensure_ascii=False)
    sse_message = f"data: {json_body}\n\n"
    return sse_message


def generate_error_response(
    response_body: Dict[str, Any]
) -> Generator[str, None, None]:
    yield format_sse(response_body)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    invalid_params = []

    errors = exc.errors()

    for error in errors:
        invalid_params.append({"name": error["loc"][1], "reason": error["msg"]})

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder(
            {
                "type": "UNPROCESSABLE_ENTITY",
                "title": "validation Error.",
                "invalidParams": invalid_params,
            }
        ),
    )


@app.post("/cats/{cat_id}/streaming-messages", status_code=status.HTTP_200_OK)
async def cats_streaming_messages(
    request: Request, cat_id: CatId, request_body: FetchCatMessagesRequestBody
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
        extra = ErrorLogExtra(
            request_id=response_headers["Ai-Meow-Cat-Request-Id"],
            conversation_id=conversation_id,
            cat_id=cat_id,
            user_id=request_body.userId,
            user_message=request_body.message,
        )

        logger.error(
            f"An error occurred while connecting to the database: {str(e)}",
            exc_info=True,
            extra=extra.model_dump(),
        )

        error_response_body = {
            "type": "INTERNAL_SERVER_ERROR",
            "title": "an unexpected error has occurred.",
            "detail": str(e),
        }

        return StreamingResponse(
            content=generate_error_response(error_response_body),
            media_type="text/event-stream",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            headers=response_headers,
        )

    async def event_stream() -> AsyncGenerator[CatResponseMessage, None]:
        try:
            # AIの応答を一時的に保存するためのリスト
            ai_responses = []

            # AIの応答を結合するための変数
            ai_response_message = ""

            cat_message_repository = CatMessageRepository()

            create_message_for_guest_user_dto = CreateMessageForGuestUserDto(
                user_id=request_body.userId,
                chat_messages=chat_messages,
            )

            ai_response_id = ""
            async for chunk in cat_message_repository.create_message_for_guest_user(
                create_message_for_guest_user_dto
            ):
                # AIの応答を更新
                ai_response_message += chunk.get("message")

                if ai_response_id == "":
                    ai_response_id = chunk.get("ai_response_id")

                chunk_body = {
                    "conversationId": conversation_id,
                    "message": chunk.get("message"),
                }

                yield format_sse(chunk_body)

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

            extra = SuccessLogExtra(
                request_id=response_headers.get("Ai-Meow-Cat-Request-Id"),
                conversation_id=conversation_id,
                cat_id=cat_id,
                user_id=request_body.userId,
                ai_response_id=ai_response_id,
            )

            logger.info(
                "success",
                extra=extra.model_dump(),
            )
        except Exception as e:
            await connection.rollback()

            extra = ErrorLogExtra(
                request_id=response_headers.get("Ai-Meow-Cat-Request-Id"),
                conversation_id=conversation_id,
                cat_id=cat_id,
                user_id=request_body.userId,
                user_message=request_body.message,
            )

            logger.error(
                f"An error occurred while creating the message: {str(e)}",
                exc_info=True,
                extra=extra.model_dump(),
            )

            error_response_body = {
                "type": "INTERNAL_SERVER_ERROR",
                "title": "an unexpected error has occurred.",
                "detail": str(e),
            }

            yield format_sse(error_response_body)
        finally:
            connection.close()

    return StreamingResponse(
        event_stream(), media_type="text/event-stream", headers=response_headers
    )


def start():
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    start()
