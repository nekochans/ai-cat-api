from fastapi import APIRouter, status, Request, Depends, Path
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBasicCredentials
from presentation.auth import basic_auth
from presentation.controller.generate_cat_message_for_guest_user_controller import (
    GenerateCatMessageForGuestUserRequestBody,
    GenerateCatMessageForGuestUserController,
    GenerateCatMessageForGuestUserSuccessResponseBody,
)
from presentation.error_response_body import (
    UnauthorizedError,
    ValidationErrorBody,
    UnexpectedErrorBody,
)
from domain.cat import CatId

router = APIRouter()


@router.post(
    "/cats/{cat_id}/messages-for-guest-users",
    tags=["cats"],
    status_code=status.HTTP_200_OK,
    response_model=GenerateCatMessageForGuestUserSuccessResponseBody,
    responses={
        status.HTTP_401_UNAUTHORIZED: {
            "model": UnauthorizedError,
            "description": "Authorization Headerが正常に設定されていない場合のレスポンス。",
        },
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "model": ValidationErrorBody,
            "description": "Validation Error時のレスポンス。",
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "model": UnexpectedErrorBody,
            "description": "予期せぬErrorが発生した時のレスポンス。",
        },
    },
)
async def generate_cat_message_for_guest_user(
    request: Request,
    request_body: GenerateCatMessageForGuestUserRequestBody,
    cat_id: CatId = Path(
        description="ねこのID .e.g. 'moko'",
        example="4ae80b0f-2e10-4d0d-938e-2c8b0d7a55a1",
    ),
    credentials: HTTPBasicCredentials = Depends(basic_auth),
) -> StreamingResponse:
    """
    このエンドポイントはねこ型AIアシスタントのメッセージを生成します。
    ゲストユーザー向けの機能です。よって画像や音声データの送信は不可となっています。

    OpenAPIでは表現方法が分からないのでJSON形式になっていますが、実際にはServer Sent Events(SSE)形式のレスポンスが返却されます。

    < HTTP/1.1 200 OK \n
    < date: Wed, 12 Jun 2024 15:49:51 GMT \n
    < server: uvicorn \n
    < ai-meow-cat-request-id: dc2054fa-4edd-42d2-a687-cff529456c0d \n
    < content-type: text/event-stream; charset=utf-8 \n
    < Transfer-Encoding: chunked \n
    < \n
    data: {"conversationId": "dc2054fa-4edd-42d2-a687-cff529456c0d", "message": "こんにちは"} \n
    data: {"conversationId": "dc2054fa-4edd-42d2-a687-cff529456c0d", "message": "、"} \n
    """

    controller = GenerateCatMessageForGuestUserController(cat_id, request_body)

    return await controller.exec()
