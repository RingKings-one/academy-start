from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Enrollment(Base):
    __tablename__ = "enrollments"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    child_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("children.id"), nullable=False)
    group_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("groups.id"), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="trial", server_default="trial"
    )  # trial / active / paused / left
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    child = relationship("Child", back_populates="enrollments")
    group = relationship("Group", back_populates="enrollments")
