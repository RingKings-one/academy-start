from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    target_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(30), nullable=False)  # reminder_24h / reminder_2h / noshow_2h / followup_1d / broadcast / cancel_notice
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    send_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", server_default="pending"
    )  # pending / sending / sent / failed / cancelled
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    locked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
