import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.post import Post
from app.services.matching import rank_images_for_post


def main() -> None:
    db = SessionLocal()
    try:
        posts = db.execute(select(Post)).scalars().all()
        for post in posts:
            result = rank_images_for_post(post.id, db)
            print(f"Post: {result['post_title']!r}")
            print(f"{'Rank':<5} {'Image':<16} {'Subject':<20} {'Sim':>6} {'Verdict':<10} Reason")
            print("-" * 90)
            for i, c in enumerate(result["candidates"][:3], start=1):
                reason = c["reason"] or "-"
                print(f"{i:<5} {c['filename']:<16} {c['subject']:<20} {c['similarity']:>6.4f} {c['verdict']:<10} {reason}")
            print(f"Suggestion: {result['suggestion'] or result['reason']}")
            print()
    finally:
        db.close()


if __name__ == "__main__":
    main()
