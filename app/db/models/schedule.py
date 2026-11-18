from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ScheduleInstance(Base):
    __tablename__ = "schedule_instances"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("groups.id"), nullable=False, index=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="scheduled", server_default="scheduled"
    )  # scheduled / cancelled / moved
    cancel_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    moved_to_instance_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("schedule_instances.id"), nullable=True
    )
    created_by: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    group = relationship("Group", back_populates="schedule_instances")
    attendances = relationship("Attendance", back_populates="instance")
