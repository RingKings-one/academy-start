from typing import Optional

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Direction(Base):
    __tablename__ = "directions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    age_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    age_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    icon_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    groups = relationship("Group", back_populates="direction")
