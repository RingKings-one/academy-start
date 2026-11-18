from datetime import date, datetime
from typing import Optional

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Child(Base):
    __tablename__ = "children"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    parent_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    birth_date: Mapped[date] = mapped_column(Date, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    parent = relationship("User", back_populates="children", foreign_keys=[parent_user_id])
    enrollments = relationship("Enrollment", back_populates="child")
    attendances = relationship("Attendance", back_populates="child")
