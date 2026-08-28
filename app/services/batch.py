import logging
import re
import time
from pathlib import Path

import pydantic

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.image import Image
from app.schemas.image_tag import ImageTag
from app.services.vision import GEMINI_MODEL, tag_image

logger = logging.getLogger(__name__)

IMAGE_EXTS = {".jpg", ".jpeg", ".png"}

RATES = {
    "gemini-2.5-flash": {"input_per_million": 0.30, "output_per_million": 2.50},
    # TODO: confirm published flash-lite pricing; using flash rates as placeholder
    "gemini-2.5-flash-lite": {"input_per_million": 0.30, "output_per_million": 2.50},
    # TODO: verify actual pricing at https://ai.google.dev/pricing before final demo
    "gemini-3.5-flash-lite": {"input_per_million": 0.30, "output_per_million": 2.50},
}

PACE_DELAY_SECONDS = 3.5

GENERAL_MAX_ATTEMPTS = 3
RATE_LIMIT_MAX_ATTEMPTS = 5
BASE_DELAY_SECONDS = 2.0
RATE_LIMIT_FALLBACK_DELAY_SECONDS = 20.0
RETRY_BUFFER_SECONDS = 1.5

LOW_CONFIDENCE_THRESHOLD = 0.7

_RETRY_DELAY_RE = re.compile(r"Please retry in ([0-9.]+)\s*(ms|s|m)?", re.IGNORECASE)


def _is_rate_limit(exc: Exception) -> bool:
    text = str(exc)
    if "RESOURCE_EXHAUSTED" in text or "429" in text:
        return True
    return getattr(exc, "status_code", None) == 429


def _is_daily_quota(exc: Exception) -> bool:
    return "PerDay" in str(exc)


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


def _collect_images(image_dir: str) -> list[str]:
    root = Path(image_dir)
    images = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix.lower() in IMAGE_EXTS:
            images.append(str(path))
    return images


def _calculate_cost(usage: dict) -> float:
    rate = RATES.get(GEMINI_MODEL)
    if rate is None:
        logger.warning("No pricing entry for %s — cost reported as $0.00", GEMINI_MODEL)
        return 0.0
    input_cost = usage["input_tokens"] / 1_000_000 * rate["input_per_million"]
    output_cost = usage["output_tokens"] / 1_000_000 * rate["output_per_million"]
    return input_cost + output_cost


def run_batch_ingestion(image_dir: str = "data/images") -> dict:
    images = _collect_images(image_dir)
    total = len(images)

    processed = 0
    succeeded = 0
    failed = 0
    invalid = 0
    low_confidence = 0
    total_cost = 0.0
    daily_quota_skipped = 0

    db = SessionLocal()
    try:
        for index, image_path in enumerate(images, start=1):
            processed += 1
            filename = Path(image_path).name

            if db.execute(select(Image).where(Image.filename == filename)).scalar_one_or_none():
                print(f"[{index}/{total}] [skip] {filename} already ingested")
                continue

            raw = None
            usage = None
            last_error = None
            attempts = 0
            daily_quota_exceeded = False
            while attempts < GENERAL_MAX_ATTEMPTS:
                rate_limited = False
                try:
                    raw, usage = tag_image(image_path, include_usage=True)
                    break
                except Exception as exc:
                    last_error = exc
                    if _is_daily_quota(exc):
                        daily_quota_exceeded = True
                        print(
                            f"[Daily quota exceeded] {filename}: "
                            "PerDay quota hit — skipping all remaining images."
                        )
                        break
                    rate_limited = _is_rate_limit(exc)
                    attempts += 1
                    max_attempts = RATE_LIMIT_MAX_ATTEMPTS if rate_limited else GENERAL_MAX_ATTEMPTS
                    if attempts >= max_attempts:
                        break
                    logger.warning(
                        "Attempt %d/%d failed for %s: %s",
                        attempts,
                        max_attempts,
                        filename,
                        exc,
                    )
                    if rate_limited:
                        delay = _parse_retry_delay(exc) or RATE_LIMIT_FALLBACK_DELAY_SECONDS
                        delay += RETRY_BUFFER_SECONDS
                        print(
                            f"[Rate limited] Waiting {delay:.1f}s before retrying "
                            f"{filename}... (attempt {attempts}/{max_attempts})"
                        )
                        time.sleep(delay)
                    else:
                        time.sleep(BASE_DELAY_SECONDS * 2 ** (attempts - 1))

            if daily_quota_exceeded:
                daily_quota_skipped = total - processed + 1
                break

            if raw is None:
                failed += 1
                logger.error(
                    "All %d attempts failed for %s: %s",
                    attempts,
                    filename,
                    last_error,
                )
                print(f"[{index}/{total}] {filename} -> FAILED: {last_error}")
                if index < total:
                    time.sleep(PACE_DELAY_SECONDS)
                continue

            try:
                validated = ImageTag(**raw)
            except pydantic.ValidationError as exc:
                invalid += 1
                logger.error("Validation failed for %s: %s", filename, exc)
                print(f"[{index}/{total}] {filename} -> INVALID (skipped): {exc}")
                if index < total:
                    time.sleep(PACE_DELAY_SECONDS)
                continue

            cost = _calculate_cost(usage)
            total_cost += cost

            db.add(
                Image(
                    filename=filename,
                    subject=validated.subject,
                    category=validated.category,
                    attributes=validated.attributes,
                    caption=validated.caption,
                    confidence=validated.confidence,
                    embedding=[],
                )
            )
            db.commit()
            succeeded += 1

            flag = " [LOW CONFIDENCE]" if validated.confidence < LOW_CONFIDENCE_THRESHOLD else ""
            if validated.confidence < LOW_CONFIDENCE_THRESHOLD:
                low_confidence += 1
                logger.warning("Low-confidence tag flagged for review: %s", filename)

            print(
                f"[{index}/{total}] {filename} -> {validated.subject} "
                f"(confidence {validated.confidence}) - ${cost:.6f}"
                f"{flag} [running total: ${total_cost:.6f}]"
            )
            if index < total:
                time.sleep(PACE_DELAY_SECONDS)
    finally:
        db.close()

    summary = {
        "model": GEMINI_MODEL,
        "total_processed": processed,
        "total_succeeded": succeeded,
        "total_failed": failed,
        "total_invalid": invalid,
        "total_low_confidence_flagged": low_confidence,
        "total_daily_quota_skipped": daily_quota_skipped,
        "total_cost": round(total_cost, 6),
    }
    return summary