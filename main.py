import os
import json
import logging
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from langchain.chat_models import ChatOpenAI
from langchain.chains import ConversationChain
from langchain.memory import ConversationTokenBufferMemory
from langchain.prompts.chat import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)


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


def create_conversational_chain():
    llm = ChatOpenAI(temperature=0.7, openai_api_key=OPENAI_API_KEY)

    memory = ConversationTokenBufferMemory(
        llm=llm, return_messages=True, max_token_limit=2000
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            SystemMessagePromptTemplate.from_template(template),
            MessagesPlaceholder(variable_name="history"),
            HumanMessagePromptTemplate.from_template("{input}"),
        ]
    )

    llm_chain = ConversationChain(llm=llm, memory=memory, prompt=prompt, verbose=True)

    return llm_chain


chain = create_conversational_chain()


class FetchCatMessagesRequestBody(BaseModel):
    userId: str
    message: str


@app.post("/cats/{cat_id}/messages")
async def cats_messages(
    request: Request, cat_id: str, request_body: FetchCatMessagesRequestBody
):
    # TODO cat_id 毎にねこの人格を設定する
    logger.info(cat_id)
    logger.info(request_body.userId)

    authorization = request.headers.get("Authorization", None)

    print(authorization)

    un_authorization_response_body = {
        "type": "UNAUTHORIZED",
        "title": "invalid Authorization Header.",
    }

    if authorization is None:
        return JSONResponse(content=un_authorization_response_body, status_code=401)

    authorization_headers = authorization.split(" ")

    if len(authorization_headers) != 2 or authorization_headers[0] != "Basic":
        return JSONResponse(content=un_authorization_response_body, status_code=401)

    if authorization_headers[1] != API_CREDENTIAL:
        return JSONResponse(content=un_authorization_response_body, status_code=401)

    try:
        llm_response = chain.predict(input=request_body.message)
    except Exception as e:
        logger.error(e)

        error_message = f"An error occurred: {str(e)}"
        response_body = {
            "type": "INTERNAL_SERVER_ERROR",
            "title": "an unexpected error has occurred.",
            "detail": error_message,
        }
        return JSONResponse(content=response_body, status_code=500)

    response_body = {
        "message": llm_response,
    }

    response = JSONResponse(content=response_body, status_code=201)

    return response


def start():
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    start()
