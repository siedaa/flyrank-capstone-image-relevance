# AI Image Understanding & Content Matching Engine

A FastAPI service that uses Google Gemini's vision model to tag animal images
with structured metadata (subject, caption, confidence), stores results in
Postgres, and matches images to blog posts via semantic embeddings with a
mismatch guard that refuses suggestions when no confident match exists.

## Architecture

```
Images ──────────> Gemini vision tagging ──> Postgres (images table)
                       (structured JSON)         │
                                                 │  embeddings (3072-dim)
                                                 v
Posts ───────────────────────────────────> Postgres (posts table)
                                                 │
                                                 v
                                           Cosine similarity ranking
                                                 │
                                                 v
                                           Mismatch guard
                                          (category -> similarity
                                           -> confidence checks)
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

# 6. Generate embeddings for images and posts
python scripts/generate_embeddings.py

# 7. Run tests
pytest
```

## Current status

| Phase | Status | What it covers |
|-------|--------|----------------|
| 0 | Done | Project skeleton, ORM models, design doc |
| 1 | Done | Image dataset organized (50 images, 5 categories) |
| 2 | Done | Gemini vision tagging pipeline with batch ingestion, retries, cost tracking |
| 3 | Done | Embeddings (3072-dim), cosine similarity matching, mismatch guard (category + similarity + confidence) |
| 4 | Pending | API endpoints for suggestions, approval workflow |

## Limitations

- **Similarity scores cluster narrow (~0.69-0.85).** Cosine similarity alone
  cannot reliably distinguish between similar animal categories — a bear
  (0.788) scored higher than a wolf (0.768) against a fox post. The category
  check is what actually carries the real discrimination power, with
  similarity mainly useful for catching totally irrelevant posts.
- **Confidence scores cluster high (~0.95-0.99).** The guard uses confidence
  as a final safety net but it rarely fires; category and similarity do the
  heavy lifting.
- **Model was swapped mid-build.** Started on `gemini-2.5-flash`, hit the
  free-tier daily quota limit (20 requests/day), switched to
  `gemini-3.5-flash-lite` which has a higher free daily quota.
- **Cost figures are placeholders.** The `RATES` dict uses `gemini-2.5-flash`
  pricing for all models. Actual flash-lite pricing needs to be confirmed at
  https://ai.google.dev/pricing before final demo.

**Guard thresholds:** `similarity_floor=0.75`, `confidence_floor=0.7`. These
were derived from measuring real similarity scores across the dataset, not
guessed. The 0.75 floor sits below the lowest accepted animal-to-animal
similarity (~0.77 for dog post top match) while above the highest
non-animal post similarity (~0.74).
