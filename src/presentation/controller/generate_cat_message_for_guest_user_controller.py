from typing import Optional, AsyncGenerator, cast
from fastapi import status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
from presentation.sse import format_sse, generate_error_response
from domain.cat import CatId
from domain.unique_id import is_uuid_format, generate_unique_id
from domain.message import is_message
from infrastructure.db import create_db_connection
from infrastructure.repository.aiomysql.aiomysql_db_handler import AiomysqlDbHandler
from infrastructure.repository.aiomysql.aiomysql_guest_users_conversation_history_repository import (
    AiomysqlGuestUsersConversationHistoryRepository,
)
from infrastructure.repository.openai.openai_cat_message_repository import (
    OpenAiCatMessageRepository,
)
from log.logger import AppLogger, ErrorLogExtra
from usecase.generate_cat_message_for_guest_user_use_case import (
    GenerateCatMessageForGuestUserUseCase,
    GenerateCatMessageForGuestUserUseCaseDto,
    GenerateCatMessageForGuestUserUseCaseResult,
    GenerateCatMessageForGuestUserUseCaseErrorResult,
    GenerateCatMessageForGuestUserUseCaseSuccessResult,
    is_success_result,
    is_error_result,
)


class GenerateCatMessageForGuestUserRequestBody(BaseModel):
    userId: str
    message: str
    conversationId: Optional[str] = None

    @field_validator("userId", "conversationId")
    @classmethod
    def validate_uuid(cls, v: str) -> str:
        if not is_uuid_format(v):
            raise ValueError(f"'{v}' is not in UUID format")
        return v

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        if not is_message(v):
            raise ValueError(
                "message must be at least 2 character and no more than 5,000 characters"
            )
        return v


class GenerateCatMessageForGuestUserSuccessResponseBody(BaseModel):
    conversationId: str
    message: str


class GenerateCatMessageForGuestUserErrorResponseBody(BaseModel):
    type: str
    title: str


class GenerateCatMessageForGuestUserController:
    def __init__(
        self, cat_id: CatId, request_body: GenerateCatMessageForGuestUserRequestBody
    ) -> None:
        app_logger = AppLogger()
        self.logger = app_logger.logger
        self.cat_id = cat_id
        self.request_body = request_body

    async def exec(self) -> StreamingResponse:
        unique_id = generate_unique_id()

        conversation_id = unique_id
        if self.request_body.conversationId is not None and is_uuid_format(
            self.request_body.conversationId
        ):
            conversation_id = self.request_body.conversationId

        response_headers = {"Ai-Meow-Cat-Request-Id": unique_id}

        try:
            connection = await create_db_connection()

            db_handler = AiomysqlDbHandler(connection)

            repository = AiomysqlGuestUsersConversationHistoryRepository(connection)
        except Exception as e:
            self.logger.error(
                f"An error occurred while connecting to the database: {str(e)}",
                exc_info=True,
                extra=ErrorLogExtra(
                    request_id=response_headers["Ai-Meow-Cat-Request-Id"],
                    conversation_id=conversation_id,
                    cat_id=self.cat_id,
                    user_id=self.request_body.userId,
                    user_message=self.request_body.message,
                ),
            )

            db_error_response_body = {
                "type": "INTERNAL_SERVER_ERROR",
                "title": "an unexpected error has occurred.",
            }

            return StreamingResponse(
                content=generate_error_response(db_error_response_body),
                media_type="text/event-stream",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                headers=response_headers,
            )

        cat_message_repository = OpenAiCatMessageRepository()

        use_case_dto: GenerateCatMessageForGuestUserUseCaseDto = (
            GenerateCatMessageForGuestUserUseCaseDto(
                request_id=unique_id,
                user_id=self.request_body.userId,
                cat_id=self.cat_id,
                message=self.request_body.message,
                db_handler=db_handler,
                guest_users_conversation_history_repository=repository,
                cat_message_repository=cat_message_repository,  # type: ignore
            )
        )

        if self.request_body.conversationId is not None:
            use_case_dto["conversation_id"] = self.request_body.conversationId

        use_case = GenerateCatMessageForGuestUserUseCase(use_case_dto)

        async def generate_cat_message_for_guest_user_stream() -> AsyncGenerator[
            str, None
        ]:
            async for chunk in use_case.execute():
                use_case_result: GenerateCatMessageForGuestUserUseCaseResult = chunk

                if is_error_result(dict(use_case_result)):
                    error_result = cast(
                        GenerateCatMessageForGuestUserUseCaseErrorResult,
                        use_case_result,
                    )
                    yield format_sse(
                        GenerateCatMessageForGuestUserErrorResponseBody(
                            type=error_result["type"],
                            title=error_result["title"],
                        ).model_dump()
                    )
                    continue

                if is_success_result(dict(use_case_result)):
                    success_result = cast(
                        GenerateCatMessageForGuestUserUseCaseSuccessResult,
                        use_case_result,
                    )

                    yield format_sse(
                        GenerateCatMessageForGuestUserSuccessResponseBody(
                            conversationId=success_result["conversation_id"],
                            message=success_result["message"],
                        ).model_dump()
                    )
                    continue

        return StreamingResponse(
            generate_cat_message_for_guest_user_stream(),
            media_type="text/event-stream",
            headers=response_headers,
        )
