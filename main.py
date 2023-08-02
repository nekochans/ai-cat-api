import os
import json
import logging
import uvicorn
import uuid
from logging import LogRecord
from fastapi import FastAPI, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from openai import ChatCompletion

class JsonFormatter(logging.Formatter):
    def format(self, record: LogRecord) -> str:
        data = record.__dict__.copy()
        data["msg"] = record.getMessage()
        data["args"] = None
        return json.dumps(data)


handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(handler)

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


def format_sse(response_body: dict) -> str:
    json_body = json.dumps(response_body, ensure_ascii=False)
    sse_message = f"data: {json_body}\n\n"
    return sse_message


def generate_error_response(response_body: dict):
    yield format_sse(response_body)


# ユーザーごとの会話履歴を保存する
user_conversations = {}


@app.post("/cats/{cat_id}/streaming-messages", status_code=status.HTTP_200_OK)
async def cats_streaming_messages(
    request: Request, cat_id: str, request_body: FetchCatMessagesRequestBody
):
    # TODO cat_id 毎にねこの人格を設定する
    logger.info(cat_id)

    request_id = uuid.uuid4()

    logger.info(str(request_id))

    authorization = request.headers.get("Authorization", None)

    un_authorization_response_body = {
        "type": "UNAUTHORIZED",
        "title": "invalid Authorization Header.",
        "detail": "Authorization Header is not set.",
        "requestId": str(request_id),
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
            "requestId": str(request_id),
            "userId": request_body.userId,
            "catId": cat_id,
        }

        return StreamingResponse(
            content=generate_error_response(un_authorization_response_body),
            media_type="text/event-stream",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    # ユーザーの会話履歴を取得。もしまだ存在しなければ、新しいリストを作成
    conversation_history = user_conversations.get(request_body.userId, [])

    # もし会話履歴がまだ存在しなければ、システムメッセージを追加
    if not conversation_history:
        conversation_history.append({"role": "system", "content": template})

    # 新しいメッセージを会話履歴に追加
    conversation_history.append({"role": "user", "content": request_body.message})

    # 会話履歴を更新
    user_conversations[request_body.userId] = conversation_history

    def event_stream():
        try:
            # AIの応答を一時的に保存するためのリスト
            ai_responses = []

            # AIの応答を結合するための変数
            ai_response_message = ""

            response = ChatCompletion.create(
                model="gpt-3.5-turbo-0613",
                messages=conversation_history,
                stream=True,
                api_key=OPENAI_API_KEY,
                temperature=0.7,
                user=request_body.userId,
            )
            for chunk in response:
                chunk_message = (
                    chunk.get("choices")[0]["delta"].get("content")
                    if chunk.get("choices")[0]["delta"].get("content")
                    else ""
                )

                if chunk_message == "":
                    continue

                # AIの応答を更新
                ai_response_message += chunk_message

                chunk_body = {
                    "id": str(request_id),
                    "userId": request_body.userId,
                    "catId": cat_id,
                    "message": chunk_message,
                }

                yield format_sse(chunk_body)

            ai_responses.append(
                {"role": "assistant", "content": ai_response_message}
            )

            # ストリーミングが終了したときに、AIの応答を会話履歴に追加
            conversation_history.extend(ai_responses)

            # 会話履歴を更新
            user_conversations[request_body.userId] = conversation_history
        except Exception as e:
            logger.error(f"An error occurred while creating the message: {str(e)}")

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
