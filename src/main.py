import os
import json
import uvicorn
import uuid
from fastapi import FastAPI, Request, status
from fastapi.responses import StreamingResponse
from typing import Optional
from pydantic import BaseModel
from openai import ChatCompletion
import tiktoken
from logger import logger

app = FastAPI(
    title="AI Cat API",
)

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


def format_sse(response_body: dict) -> str:
    json_body = json.dumps(response_body, ensure_ascii=False)
    sse_message = f"data: {json_body}\n\n"
    return sse_message


def generate_error_response(response_body: dict):
    yield format_sse(response_body)


# ユーザーごとの会話履歴を保存する
user_conversations = {}


def calculate_token_count(text: str) -> int:
    tiktoken_encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
    encoded = tiktoken_encoding.encode(text)
    return len(encoded)


# 最大トークン数
max_token_limit = 1000


@app.post("/cats/{cat_id}/streaming-messages", status_code=status.HTTP_200_OK)
async def cats_streaming_messages(
    request: Request, cat_id: str, request_body: FetchCatMessagesRequestBody
):
    unique_id = uuid.uuid4()

    conversation_id = (
        str(unique_id)
        if request_body.conversationId is None
        else request_body.conversationId
    )

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
        )

    authorization_headers = authorization.split(" ")

    if len(authorization_headers) != 2 or authorization_headers[0] != "Basic":
        return StreamingResponse(
            content=generate_error_response(un_authorization_response_body),
            media_type="text/event-stream",
            status_code=status.HTTP_401_UNAUTHORIZED,
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
        )

    # ユーザーの会話履歴を取得。もしまだ存在しなければ、新しいリストを作成
    conversation_history = user_conversations.get(conversation_id, [])

    # もし会話履歴がまだ存在しなければ、システムメッセージを追加
    if not conversation_history:
        conversation_history.append({"role": "system", "content": template})

    # 新しいメッセージを会話履歴に追加
    conversation_history.append({"role": "user", "content": request_body.message})

    # 会話履歴を更新
    user_conversations[conversation_id] = conversation_history

    # 実際に会話履歴に含めるメッセージ
    messages_for_chat_completion = []
    total_tokens = 0

    for message in reversed(conversation_history):
        message_tokens = calculate_token_count(message["content"])
        if (
            total_tokens + message_tokens > max_token_limit
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

            # ストリーミングが終了したときに、AIの応答を会話履歴に追加
            conversation_history.extend(ai_responses)

            # 会話履歴を更新
            user_conversations[conversation_id] = conversation_history

            logger.info(
                "success",
                extra={
                    "conversation_id": conversation_id,
                    "user_id": request_body.userId,
                    "user_message": request_body.message,
                    "ai_response_id": ai_response_id,
                    "ai_message": ai_response_message,
                },
            )
        except Exception as e:
            logger.error(
                f"An error occurred while creating the message: {str(e)}",
                exc_info=True,
                extra={
                    "conversation_id": conversation_id,
                    "user_id": request_body.userId,
                    "user_message": request_body.message,
                },
            )

            error_response_body = {
                "type": "INTERNAL_SERVER_ERROR",
                "title": "an unexpected error has occurred.",
                "detail": str(e),
            }

            yield format_sse(error_response_body)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def start():
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    start()
