import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.image import Image
from app.models.post import Post
from app.services.matching import cosine_similarity, evaluate_guard


def main() -> None:
    db = SessionLocal()
    try:
        post = db.execute(
            select(Post).where(Post.title == "The Secret Life of Red Foxes")
        ).scalar_one()
        wolf = db.execute(
            select(Image).where(Image.filename == "wolf_02.jpg")
        ).scalar_one()

        all_subjects = [img.subject for img in db.execute(select(Image)).scalars().all()]

        score = cosine_similarity(post.embedding, wolf.embedding)
        result = evaluate_guard(wolf, post, score, all_image_subjects=all_subjects)

        print(f"Forcing wolf_02.jpg as a candidate for 'The Secret Life of Red Foxes'")
        print(f"Similarity score: {score:.4f}")
        print(f"Guard verdict: {result['verdict']}")
        print(f"Reason: {result['reason']}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
