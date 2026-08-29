import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.image import Image
from app.models.post import Post
from app.services.embeddings import embed_text

PACE_DELAY_SECONDS = 1.0


def main() -> None:
    db = SessionLocal()
    images_embedded = 0
    posts_embedded = 0
    failures = 0

    try:
        # --- Embed images ---
        images = db.execute(
            select(Image).where(Image.embedding == [])
        ).scalars().all()
        total_images = len(images)
        print(f"Found {total_images} images needing embeddings.\n")

        for idx, image in enumerate(images, start=1):
            try:
                vector = embed_text(image.caption)
                image.embedding = vector
                db.commit()
                images_embedded += 1
                print(f"[{idx}/{total_images}] {image.filename} embedded ({len(vector)}-dim)")
            except Exception as exc:
                db.rollback()
                failures += 1
                print(f"[{idx}/{total_images}] {image.filename} FAILED: {exc}")
            if idx < total_images:
                time.sleep(PACE_DELAY_SECONDS)

        # --- Embed posts ---
        posts_data = json.loads(Path("data/posts.json").read_text())
        existing_titles = {
            row[0]
            for row in db.execute(select(Post.title)).all()
        }
        new_posts = [p for p in posts_data if p["title"] not in existing_titles]
        total_posts = len(new_posts)
        print(f"\nFound {total_posts} new posts needing embeddings (out of {len(posts_data)} in posts.json).\n")

        for idx, post_data in enumerate(new_posts, start=1):
            text = f"{post_data['title']} {post_data['body']}"
            try:
                vector = embed_text(text)
                db.add(Post(
                    title=post_data["title"],
                    body=post_data["body"],
                    embedding=vector,
                ))
                db.commit()
                posts_embedded += 1
                print(f"[{idx}/{total_posts}] {post_data['title']!r} embedded ({len(vector)}-dim)")
            except Exception as exc:
                db.rollback()
                failures += 1
                print(f"[{idx}/{total_posts}] {post_data['title']!r} FAILED: {exc}")
            if idx < total_posts:
                time.sleep(PACE_DELAY_SECONDS)

    finally:
        db.close()

    print("\n===== EMBEDDING SUMMARY =====")
    print(f"images_embedded: {images_embedded}")
    print(f"posts_embedded:  {posts_embedded}")
    print(f"failures:        {failures}")


if __name__ == "__main__":
    main()
