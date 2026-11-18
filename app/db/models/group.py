from typing import Optional

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    direction_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("directions.id"), nullable=False, index=True)
    coach_user_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    age_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    age_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    capacity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    branch: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    direction = relationship("Direction", back_populates="groups")
    schedule_instances = relationship("ScheduleInstance", back_populates="group")
    enrollments = relationship("Enrollment", back_populates="group")
