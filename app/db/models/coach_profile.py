from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CoachProfile(Base):
    __tablename__ = "coach_profiles"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    photo_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    achievements: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    bio: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="coach_profile")
