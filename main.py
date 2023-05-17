import threading
import queue
import os
import json

import uvicorn

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from langchain.chat_models import ChatOpenAI
from langchain.callbacks.manager import CallbackManager
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler
from langchain.schema import HumanMessage, SystemMessage

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


def llm_thread(g, prompt):
    try:
        chat = ChatOpenAI(
            verbose=True,
            streaming=True,
            callback_manager=CallbackManager([ChainStreamHandler(g)]),
            openai_api_key=OPENAI_API_KEY,
            temperature=0.7,
        )
        chat(
            [
                SystemMessage(content="You are a poetic assistant"),
                HumanMessage(content=prompt),
            ]
        )
    finally:
        g.close()


def chat(prompt):
    g = ThreadedGenerator()
    threading.Thread(target=llm_thread, args=(g, prompt)).start()
    for message in g:
        yield f"data: {json.dumps({'message': message, 'id': 'xxxxxxxx-xxxxxxxxx-xxxxxxxxxxxxxxxxx'}, ensure_ascii=False)}\n\n"


class Message(BaseModel):
    message: str


@app.post("/question-stream")
async def stream(message: Message):
    return StreamingResponse(chat(message.message), media_type="text/event-stream")


def start():
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    start()
