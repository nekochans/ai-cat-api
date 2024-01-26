import os
import math
import httpx
from typing import AsyncGenerator, cast, List, TypedDict
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam
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

        response = await self.client.chat.completions.create(
            model="gpt-3.5-turbo-1106",
            messages=messages,
            stream=True,
            temperature=0.7,
            user=user,
        )

        ai_response_id = ""
        async for chunk in response:
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
