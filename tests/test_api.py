import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.db.session import SessionLocal
from app.models.approval import Approval
from app.models.post import Post
from app.models.suggestion import Suggestion
from app.services.matching import rank_images_for_post

client = TestClient(app)

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


@pytest.fixture(scope="module")
def fox_suggestion_id():
    """Ensure a suggestion exists for the fox post and return its ID."""
    db = Session()
    try:
        existing = db.execute(
            __import__("sqlalchemy", fromlist=["select"]).select(Suggestion).where(
                Suggestion.post_id == 1,
                Suggestion.guard_verdict == "accepted",
            )
        ).scalars().first()
        if existing:
            return existing.id
        result = rank_images_for_post(1, db)
        accepted = next((c for c in result["candidates"] if c["verdict"] == "accepted"), None)
        if not accepted:
            pytest.skip("No accepted suggestion for fox post in DB")
        filename_to_id = {img.filename: img.id for img in db.execute(__import__("sqlalchemy", fromlist=["select"]).select(__import__("app.models.image", fromlist=["Image"]).Image)).scalars().all()}
        suggestion = Suggestion(
            post_id=1,
            image_id=filename_to_id[accepted["filename"]],
            similarity_score=accepted["similarity"],
            guard_verdict="accepted",
            reason="",
        )
        db.add(suggestion)
        db.commit()
        db.refresh(suggestion)
        return suggestion.id
    finally:
        db.close()


def test_fox_post_images_returns_suggestion():
    response = client.get("/posts/1/images")
    assert response.status_code == 200
    data = response.json()
    assert data["suggestion"] is not None


def test_coffee_post_images_returns_null_suggestion():
    response = client.get("/posts/6/images")
    assert response.status_code == 200
    data = response.json()
    assert data["suggestion"] is None


def test_nonexistent_post_returns_404():
    response = client.get("/posts/999999/images")
    assert response.status_code == 404


def test_get_suggestion_404():
    response = client.get("/suggestions/999999")
    assert response.status_code == 404


def test_approve_suggestion_404():
    response = client.post("/suggestions/999999/approve", json={"note": "test"})
    assert response.status_code == 404


def test_approve_is_idempotent(fox_suggestion_id):
    db = Session()
    try:
        db.execute(
            text("DELETE FROM approvals WHERE suggestion_id = :sid"),
            {"sid": fox_suggestion_id},
        )
        db.commit()
    finally:
        db.close()

    resp1 = client.post(f"/suggestions/{fox_suggestion_id}/approve", json={"note": "first"})
    assert resp1.status_code == 200
    data1 = resp1.json()
    approval_id_1 = data1["approval"]["id"]

    resp2 = client.post(f"/suggestions/{fox_suggestion_id}/approve", json={"note": "second"})
    assert resp2.status_code == 200
    data2 = resp2.json()
    approval_id_2 = data2["approval"]["id"]

    assert approval_id_1 == approval_id_2
    assert data2["approval"]["reviewer_note"] == "second"

    db = Session()
    try:
        count = db.execute(
            text("SELECT COUNT(*) FROM approvals WHERE suggestion_id = :sid"),
            {"sid": fox_suggestion_id},
        ).scalar()
        assert count == 1
    finally:
        db.close()
