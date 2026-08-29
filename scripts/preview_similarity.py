import sys
from pathlib import Path

import numpy as np
from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal
from app.models.image import Image
from app.models.post import Post


def cosine_similarity(a: list[float], b: list[float]) -> float:
    a_np, b_np = np.array(a), np.array(b)
    return float(np.dot(a_np, b_np) / (np.linalg.norm(a_np) * np.linalg.norm(b_np)))


POST_TITLES = [
    "The Secret Life of Red Foxes",
    "Brewing a Better Cup of Coffee at Home",
    "Hiking Gear Review: The Best Trail Boots of the Year",
]

IMAGE_FILENAMES = ["fox_01.jpg", "fox_05.jpg", "wolf_02.jpg", "dog_01.jpg", "bear_01.jpg"]


def main() -> None:
    db = SessionLocal()
    try:
        images = []
        for fn in IMAGE_FILENAMES:
            img = db.execute(select(Image).where(Image.filename == fn)).scalar_one()
            images.append(img)

        for title in POST_TITLES:
            post = db.execute(select(Post).where(Post.title == title)).scalar_one()

            results = []
            for img in images:
                sim = cosine_similarity(post.embedding, img.embedding)
                results.append((img.filename, img.subject, sim))

            results.sort(key=lambda r: r[2], reverse=True)

            print(f"Post: {post.title!r}\n")
            print(f"{'Image':<16} {'Subject':<20} {'Similarity':>10}")
            print("-" * 48)
            for filename, subject, sim in results:
                print(f"{filename:<16} {subject:<20} {sim:>10.4f}")
            print()
    finally:
        db.close()


if __name__ == "__main__":
    main()
