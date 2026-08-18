import json
import sys
from pathlib import Path

import pydantic

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.schemas.image_tag import ImageTag
from app.services.vision import tag_image

IMAGE_PATHS = [
    "data/images/fox/fox_10.jpg",
    "data/images/wolf/wolf_01.jpg",
    "data/images/wolf/wolf_06.jpg",
    "data/images/fox/fox_03.jpg",
]


def main() -> None:
    for image_path in IMAGE_PATHS:
        print(f"Tagging {image_path} ...")
        raw = tag_image(image_path)
        print("Raw parsed dict:")
        print(json.dumps(raw, indent=2, ensure_ascii=False))
        print("Field types:")
        for key, value in raw.items():
            print(f"  {key}: type={type(value).__name__!r} value={value!r}")

        try:
            validated = ImageTag(**raw)
            print("Validation: SUCCESS")
            print(f"Validated confidence: {validated.confidence!r}")
        except pydantic.ValidationError as exc:
            print("Validation: FAILED")
            print("Pydantic ValidationError:")
            print(exc)
        print()


if __name__ == "__main__":
    main()