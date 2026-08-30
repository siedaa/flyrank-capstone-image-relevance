from pydantic import BaseModel


class CandidateOut(BaseModel):
    image_id: int
    filename: str
    subject: str
    similarity: float
    verdict: str
    reason: str | None


class SuggestionOut(BaseModel):
    id: int
    post_id: int
    image_id: int
    similarity_score: float
    guard_verdict: str
    reason: str
    created_at: str


class PostImagesResponse(BaseModel):
    post_id: int
    post_title: str
    suggestion: SuggestionOut | None
    message: str | None
    candidates: list[CandidateOut]
