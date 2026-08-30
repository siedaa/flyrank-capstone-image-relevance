from pydantic import BaseModel


class ApproveRequest(BaseModel):
    note: str | None = None


class ApprovalOut(BaseModel):
    id: int
    suggestion_id: int
    decision: str
    reviewer_note: str | None
    created_at: str


class SuggestionDetailResponse(BaseModel):
    suggestion: dict
    approval: ApprovalOut | None
