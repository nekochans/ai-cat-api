from typing import Literal
import tiktoken


def calculate_token_count(text: str, model: Literal["gpt-4", "gpt-3.5-turbo"]) -> int:
    tiktoken_encoding = tiktoken.encoding_for_model(model)
    encoded = tiktoken_encoding.encode(text)
    return len(encoded)


def is_token_limit_exceeded(use_token: int) -> bool:
    # 最大トークン数
    max_token_limit = 1000

    return use_token > max_token_limit
