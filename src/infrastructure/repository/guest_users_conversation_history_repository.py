from typing import List, TypedDict
import aiomysql
from domain.cat import CatId, get_prompt_by_cat_id
from domain.message import ChatMessage
from infrastructure.openai import calculate_token_count, is_token_limit_exceeded


class CreateMessagesWithConversationHistoryDto(TypedDict):
    conversation_id: str
    request_message: str
    cat_id: CatId


class GuestUsersConversationHistoryRepository:
    def __init__(self, connection: aiomysql.Connection):
        self.connection = connection

    async def create_messages_with_conversation_history(
        self, dto: CreateMessagesWithConversationHistoryDto
    ) -> List[ChatMessage]:
        async with self.connection.cursor() as cursor:
            sql = """
            SELECT user_message, ai_message
            FROM guest_users_conversation_histories
            WHERE conversation_id = %s
            ORDER BY created_at DESC
            LIMIT 10
            """
            await cursor.execute(sql, (dto["conversation_id"],))
            result = await cursor.fetchall()
            if result:
                result.reverse()

            conversation_history = [
                {"role": role_type, "content": row[message_type]}
                for row in result
                for role_type, message_type in [
                    ("user", "user_message"),
                    ("assistant", "ai_message"),
                ]
            ]

        # もし会話履歴がまだ存在しなければ、システムメッセージを追加
        if not conversation_history:
            conversation_history.append(
                {"role": "system", "content": get_prompt_by_cat_id(dto["cat_id"])}
            )

        # 新しいメッセージを会話履歴に追加
        conversation_history.append({"role": "user", "content": dto["request_message"]})

        # 実際に会話履歴に含めるメッセージ
        chat_messages = []
        total_tokens = 0

        for message in reversed(conversation_history):
            message_tokens = calculate_token_count(message["content"], "gpt-3.5-turbo")
            if is_token_limit_exceeded(total_tokens + message_tokens) and chat_messages:
                # トークン数が最大を超える場合、ループを抜ける
                break
            chat_messages.insert(0, message)
            total_tokens += message_tokens

        if not any(message["role"] == "system" for message in chat_messages):
            chat_messages.insert(
                0, {"role": "system", "content": get_prompt_by_cat_id(dto["cat_id"])}
            )

        return chat_messages
