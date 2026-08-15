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
