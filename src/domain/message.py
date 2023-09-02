from typing import Literal, TypedDict


def is_message(value: str) -> bool:
    return 2 <= len(value) <= 5000


class ChatMessage(TypedDict):
    role: Literal["system", "user", "assistant"]
    content: str
