from typing import Literal

from pydantic import BaseModel, Field


class ImageTag(BaseModel):
    """Validates Gemini's vision output for a single tagged image."""

    subject: str
    category: Literal["animal"]
    attributes: list[str]
    caption: str
    confidence: float = Field(ge=0.0, le=1.0)
