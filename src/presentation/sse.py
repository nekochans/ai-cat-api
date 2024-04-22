# Server Sent Events(SSE)のレスポンスを生成する為の関数郡
import json
from typing import Any, Dict, Generator



def format_sse(response_body: Dict[str, Any]) -> str:
    json_body = json.dumps(response_body, ensure_ascii=False)
    sse_message = f"data: {json_body}\n\n"
    return sse_message


def generate_error_response(
    response_body: Dict[str, Any],
) -> Generator[str, None, None]:
    yield format_sse(response_body)
