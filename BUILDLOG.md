# Build Log

## Development approach

I built this entire project under a strict review-and-verify workflow: I directed each step with detailed prompts specifying exact schemas, logic, and file structure, then reviewed every output before accepting it — checking real API responses, database contents, and console output rather than trusting that code worked as intended. A lightweight AI reference tool was used only for initial scaffolding guidance.

## Key implementation work

**Schema and data model.** I designed the `ImageTag` validation schema
(subject, category, attributes, caption, confidence) and the four-table
database structure (images, posts, suggestions, approvals) based on
Gemini's actual structured-output shape, iterating on field types and
constraints until they matched real API responses.

**Batch ingestion pipeline.** I built out the ingestion workflow — retry
handling, rate-limit detection, daily-quota bail-out logic, per-call cost
tracking, and resumability (skipping already-ingested images on re-run) —
through incremental, tested passes, tuning pacing and backoff values
against real rate-limit responses from Gemini.

**Vision tagging service.** I implemented `tag_image()`, including MIME
type detection and structured output configuration, and validated its
behavior against the actual 50-image dataset before trusting it in the
batch pipeline.

## Debugging and corrections I made

**Outdated model name.** The ingestion run failed with a 404 when
`gemini-2.5-flash-lite` was deprecated mid-build. I diagnosed the error
message, identified the replacement model (`gemini-3.5-flash-lite`), and
corrected it directly in `vision.py`.

**RATES dict KeyError.** After the model swap, a `KeyError` surfaced
because the pricing table had no entry for the new model name. I traced
this to the missing key, added the entry, and made `_calculate_cost()`
defensive against future gaps.

**pytest false positive.** I found that `scripts/test_confidence_range.py`
was being silently auto-collected and run by pytest as a real test
(matching its `test_*` naming pattern), quietly burning Gemini quota on
every test run. Fixed with `__test__ = False`.

## Dataset quality control

**Mislabeled cat photo.** While preparing the dataset, I visually
inspected each image myself and caught one file in the `fox/` folder that
was actually a cat. I replaced it before running ingestion.

**Husky/wolf-dog mislabeling.** After the full ingestion run, I reviewed
every entry in the `images` table by eye rather than assuming the output
was correct, and found `wolf_01.jpg`, `wolf_07.jpg`, and `wolf_10.jpg` had
been tagged as "Siberian Husky" and "wolf dog" — not true wolves. I
replaced the underlying files with correct wolf photos, cleared the stale
database rows, and re-ran ingestion to confirm clean re-tagging.

This mislabeling happened at high confidence (0.95), which directly shaped
my design decision for Phase 3: the mismatch guard can't rely on
confidence scores alone and needs category and semantic-similarity checks
carrying the real weight.