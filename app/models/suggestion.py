from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Suggestion(Base):
    __tablename__ = "suggestions"
    __table_args__ = (Index("ix_suggestions_post_id", "post_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    post_id: Mapped[int] = mapped_column(ForeignKey("posts.id"), nullable=False)
    image_id: Mapped[int] = mapped_column(ForeignKey("images.id"), nullable=False)
    similarity_score: Mapped[float] = mapped_column(Float, nullable=False)
    guard_verdict: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str] = mapped_column(String(1000), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
