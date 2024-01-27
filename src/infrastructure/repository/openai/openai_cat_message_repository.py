import os
import math
import httpx
import json
from typing import AsyncGenerator, cast, List, TypedDict
from openai import AsyncOpenAI, AsyncStream
from openai.types.chat import ChatCompletionMessageParam, ChatCompletionChunk
from domain.repository.cat_message_repository_interface import (
    CatMessageRepositoryInterface,
    GenerateMessageForGuestUserDto,
    GenerateMessageForGuestUserResult,
)


class FetchCurrentWeatherResponse(TypedDict):
    city_name: str
    description: str
    temperature: int


class OpenAiCatMessageRepository(CatMessageRepositoryInterface):
    def __init__(self) -> None:
        self.OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
        self.OPEN_WEATHER_API_KEY = os.environ["OPEN_WEATHER_API_KEY"]
        self.client = AsyncOpenAI(api_key=self.OPENAI_API_KEY)

    # TODO: 型は合っているのに型チェックエラーが出る mypy が AsyncGenerator に対応していない可能性がある
    # TODO: https://github.com/nekochans/ai-cat-api/issues/68 で別の型チェックツールを試してみる
    async def generate_message_for_guest_user(  # type: ignore
        self, dto: GenerateMessageForGuestUserDto
    ) -> AsyncGenerator[GenerateMessageForGuestUserResult, None]:
        messages = cast(List[ChatCompletionMessageParam], dto.get("chat_messages"))
        user = str(dto.get("user_id"))

        functions = [
            {
                "name": "fetch_current_weather",
                "description": "指定された都市の現在の天気を取得する。（日本の都市の天気しか取得出来ない）",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city_name": {
                            "type": "string",
                            "description": "英語表記の日本の都市名",
                        }
                    },
                    "required": ["city_name"],
                },
            }
        ]

        response = await self.client.chat.completions.create(
            model="gpt-3.5-turbo-1106",
            messages=messages,
            stream=True,
            temperature=0.7,
            user=user,
            functions=functions,
            function_call="auto",
        )

        function_info = {
            "name": None,
            "arguments": "",
        }

        async for chunk in response:
            function_call = chunk.choices[0].delta.function_call

            if function_call:
                if function_call.name is not None and function_call.name != "":
                    function_info["name"] = function_call.name
                if (
                    function_call.arguments is not None
                    and function_call.arguments != ""
                ):
                    function_info["arguments"] += function_call.arguments
                continue

            if chunk.choices[0].finish_reason == "function_call":
                if function_info["name"] == "fetch_current_weather":
                    city_name = json.loads(function_info["arguments"])["city_name"]
                    function_response = await self._fetch_current_weather(city_name)

                    function_result_message = {
                        "role": "function",
                        "name": function_info["name"],
                        "content": json.dumps(function_response, ensure_ascii=False),
                    }

                    messages.append(function_result_message)
                    response = await self.client.chat.completions.create(
                        model="gpt-3.5-turbo-1106",
                        messages=messages,
                        stream=True,
                        temperature=0.7,
                        user=user,
                    )

                    async for generated_response in self._extract_chat_chunks(response):
                        yield generated_response
                    continue

            async for generated_response in self._extract_chat_chunks(response):
                yield generated_response

    async def _fetch_current_weather(
        self, city_name: str = "Tokyo"
    ) -> FetchCurrentWeatherResponse:
        async with httpx.AsyncClient() as client:
            geocoding_response = await client.get(
                "http://api.openweathermap.org/geo/1.0/direct",
                params={
                    "q": city_name + ",jp",
                    "limit": 1,
                    "appid": self.OPEN_WEATHER_API_KEY,
                },
            )
            geocoding_list = geocoding_response.json()
            geocoding = geocoding_list[0]
            lat, lon = geocoding["lat"], geocoding["lon"]

            current_weather_response = await client.get(
                "https://api.openweathermap.org/data/2.5/weather",
                params={
                    "lat": lat,
                    "lon": lon,
                    "units": "metric",
                    "lang": "ja",
                    "appid": self.OPEN_WEATHER_API_KEY,
                },
            )
            current_weather = current_weather_response.json()

            return {
                "city_name": city_name,
                "description": current_weather["weather"][0]["description"],
                "temperature": math.floor(current_weather["main"]["temp"]),
            }

    @staticmethod
    async def _extract_chat_chunks(async_stream: AsyncStream[ChatCompletionChunk]):
        ai_response_id = ""
        async for chunk in async_stream:
            chunk_message: str = (
                chunk.choices[0].delta.content
                if chunk.choices[0].delta.content is not None
                else ""
            )

            if ai_response_id == "":
                ai_response_id = chunk.id

            if chunk_message == "":
                continue

            chunk_body: GenerateMessageForGuestUserResult = {
                "ai_response_id": ai_response_id,
                "message": chunk_message,
            }

            yield chunk_body
