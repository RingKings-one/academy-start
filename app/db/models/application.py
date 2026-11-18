from datetime import date, datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    parent_user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=True, index=True
    )
    child_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("children.id"), nullable=True)
    child_name: Mapped[str] = mapped_column(String(128), nullable=False)
    child_birth_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    direction_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("directions.id"), nullable=False)
    group_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("groups.id"), nullable=True)
    trial_instance_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("schedule_instances.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="new", server_default="new"
    )  # new / confirmed / attended / no_show / converted / rejected
    source: Mapped[str] = mapped_column(String(10), nullable=False)  # site / bot
    medcert: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # has / needs
    pd_consent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deep_link_token: Mapped[Optional[str]] = mapped_column(String(64), unique=True, nullable=True, index=True)
    followup_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    noshow_sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
