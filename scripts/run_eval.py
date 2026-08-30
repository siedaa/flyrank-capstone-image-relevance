import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.post import Post
from app.services.matching import rank_images_for_post


def main() -> None:
    eval_set = json.loads(Path("data/eval_set.json").read_text())
    db = SessionLocal()

    correct = 0
    total = 0

    try:
        print(f"{'Post Title':<50} {'Expected':<10} {'Suggestion':<20} {'Correct':<8}")
        print("-" * 90)

        for entry in eval_set:
            post = db.execute(
                select(Post).where(Post.title == entry["post_title"])
            ).scalar_one()

            result = rank_images_for_post(post.id, db)
            suggested = result["suggestion"]
            expected = entry["expected_category"]

            if expected is not None:
                is_correct = suggested is not None and expected in suggested.lower()
            else:
                is_correct = suggested is None

            if is_correct:
                correct += 1
            total += 1

            suggestion_display = suggested or "no match"
            correct_display = "yes" if is_correct else "NO"

            print(f"{entry['post_title']:<50} {str(expected):<10} {suggestion_display:<20} {correct_display:<8}")

        precision = correct / total if total > 0 else 0
        print()
        print(f"Top-1 precision: {correct}/{total} = {precision:.1%}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
