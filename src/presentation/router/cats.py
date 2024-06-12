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
    controller = GenerateCatMessageForGuestUserController(cat_id, request_body)

    return await controller.exec()
