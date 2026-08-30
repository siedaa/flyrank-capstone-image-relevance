import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models.image import Image
from app.models.post import Post
from app.services.matching import rank_images_for_post

engine = create_engine(settings.DATABASE_URL)
Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def _db_reachable():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _db_reachable(),
    reason="Postgres not reachable — run with Docker first: docker compose up -d",
)


def test_fox_post_returns_fox_image():
    db = Session()
    try:
        result = rank_images_for_post(1, db)
        assert result["suggestion"] is not None, "Fox post should have a suggestion"
        # The accepted image should contain "fox" in its subject
        accepted = next(c for c in result["candidates"] if c["verdict"] == "accepted")
        assert "fox" in accepted["subject"].lower()
    finally:
        db.close()


def test_coffee_post_returns_no_suggestion():
    db = Session()
    try:
        result = rank_images_for_post(6, db)
        assert result["suggestion"] is None, "Coffee post should have no suggestion"
    finally:
        db.close()


def test_hiking_post_returns_no_suggestion():
    db = Session()
    try:
        result = rank_images_for_post(7, db)
        assert result["suggestion"] is None, "Hiking post should have no suggestion"
    finally:
        db.close()


def test_wolf_vs_fox_post_rejected():
    db = Session()
    try:
        # Create a fake wolf image with an embedding similar to real fox images
        fox_post = db.execute(
            __import__("sqlalchemy", fromlist=["select"]).select(Post).where(Post.id == 1)
        ).scalar_one()

        wolf_image = Image(
            filename="wolf_fake.jpg",
            subject="gray wolf",
            category="animal",
            attributes=["fur"],
            caption="A gray wolf",
            confidence=0.95,
            embedding=fox_post.embedding,  # same embedding to force high similarity
        )
        db.add(wolf_image)
        db.commit()
        db.refresh(wolf_image)

        result = rank_images_for_post(1, db)
        # The wolf image should be rejected with category mismatch
        wolf_entry = next(
            (c for c in result["candidates"] if c["filename"] == "wolf_fake.jpg"),
            None,
        )
        assert wolf_entry is not None, "wolf_fake.jpg should be in candidates"
        assert wolf_entry["verdict"] == "rejected"
        assert "Category mismatch" in wolf_entry["reason"]
    finally:
        # Clean up the fake wolf image
        db.execute(text("DELETE FROM images WHERE filename = 'wolf_fake.jpg'"))
        db.commit()
        db.close()
