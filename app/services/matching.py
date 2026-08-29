import numpy as np
from sqlalchemy import select

from app.models.image import Image
from app.models.post import Post

STOP_WORDS = {"a", "an", "the", "of", "and", "or", "is", "in", "on", "at", "to", "for", "with", "by", "its", "it"}
COLOR_WORDS = {"red", "brown", "black", "white", "gray", "grey", "golden", "yellow", "blue", "green", "asian"}


def cosine_similarity(a: list[float], b: list[float]) -> float:
    a_np, b_np = np.array(a), np.array(b)
    return float(np.dot(a_np, b_np) / (np.linalg.norm(a_np) * np.linalg.norm(b_np)))


def _find_post_animal(post_title: str, all_image_subjects: list[str]) -> str | None:
    """Find the animal word in the post title by checking overlap with image subjects."""
    post_words = set(post_title.lower().split()) - STOP_WORDS - COLOR_WORDS
    for subject in all_image_subjects:
        subject_words = set(subject.lower().split()) - STOP_WORDS - COLOR_WORDS
        for pw in post_words:
            for sw in subject_words:
                if sw in pw or pw in sw:
                    return sw
    return None


def category_match(image_subject: str, post_title: str, post_body: str) -> bool:
    words = set(image_subject.lower().split()) - STOP_WORDS
    text = (post_title + " " + post_body).lower()
    return any(word in text for word in words)


def evaluate_guard(image, post, similarity_score, all_image_subjects=None, similarity_floor=0.75, confidence_floor=0.7) -> dict:
    if not category_match(image.subject, post.title, post.body):
        post_animal = _find_post_animal(post.title, all_image_subjects) if all_image_subjects else None
        if post_animal:
            reason = f"Category mismatch: expected {post_animal}, detected {image.subject}"
        else:
            reason = f"Category mismatch: expected something in the post, detected {image.subject}"
        return {"verdict": "rejected", "reason": reason}
    if similarity_score < similarity_floor:
        return {"verdict": "rejected", "reason": f"Similarity below threshold: {similarity_score:.4f} < {similarity_floor}"}
    if image.confidence < confidence_floor:
        return {"verdict": "rejected", "reason": f"Low confidence tag: {image.confidence:.2f} < {confidence_floor:.2f}"}
    return {"verdict": "accepted", "reason": None}


def rank_images_for_post(post_id: int, db_session) -> dict:
    post = db_session.execute(select(Post).where(Post.id == post_id)).scalar_one()
    images = db_session.execute(select(Image).where(Image.embedding != [])).scalars().all()

    all_subjects = [img.subject for img in images]

    ranked = []
    for img in images:
        sim = cosine_similarity(post.embedding, img.embedding)
        guard = evaluate_guard(img, post, sim, all_image_subjects=all_subjects)
        ranked.append({
            "filename": img.filename,
            "subject": img.subject,
            "similarity": round(sim, 4),
            "verdict": guard["verdict"],
            "reason": guard["reason"],
        })

    ranked.sort(key=lambda r: r["similarity"], reverse=True)

    accepted = next((r for r in ranked if r["verdict"] == "accepted"), None)

    return {
        "post_title": post.title,
        "suggestion": accepted["filename"] if accepted else None,
        "reason": None if accepted else "No confident match found",
        "candidates": ranked,
    }
