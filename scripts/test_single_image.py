import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.vision import tag_image

IMAGE_PATH = "data/images/fox/fox_01.jpg"


def main() -> None:
    print(f"Tagging {IMAGE_PATH} ...")
    result = tag_image(IMAGE_PATH)
    print("\nRaw parsed dict:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print("\nField types:")
    for key, value in result.items():
        print(f"  {key}: type={type(value).__name__!r} value={value!r}")


if __name__ == "__main__":
    main()
