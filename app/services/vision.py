import json

from google import genai
from google.genai import types

from app.core.config import settings

GEMINI_MODEL = "gemini-2.5-flash"

_TAGGING_PROMPT = """Analyze the animal in this image and return structured JSON with this exact shape:
{
  "subject": "specific animal name, e.g. red fox",
  "category": "animal",
  "attributes": ["3-5 short descriptive tags"],
  "caption": "one sentence describing the image",
  "confidence": 0.95
}
Rules:
- subject must be the specific animal species shown, not a generic label.
- confidence is a float between 0 and 1 representing your certainty in this tagging.
- Output only JSON, no markdown fences, no extra text.
"""


def tag_image(image_path: str) -> dict:
    """Tag the image at image_path with Gemini Flash and return the parsed JSON dict."""
    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    with open(image_path, "rb") as fh:
        image_bytes = fh.read()

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
            _TAGGING_PROMPT,
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema={
                "type": "OBJECT",
                "properties": {
                    "subject": {"type": "STRING"},
                    "category": {"type": "STRING"},
                    "attributes": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "caption": {"type": "STRING"},
                    "confidence": {"type": "NUMBER"},
                },
                "required": ["subject", "category", "attributes", "caption", "confidence"],
            },
        ),
    )

    return json.loads(response.text)


def test_hard_cases() -> None:
    """Debug: tag deliberately hard images (low file size / resolution or 50x50) and print confidence."""
    import os

    from pathlib import Path

    from PIL import Image

    images_root = Path(__file__).resolve().parents[2] / "data" / "images"

    ranked = []
    for folder in sorted(p for p in images_root.iterdir() if p.is_dir()):
        for img in sorted(folder.glob("*.jpg")):
            with Image.open(img) as im:
                width, height = im.size
            ranked.append((os.path.getsize(img), width * height, img))
    ranked.sort()

    hardest = ranked[:3]
    smallest = hardest[0][2]

    lowres_path = images_root / "_test_lowres.jpg"
    with Image.open(smallest) as im:
        im.resize((50, 50)).save(lowres_path, "JPEG")

    cases = [("hardest-1", t[2]) for t in hardest] + [("lowres-50x50", lowres_path)]

    for label, path in cases:
        size_kb = os.path.getsize(path) / 1024
        with Image.open(path) as im:
            width, height = im.size
        print(f"=== {label}: {path} ({size_kb:.1f} KB, {width}x{height}) ===")
        raw = tag_image(str(path))
        print(f"subject={raw['subject']!r}")
        print(f"confidence={raw['confidence']!r}")
        print()
