# AI Image Understanding & Content Matching Engine

A FastAPI service that uses Google Gemini's vision model to tag animal images
with structured metadata (subject, caption, confidence), stores results in
Postgres, and will ultimately match images to blog posts via semantic
embeddings with a mismatch guard that refuses suggestions when confidence is
low.

## Architecture

```
                    Phase 2 (done)             Phase 3 (in progress)
                    ==============             =====================
Images ──────────> Gemini vision tagging ──> Postgres (images table)
                       (structured JSON)         │
                                                 │  embeddings
                                                 v
Posts ───────────────────────────────────> Postgres (posts table)
                                                 │
                                                 v
                                           Cosine similarity matching
                                                 │
                                                 v
                                           Mismatch guard
                                          (category + similarity
                                           + confidence checks)
                                                 │
                                                 v
                                           suggestions table
                                                 │
                                                 v
                                           Approve / reject API
```

## How to run

```bash
# 1. Start Postgres
docker compose up -d

# 2. Run migrations
alembic upgrade head

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set your Gemini API key in .env
#    GEMINI_API_KEY=your_key_here

# 5. Run batch image ingestion (50 animal images)
python scripts/run_ingestion.py

# 6. Run tests
pytest
```

## Current status

| Phase | Status | What it covers |
|-------|--------|----------------|
| 0 | Done | Project skeleton, ORM models, design doc |
| 1 | Done | Image dataset organized (50 images, 5 categories) |
| 2 | Done | Gemini vision tagging pipeline with batch ingestion, retries, cost tracking |
| 3 | In progress | Embeddings, semantic matching, mismatch guard |
| 4 | Pending | API endpoints for suggestions, approval workflow |

## Limitations

- **No embeddings yet.** The `embedding` column is populated with empty arrays
  `[]`. Semantic matching (Phase 3) will fill these with real vectors.
- **Confidence scores cluster high (~0.95-0.99).** The mismatch guard will
  rely more heavily on category matching and cosine similarity than on raw
  confidence, since confidence alone won't meaningfully separate good matches
  from bad ones at this range.
- **Model was swapped mid-build.** Started on `gemini-2.5-flash`, hit the
  free-tier daily quota limit (20 requests/day), switched to
  `gemini-3.5-flash-lite` which has a higher free daily quota.
- **Cost figures are placeholders.** The `RATES` dict uses `gemini-2.5-flash`
  pricing for all models. Actual flash-lite pricing needs to be confirmed at
  https://ai.google.dev/pricing before final demo.
