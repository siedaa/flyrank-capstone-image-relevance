from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.approval import Approval
from app.models.image import Image
from app.models.post import Post
from app.models.suggestion import Suggestion
from app.schemas.approval import ApprovalOut, ApproveRequest

router = APIRouter()


def _suggestion_to_dict(suggestion: Suggestion, db) -> dict:
    image = db.execute(select(Image).where(Image.id == suggestion.image_id)).scalar_one()
    post = db.execute(select(Post).where(Post.id == suggestion.post_id)).scalar_one()
    return {
        "id": suggestion.id,
        "post_id": suggestion.post_id,
        "post_title": post.title,
        "image_id": suggestion.image_id,
        "image_filename": image.filename,
        "image_subject": image.subject,
        "similarity_score": suggestion.similarity_score,
        "guard_verdict": suggestion.guard_verdict,
        "reason": suggestion.reason,
        "created_at": str(suggestion.created_at),
    }


@router.get("/{suggestion_id}")
def get_suggestion(suggestion_id: int) -> dict:
    db = SessionLocal()
    try:
        suggestion = db.execute(
            select(Suggestion).where(Suggestion.id == suggestion_id)
        ).scalar_one_or_none()
        if suggestion is None:
            raise HTTPException(status_code=404, detail=f"Suggestion {suggestion_id} not found")

        approval = db.execute(
            select(Approval).where(Approval.suggestion_id == suggestion_id)
        ).scalars().first()

        approval_out = None
        if approval:
            approval_out = ApprovalOut(
                id=approval.id,
                suggestion_id=approval.suggestion_id,
                decision=approval.decision,
                reviewer_note=approval.reviewer_note,
                created_at=str(approval.created_at),
            )

        return {
            "suggestion": _suggestion_to_dict(suggestion, db),
            "approval": approval_out,
        }
    finally:
        db.close()


@router.post("/{suggestion_id}/approve")
def approve_suggestion(suggestion_id: int, body: ApproveRequest | None = None) -> dict:
    db = SessionLocal()
    try:
        suggestion = db.execute(
            select(Suggestion).where(Suggestion.id == suggestion_id)
        ).scalar_one_or_none()
        if suggestion is None:
            raise HTTPException(status_code=404, detail=f"Suggestion {suggestion_id} not found")

        note = body.note if body else None
        approval = Approval(
            suggestion_id=suggestion_id,
            decision="approved",
            reviewer_note=note,
        )
        db.add(approval)
        db.commit()
        db.refresh(approval)

        return {
            "suggestion": _suggestion_to_dict(suggestion, db),
            "approval": ApprovalOut(
                id=approval.id,
                suggestion_id=approval.suggestion_id,
                decision=approval.decision,
                reviewer_note=approval.reviewer_note,
                created_at=str(approval.created_at),
            ),
        }
    finally:
        db.close()


@router.post("/{suggestion_id}/reject")
def reject_suggestion(suggestion_id: int, body: ApproveRequest | None = None) -> dict:
    db = SessionLocal()
    try:
        suggestion = db.execute(
            select(Suggestion).where(Suggestion.id == suggestion_id)
        ).scalar_one_or_none()
        if suggestion is None:
            raise HTTPException(status_code=404, detail=f"Suggestion {suggestion_id} not found")

        note = body.note if body else None
        approval = Approval(
            suggestion_id=suggestion_id,
            decision="rejected",
            reviewer_note=note,
        )
        db.add(approval)
        db.commit()
        db.refresh(approval)

        return {
            "suggestion": _suggestion_to_dict(suggestion, db),
            "approval": ApprovalOut(
                id=approval.id,
                suggestion_id=approval.suggestion_id,
                decision=approval.decision,
                reviewer_note=approval.reviewer_note,
                created_at=str(approval.created_at),
            ),
        }
    finally:
        db.close()
