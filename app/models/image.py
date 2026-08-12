from datetime import datetime

from sqlalchemy import DateTime, Float, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Image(Base):
    __tablename__ = "images"
    __table_args__ = (Index("ix_images_subject", "subject"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    attributes: Mapped[list] = mapped_column(ARRAY(String), nullable=False, default=list)
    caption: Mapped[str] = mapped_column(String(1000), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    embedding: Mapped[list] = mapped_column(ARRAY(Float), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
