from fastapi import APIRouter, status, Request, Depends
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBasicCredentials
from presentation.auth import basic_auth
from presentation.controller.generate_cat_message_for_guest_user_controller import (
    GenerateCatMessageForGuestUserRequestBody,
    GenerateCatMessageForGuestUserController,
)
from domain.cat import CatId

router = APIRouter()


@router.post(
    "/cats/{cat_id}/messages-for-guest-users",
    tags=["cats"],
    status_code=status.HTTP_200_OK,
)
async def generate_cat_message_for_guest_user(
    request: Request,
    cat_id: CatId,
    request_body: GenerateCatMessageForGuestUserRequestBody,
    credentials: HTTPBasicCredentials = Depends(basic_auth),
) -> StreamingResponse:
    controller = GenerateCatMessageForGuestUserController(cat_id, request_body)

    return await controller.exec()
