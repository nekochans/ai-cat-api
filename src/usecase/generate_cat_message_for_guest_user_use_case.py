from typing import TypedDict, AsyncGenerator
from usecase.db_handler_interface import DbHandlerInterface
from usecase.error.create_messages_with_conversation_history_error import (
    CreateMessagesWithConversationHistoryError,
)
from domain.repository.guest_users_conversation_history_repository_interface import (
    GuestUsersConversationHistoryRepositoryInterface,
)
from domain.repository.cat_message_repository_interface import (
    CatMessageRepositoryInterface,
    GenerateMessageForGuestUserDto,
)
from domain.cat import CatId
from log.logger import AppLogger, ErrorLogExtra, SuccessLogExtra


class GenerateCatMessageForGuestUserUseCaseDtoRequiredType(TypedDict):
    request_id: str
    user_id: str
    cat_id: CatId
    message: str
    db_handler: DbHandlerInterface
    guest_users_conversation_history_repository: GuestUsersConversationHistoryRepositoryInterface
    cat_message_repository: CatMessageRepositoryInterface


class GenerateCatMessageForGuestUserUseCaseDtoOptionalType(TypedDict, total=False):
    conversation_id: str


class GenerateCatMessageForGuestUserUseCaseDto(
    GenerateCatMessageForGuestUserUseCaseDtoRequiredType,
    GenerateCatMessageForGuestUserUseCaseDtoOptionalType,
):
    pass


class GenerateCatMessageForGuestUserUseCase:
    def __init__(self, dto: GenerateCatMessageForGuestUserUseCaseDto) -> None:
        app_logger = AppLogger()
        self.logger = app_logger.logger
        self.dto = dto

    async def execute(self) -> AsyncGenerator[str, None]:
        conversation_id: str = self.dto["request_id"]
        if self.dto.get("conversation_id") is not None:
            conversation_id = self.dto.get("conversation_id")

        try:
            chat_messages = await self.dto[
                "guest_users_conversation_history_repository"
            ].create_messages_with_conversation_history(
                {
                    "conversation_id": conversation_id,
                    "request_message": self.dto["message"],
                    "cat_id": self.dto.get("cat_id"),
                }
            )
        except Exception as e:
            self.logger.error(
                f"An error occurred while connecting to the database: {str(e)}",
                exc_info=True,
                extra=ErrorLogExtra(
                    request_id=self.dto["request_id"],
                    conversation_id=conversation_id,
                    cat_id=self.dto.get("cat_id"),
                    user_id=self.dto.get("user_id"),
                    user_message=self.dto.get("message"),
                ),
            )

            raise CreateMessagesWithConversationHistoryError(
                "failed to GuestUsersConversationHistoryRepository.create_messages_with_conversation_history",
                e,
            ) from e

        try:
            # AIの応答を一時的に保存するためのリスト
            ai_responses = []

            # AIの応答を結合するための変数
            ai_response_message = ""

            create_message_for_guest_user_dto = GenerateMessageForGuestUserDto(
                user_id=self.dto.get("user_id"),
                chat_messages=chat_messages,
            )

            ai_response_id = ""

            async for chunk in self.dto["cat_message_repository"].generate_message_for_guest_user(  # type: ignore
                create_message_for_guest_user_dto
            ):
                # AIの応答を更新
                ai_response_message += chunk.get("message") or ""

                if ai_response_id == "":
                    ai_response_id = chunk.get("ai_response_id") or ""

                chunk_body = {
                    "conversation_id": conversation_id,
                    "message": chunk.get("message") or "",
                }

                yield chunk_body

            ai_responses.append({"role": "assistant", "content": ai_response_message})

            # ストリーミングが終了したときに会話履歴をDBに保存する
            await self.dto["db_handler"].begin()

            await self.dto[
                "guest_users_conversation_history_repository"
            ].save_conversation_history(
                {
                    "conversation_id": conversation_id,
                    "cat_id": self.dto.get("cat_id"),
                    "user_id": self.dto.get("user_id"),
                    "user_message": self.dto.get("message"),
                    "ai_message": ai_response_message,
                }
            )

            await self.dto["db_handler"].commit()

            self.logger.info(
                "success",
                extra=SuccessLogExtra(
                    request_id=self.dto["request_id"],
                    conversation_id=conversation_id,
                    cat_id=self.dto.get("cat_id"),
                    user_id=self.dto.get("user_id"),
                    ai_response_id=ai_response_id,
                ),
            )
        except Exception as e:
            await self.dto["db_handler"].rollback()

            self.logger.error(
                f"An error occurred while creating the message: {str(e)}",
                exc_info=True,
                extra=ErrorLogExtra(
                    request_id=self.dto["request_id"],
                    conversation_id=conversation_id,
                    cat_id=self.dto["cat_id"],
                    user_id=self.dto["user_id"],
                    user_message=self.dto["message"],
                ),
            )

            unexpected_error_response_body = {
                "type": "INTERNAL_SERVER_ERROR",
                "title": "an unexpected error has occurred.",
            }

            yield unexpected_error_response_body
        finally:
            self.dto["db_handler"].close()
