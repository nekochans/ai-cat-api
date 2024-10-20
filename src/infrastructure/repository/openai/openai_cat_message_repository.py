import os
import math
import httpx
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import cast, List, TypedDict, Union
from collections.abc import AsyncIterator
from openai import AsyncOpenAI, AsyncStream
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionChunk,
    ChatCompletionToolParam,
    ChatCompletionMessageToolCall,
)
from langsmith.wrappers import wrap_openai
from langsmith import traceable
from domain.repository.cat_message_repository_interface import (
    CatMessageRepositoryInterface,
    GenerateMessageForGuestUserDto,
    GenerateMessageForGuestUserResult,
)
from domain.cat import get_prompt_by_cat_id, CatId


class FetchCurrentWeatherResponse(TypedDict):
    city_name: str
    description: str
    temperature: int


class GetCurrentDatetimeResponse(TypedDict):
    current_datetime: str


class OpenAiCatMessageRepository(CatMessageRepositoryInterface):
    def __init__(self) -> None:
        self.OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
        self.OPEN_WEATHER_API_KEY = os.environ["OPEN_WEATHER_API_KEY"]
        self.client = wrap_openai(AsyncOpenAI(api_key=self.OPENAI_API_KEY))

    @traceable
    async def generate_message_for_guest_user(
        self, dto: GenerateMessageForGuestUserDto
    ) -> AsyncIterator[GenerateMessageForGuestUserResult]:
        messages = cast(List[ChatCompletionMessageParam], dto.get("chat_messages"))
        user = str(dto.get("user_id"))

        regenerated_messages = (
            await self._might_regenerate_messages_contain_tools_results_exec(
                dto,
                messages,
            )
        )

        response = await self.client.chat.completions.create(
            model="gpt-4o-2024-08-06",
            messages=regenerated_messages,
            stream=True,
            temperature=0.1,
            user=user,
        )

        async for generated_response in self._extract_chat_chunks(response):
            yield generated_response

    # 必要に応じてtoolsを実行してメッセージのリストにtoolsの実行結果を含めて再生成する
    @traceable
    async def _might_regenerate_messages_contain_tools_results_exec(
        self,
        dto: GenerateMessageForGuestUserDto,
        messages: List[ChatCompletionMessageParam],
    ) -> List[ChatCompletionMessageParam]:
        tools = [
            {
                "type": "function",
                "function": {
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
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_current_datetime_in_iso_format",
                    "description": "指定されたタイムゾーンの現在日時をISO 8601形式で返す。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "timezone": {
                                "type": "string",
                                "description": "タイムゾーン名: 例: Asia/Tokyo, UTC, America/New_York",
                            }
                        },
                        "required": ["timezone"],
                    },
                },
            },
        ]
        tools_params = cast(List[ChatCompletionToolParam], tools)

        copied_messages = messages.copy()

        system_prompt = """
        {base_system_prompt}
        # Output Indicator
        以下のようなJSON形式でお願いします。
        ## use_tools
        toolsの利用が必要な場合はtrue,不要な場合はfalseを設定します。
        """.format(
            base_system_prompt=get_prompt_by_cat_id(cast(CatId, dto.get("cat_id")))
        )

        copied_messages[0] = {
            "role": "system",
            "content": system_prompt,
        }

        response = await self.client.chat.completions.create(
            model="gpt-4o-2024-08-06",
            messages=copied_messages,
            temperature=0,
            user=str(dto.get("user_id")),
            tools=tools_params,
            tool_choice="auto",
            response_format={"type": "json_object"},
        )

        tool_response_messages = []
        if response.choices[0].finish_reason == "tool_calls":
            tool_calls = response.choices[0].message.tool_calls

            if tool_calls is None:
                return messages

            for tool_call in tool_calls:
                tool_call_response = await self._might_call_tool(tool_call)
                if tool_call_response is not None:
                    tool_response_messages.append(
                        {
                            "tool_call_id": tool_call.id,
                            "role": "tool",
                            "content": json.dumps(
                                tool_call_response, ensure_ascii=False
                            ),
                        }
                    )
            # tools（Function calling等）の実行結果を含めて再生成したメッセージのリストを返す
            regenerated_messages = [
                *messages,
                response.choices[0].message,
                *tool_response_messages,
            ]

            return cast(List[ChatCompletionMessageParam], regenerated_messages)

        # ここに来たという事はtoolsの実行が必要ないという事なので、引数で渡されたmessagesをそのまま返す
        return messages

    async def _might_call_tool(
        self, tool_call: ChatCompletionMessageToolCall
    ) -> Union[None, FetchCurrentWeatherResponse, GetCurrentDatetimeResponse]:
        if tool_call.type == "function":
            return await self._might_call_function(tool_call)

    async def _might_call_function(
        self,
        tool_call: ChatCompletionMessageToolCall,
    ) -> Union[None, FetchCurrentWeatherResponse, GetCurrentDatetimeResponse]:
        if tool_call.function.name == "fetch_current_weather":
            function_arguments = json.loads(tool_call.function.arguments)
            city_name = function_arguments["city_name"]
            return await self._fetch_current_weather(city_name)

        if tool_call.function.name == "get_current_datetime_in_iso_format":
            function_arguments = json.loads(tool_call.function.arguments)
            timezone = function_arguments["timezone"]
            return await self._get_current_datetime_in_iso_format(timezone)

        return None

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
    async def _get_current_datetime_in_iso_format(
        timezone: str,
    ) -> GetCurrentDatetimeResponse:
        current_datetime = datetime.now(ZoneInfo(timezone))

        return {
            "current_datetime": current_datetime.isoformat(),
        }

    @staticmethod
    async def _extract_chat_chunks(
        async_stream: AsyncStream[ChatCompletionChunk],
    ) -> AsyncIterator[GenerateMessageForGuestUserResult]:
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
