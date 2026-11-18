from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Attendance(Base):
    __tablename__ = "attendance"
    __table_args__ = (UniqueConstraint("child_id", "instance_id", name="uq_attendance_child_instance"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    child_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("children.id"), nullable=False)
    instance_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("schedule_instances.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # going / not_going / attended / no_show
    source: Mapped[str] = mapped_column(String(10), nullable=False)  # parent / coach
    set_by_user_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
    set_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    child = relationship("Child", back_populates="attendances")
    instance = relationship("ScheduleInstance", back_populates="attendances")
