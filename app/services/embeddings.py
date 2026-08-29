import logging
import re
import time

from google import genai
from google.genai import types

from app.core.config import settings

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "gemini-embedding-001"

MAX_ATTEMPTS = 3
BASE_DELAY_SECONDS = 2.0
FALLBACK_DELAY_SECONDS = 20.0
RETRY_BUFFER_SECONDS = 1.5

_RETRY_DELAY_RE = re.compile(r"Please retry in ([0-9.]+)\s*(ms|s|m)?", re.IGNORECASE)


def _is_rate_limit(exc: Exception) -> bool:
    text = str(exc)
    if "RESOURCE_EXHAUSTED" in text or "429" in text:
        return True
    return getattr(exc, "status_code", None) == 429


def _parse_retry_delay(exc: Exception) -> float | None:
    match = _RETRY_DELAY_RE.search(str(exc))
    if not match:
        return None
    value = float(match.group(1))
    unit = match.group(2) or "s"
    if unit == "ms":
        value /= 1000.0
    elif unit == "m":
        value *= 60.0
    return value


def embed_text(text: str) -> list[float]:
    """Embed text using Gemini's embedding endpoint. Returns the vector as a list of floats."""
    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    attempts = 0
    while attempts < MAX_ATTEMPTS:
        try:
            result = client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=text,
                config=types.EmbedContentConfig(task_type="SEMANTIC_SIMILARITY"),
            )
            return result.embeddings[0].values
        except Exception as exc:
            attempts += 1
            if attempts >= MAX_ATTEMPTS:
                raise
            if _is_rate_limit(exc):
                delay = _parse_retry_delay(exc) or FALLBACK_DELAY_SECONDS
                delay += RETRY_BUFFER_SECONDS
                logger.warning("Rate limited on embedding, waiting %.1fs (attempt %d/%d)", delay, attempts, MAX_ATTEMPTS)
                time.sleep(delay)
            else:
                logger.warning("Embedding failed (attempt %d/%d): %s", attempts, MAX_ATTEMPTS, exc)
                time.sleep(BASE_DELAY_SECONDS * 2 ** (attempts - 1))
