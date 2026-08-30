from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.image import Image
from app.models.post import Post
from app.models.suggestion import Suggestion
from app.schemas.suggestion import CandidateOut, PostImagesResponse, SuggestionOut
from app.services.matching import rank_images_for_post

router = APIRouter()


@router.get("/{post_id}/images", response_model=PostImagesResponse)
def get_post_images(post_id: int) -> dict:
    db = SessionLocal()
    try:
        post = db.execute(select(Post).where(Post.id == post_id)).scalar_one_or_none()
        if post is None:
            raise HTTPException(status_code=404, detail=f"Post {post_id} not found")

        result = rank_images_for_post(post_id, db)

        filename_to_id = {
            img.filename: img.id
            for img in db.execute(select(Image)).scalars().all()
        }

        candidates_out = []
        for c in result["candidates"]:
            image_id = filename_to_id[c["filename"]]
            candidates_out.append(CandidateOut(
                image_id=image_id,
                filename=c["filename"],
                subject=c["subject"],
                similarity=c["similarity"],
                verdict=c["verdict"],
                reason=c["reason"] or "",
            ))

        accepted = next((c for c in result["candidates"] if c["verdict"] == "accepted"), None)
        suggestion_db = None
        if accepted:
            image_id = filename_to_id[accepted["filename"]]
            existing = db.execute(
                select(Suggestion).where(
                    Suggestion.post_id == post_id,
                    Suggestion.image_id == image_id,
                )
            ).scalar_one_or_none()
            if existing:
                suggestion_db = existing
            else:
                suggestion_db = Suggestion(
                    post_id=post_id,
                    image_id=image_id,
                    similarity_score=accepted["similarity"],
                    guard_verdict="accepted",
                    reason="",
                )
                db.add(suggestion_db)
                db.commit()
                db.refresh(suggestion_db)

        suggestion_out = None
        if suggestion_db:
            suggestion_out = SuggestionOut(
                id=suggestion_db.id,
                post_id=suggestion_db.post_id,
                image_id=suggestion_db.image_id,
                similarity_score=suggestion_db.similarity_score,
                guard_verdict=suggestion_db.guard_verdict,
                reason=suggestion_db.reason,
                created_at=str(suggestion_db.created_at),
            )

        for c in result["candidates"]:
            if c["verdict"] == "rejected":
                image_id = filename_to_id[c["filename"]]
                existing = db.execute(
                    select(Suggestion).where(
                        Suggestion.post_id == post_id,
                        Suggestion.image_id == image_id,
                    )
                ).scalar_one_or_none()
                if not existing:
                    db.add(Suggestion(
                        post_id=post_id,
                        image_id=image_id,
                        similarity_score=c["similarity"],
                        guard_verdict="rejected",
                        reason=c["reason"] or "",
                    ))
                    db.commit()

        return PostImagesResponse(
            post_id=post_id,
            post_title=result["post_title"],
            suggestion=suggestion_out,
            message=result["reason"],
            candidates=candidates_out,
        )
    finally:
        db.close()
