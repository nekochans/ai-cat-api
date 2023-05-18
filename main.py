import threading
import queue
import os
import json
import logging
import uvicorn
from typing import Dict, List

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from langchain.chat_models import ChatOpenAI
from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.schema import HumanMessage, SystemMessage


class JsonFormatter(logging.Formatter):
    def format(self, record):
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


class ThreadedGenerator:
    def __init__(self):
        self.queue = queue.Queue()

    def __iter__(self):
        return self

    def __next__(self):
        item = self.queue.get()
        if item is StopIteration:
            raise item
        return item

    def send(self, data):
        self.queue.put(data)

    def close(self):
        self.queue.put(StopIteration)


class ChainStreamHandler(StreamingStdOutCallbackHandler):
    def __init__(self, gen):
        super().__init__()
        self.gen = gen

    def on_llm_new_token(self, token: str, **kwargs):
        self.gen.send(token)


OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

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

# とりあえず仮でオンメモリで会話履歴を持つ
user_conversations: Dict[str, List[HumanMessage or SystemMessage]] = {}


def llm_thread(g, user_id, prompt):
    try:
        conversation = user_conversations.get(
            user_id, [SystemMessage(content=template)]
        )

        conversation.append(HumanMessage(content=prompt))

        user_conversations[user_id] = conversation

        chat_model = ChatOpenAI(
            verbose=True,
            streaming=True,
            callback_manager=CallbackManager([ChainStreamHandler(g)]),
            openai_api_key=OPENAI_API_KEY,
            temperature=0.7,
        )
        chat_model(conversation)
    finally:
        g.close()


def format_sse(response_body: dict) -> str:
    json_body = json.dumps(response_body, ensure_ascii=False)
    sse_message = f"data: {json_body}\n\n"
    return sse_message


def chat(user_id: str, cat_id: str, prompt: str):
    g = ThreadedGenerator()
    threading.Thread(target=llm_thread, args=(g, user_id, prompt)).start()
    for message in g:
        # TODO idをどうやって生成するかは後で考える
        yield format_sse(
            {
                "id": "xxxxxxxx-xxxxxxxxx-xxxxxxxxxxxxxxxxx",
                "userId": user_id,
                "catId": cat_id,
                "message": message,
            }
        )


class Message(BaseModel):
    userId: str
    message: str


@app.post("/cats/{cat_id}/streaming-messages")
async def cats_streaming_messages(cat_id: str, message: Message):
    # TODO cat_id 毎にねこの人格を設定する
    logger.info(cat_id)

    return StreamingResponse(
        chat(message.userId, cat_id, message.message), media_type="text/event-stream"
    )


def start():
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    start()
