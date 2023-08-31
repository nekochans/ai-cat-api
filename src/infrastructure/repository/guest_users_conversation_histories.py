from sqlalchemy import String, BigInteger, DateTime, UnicodeText
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column
from infrastructure.db import Base


class GuestUsersConversationHistory(Base):
    __tablename__ = "guest_users_conversation_histories"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    conversation_id: Mapped[str] = mapped_column(String(36), nullable=False)
    cat_id: Mapped[str] = mapped_column(String(255), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    user_message: Mapped[str] = mapped_column(UnicodeText, nullable=False)
    ai_message: Mapped[str] = mapped_column(UnicodeText, nullable=False)
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(6), nullable=False, server_default=func.current_timestamp(6)
    )
    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(6),
        nullable=False,
        server_default=func.current_timestamp(6),
        onupdate=func.current_timestamp(6),
    )
