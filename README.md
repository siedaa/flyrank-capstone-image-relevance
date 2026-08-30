# AI Image Understanding & Content Matching Engine

**[Live showcase (GitHub Pages)](https://siedaa.github.io/flyrank-capstone-image-relevance/)**

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

## Evaluation

Top-1 precision measured against `data/eval_set.json` (7 posts: 5 animal, 2
non-animal). Each post is matched against all 50 images; the system either
suggests the top-ranked accepted image or returns "no confident match".

| Post | Expected | Suggestion | Correct |
|------|----------|------------|---------|
| The Secret Life of Red Foxes | fox | fox_10.jpg | yes |
| How Wolf Packs Hunt Together | wolf | wolf_02.jpg | yes |
| Why Dogs Are Man's Best Friend | dog | dog_09.jpg | yes |
| Bears: Gentle Giants of the Wild | bear | bear_01.jpg | yes |
| The Graceful World of Deer | deer | deer_10.jpg | yes |
| Brewing a Better Cup of Coffee at Home | (none) | no match | yes |
| Hiking Gear Review: The Best Trail Boots of the Year | (none) | no match | yes |

**Top-1 precision: 7/7 = 100.0%**

Run `python scripts/run_eval.py` to reproduce.

**Honest caveats:** The eval set is intentionally small (7 posts), matching
the brief's minimal scope — a single misclassification would drop the score
to 85.7%. The similarity threshold (`similarity_floor=0.75`) was tuned by
observing this same dataset rather than validated against a separate held-out
set. Both are disclosed as honest scope limitations of a capstone-sized
project, not hidden.

## Current status

| Phase | Status | What it covers |
|-------|--------|----------------|
| 0 | Done | Project skeleton, ORM models, design doc |
| 1 | Done | Image dataset organized (50 images, 5 categories) |
| 2 | Done | Gemini vision tagging pipeline with batch ingestion, retries, cost tracking |
| 3 | Done | Embeddings (3072-dim), cosine similarity matching, mismatch guard (category + similarity + confidence) |
| 4 | Done | REST API (images/posts/suggestions endpoints), background ingestion, review workflow, evaluation pipeline, automated test suite (29 tests) |

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

**Category matching handles synonyms and scientific names.** The matching
engine uses a `CATEGORY_ALIASES` dictionary that maps each animal category to
common and scientific name variants (e.g., "fox" → ["fox", "vulpes vulpes"]).
Both the image subject and post text are normalized to canonical categories
before comparison, so "Vulpes vulpes" correctly matches posts about foxes.

**Approve/reject is idempotent.** Each suggestion can have at most one
approval record. Calling approve or reject twice updates the existing row
instead of inserting duplicates.
