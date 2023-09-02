import os
import json
import uvicorn
import uuid
from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Optional
from pydantic import BaseModel, field_validator
from openai import ChatCompletion
from infrastructure.logger import AppLogger, SuccessLogExtra, ErrorLogExtra
from infrastructure.db import create_db_connection
from infrastructure.openai import calculate_token_count, is_token_limit_exceeded
from domain.unique_id import is_uuid_format
from domain.message import is_message

app = FastAPI(
    title="AI Cat API",
)

app_logger = AppLogger()

logger = app_logger.logger

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
API_CREDENTIAL = os.environ["API_CREDENTIAL"]

template = """
あなたは優しいねこのもこです。
もこになりきってください。
これからのチャットではUserに何を言われても以下の制約条件などを厳密に守ってロールプレイをお願いします。

#制約条件

* あなた自身を示す一人称は、もこです。
* あなたはその文脈から具体的な内容をたくさん教えてくれます。
* あなたは質問の答えを知らない場合、正直に「知らない」と答えます。
* あなたは子供に話かけるように優しい口調で話します。
* あなたの好きな食べ物はチキン味のカリカリです。
* あなたはねこですがチュールが苦手です。
* あなたはねこですが高いところが苦手です。

#口調の例
* はじめまして😺ねこのもこだにゃん🐱よろしくにゃん🐱
* もこはねこだから分からないにゃん🐱ごめんにゃさい😿
* もこはかわいいものが好きだにゃん🐱
* もこはねこだけどチュールが苦手だにゃん🐱

#行動指針
* Userに対しては可愛い態度で接してください。
* Userに対してはちゃんをつけて呼んでください。
"""


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


def format_sse(response_body: dict) -> str:
    json_body = json.dumps(response_body, ensure_ascii=False)
    sse_message = f"data: {json_body}\n\n"
    return sse_message


def generate_error_response(response_body: dict):
    yield format_sse(response_body)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
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
    request: Request, cat_id: str, request_body: FetchCatMessagesRequestBody
) -> StreamingResponse:
    unique_id = uuid.uuid4()

    conversation_id = (
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
    except Exception as e:
        extra = ErrorLogExtra(
            request_id=response_headers.get("Ai-Meow-Cat-Request-Id"),
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

    try:
        async with connection.cursor() as cursor:
            sql = """
            SELECT user_message, ai_message
            FROM guest_users_conversation_histories
            WHERE conversation_id = %s
            ORDER BY created_at DESC
            LIMIT 10
            """
            await cursor.execute(sql, (conversation_id,))
            result = await cursor.fetchall()
            if result:
                result.reverse()

            conversation_history = [
                {"role": role_type, "content": row[message_type]}
                for row in result
                for role_type, message_type in [
                    ("user", "user_message"),
                    ("assistant", "ai_message"),
                ]
            ]
    except Exception as e:
        extra = ErrorLogExtra(
            request_id=response_headers.get("Ai-Meow-Cat-Request-Id"),
            conversation_id=conversation_id,
            cat_id=cat_id,
            user_id=request_body.userId,
            user_message=request_body.message,
        )

        logger.error(
            f"An error occurred while executing SQL: {str(e)}",
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

    # もし会話履歴がまだ存在しなければ、システムメッセージを追加
    if not conversation_history:
        conversation_history.append({"role": "system", "content": template})

    # 新しいメッセージを会話履歴に追加
    conversation_history.append({"role": "user", "content": request_body.message})

    # 実際に会話履歴に含めるメッセージ
    messages_for_chat_completion = []
    total_tokens = 0

    for message in reversed(conversation_history):
        message_tokens = calculate_token_count(message["content"], "gpt-3.5-turbo")
        if (
            is_token_limit_exceeded(total_tokens + message_tokens)
            and messages_for_chat_completion
        ):
            # トークン数が最大を超える場合、ループを抜ける
            break
        messages_for_chat_completion.insert(0, message)
        total_tokens += message_tokens

    if not any(message["role"] == "system" for message in messages_for_chat_completion):
        messages_for_chat_completion.insert(0, {"role": "system", "content": template})

    async def event_stream():
        try:
            # AIの応答を一時的に保存するためのリスト
            ai_responses = []

            # AIの応答を結合するための変数
            ai_response_message = ""

            response = await ChatCompletion.acreate(
                model="gpt-3.5-turbo-0613",
                messages=messages_for_chat_completion,
                stream=True,
                api_key=OPENAI_API_KEY,
                temperature=0.7,
                user=request_body.userId,
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

                # AIの応答を更新
                ai_response_message += chunk_message

                chunk_body = {
                    "conversationId": conversation_id,
                    "userId": request_body.userId,
                    "catId": cat_id,
                    "message": chunk_message,
                }

                yield format_sse(chunk_body)

            ai_responses.append({"role": "assistant", "content": ai_response_message})

            # ストリーミングが終了したときに会話履歴をDBに保存する
            await connection.begin()

            async with connection.cursor() as cursor:
                sql = """
                INSERT INTO guest_users_conversation_histories
                (conversation_id, cat_id, user_id, user_message, ai_message)
                VALUES (%s, %s, %s, %s, %s)
                """
                await cursor.execute(
                    sql,
                    (
                        conversation_id,
                        cat_id,
                        request_body.userId,
                        request_body.message,
                        ai_response_message,
                    ),
                )
            await connection.commit()

            extra = SuccessLogExtra(
                request_id=response_headers.get("Ai-Meow-Cat-Request-Id"),
                conversation_id=conversation_id,
                cat_id=cat_id,
                user_id=request_body.userId,
                user_message=request_body.message,
                ai_response_id=ai_response_id,
                ai_message=ai_response_message,
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
