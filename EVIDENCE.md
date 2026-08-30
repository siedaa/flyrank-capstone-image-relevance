# Evidence — Definition of Done checkboxes

## Done

### "Vision model produces structured output validated against a schema"

Gemini returns raw JSON that is validated against the `ImageTag` Pydantic
schema before being written to the database. If validation fails, the image
is skipped with an `INVALID` label and never written.

Example — successful validation:

```python
>>> from app.services.vision import tag_image
>>> from app.schemas.image_tag import ImageTag
>>> raw = tag_image("data/images/fox/fox_01.jpg")
>>> validated = ImageTag(**raw)
>>> validated.subject
'red fox'
>>> validated.confidence
0.98
```

Example — ingestion output showing validation in action:

```
[31/50] fox_01.jpg -> red fox (confidence 0.98) - $0.000584 [running total: $0.005228]
[32/50] fox_02.jpg -> red fox (confidence 0.98) - $0.000591 [running total: $0.005819]
```

### "Images are processed through a batch background job with retries"

`scripts/run_ingestion.py` calls `run_batch_ingestion()` which processes all
50 images with per-image retry logic, rate-limit detection, daily quota
bail-out, and exponential backoff.

Example — retry handling during a run:

```
Attempt 1/3 failed for dog_03.jpg: 404 NOT_FOUND. {'error': {'code': 404, ...
Attempt 2/3 failed for dog_03.jpg: 404 NOT_FOUND. {'error': {'code': 404, ...
All 3 attempts failed for dog_03.jpg: 404 NOT_FOUND. ...
```

Example — daily quota detection (from the gemini-2.5-flash run):

```
[Daily quota exceeded] dog_03.jpg: PerDay quota hit — skipping all remaining images.
```

### "Vision and embedding costs are tracked per call"

Every successful `tag_image()` call returns real token counts from Gemini's
`usage_metadata`. `_calculate_cost()` multiplies these by the rate table and
prints a running total on each line.

Example — running cost output:

```
[23/50] dog_03.jpg -> domestic dog (confidence 0.98) - $0.000587 [running total: $0.000587]
[24/50] dog_04.jpg -> Samoyed (confidence 0.95) - $0.000580 [running total: $0.001167]
...
[50/50] wolf_10.jpg -> gray wolf (confidence 0.98) - $0.000589 [running total: $0.01774]

===== FINAL SUMMARY =====
{
  "model": "gemini-3.5-flash-lite",
  "total_processed": 50,
  "total_succeeded": 50,
  "total_cost": 0.01774
}
```

### "Batch job is resumable — re-running skips already-ingested images"

Before calling Gemini on each image, the batch job queries the `images` table
for a matching filename. If found, it prints `[skip]` and moves on without
calling the API.

Example — resumability on re-run:

```
[1/50] [skip] bear_01.jpg already ingested
[2/50] [skip] bear_02.jpg already ingested
...
[22/50] [skip] dog_02.jpg already ingested
[23/50] dog_03.jpg -> domestic dog (confidence 0.98) - $0.000587 ...
```

### Semantic matching works for equivalent concepts

The fox post ("The Secret Life of Red Foxes") correctly ranks fox_10.jpg
highest (similarity 0.8458) among all 50 images, with fox_01.jpg (0.8450)
and fox_05.jpg (0.8347) rounding out the top 3. All three pass the guard
and are accepted.

```
Post: 'The Secret Life of Red Foxes'
Rank  Image            Subject              Sim Verdict    Reason
------------------------------------------------------------------------------------------
1     fox_10.jpg       red fox              0.8458 accepted   -
2     fox_01.jpg       red fox              0.8450 accepted   -
3     fox_05.jpg       red fox              0.8347 accepted   -
Suggestion: fox_10.jpg
```

### The mismatch guard rejects incorrect recommendations

Forcing wolf_02.jpg (a real wolf, similarity 0.7683) as a candidate for the
fox post provably fails — the guard rejects it on the category check before
similarity is even evaluated:

```
Forcing wolf_02.jpg as a candidate for 'The Secret Life of Red Foxes'
Similarity score: 0.7683
Guard verdict: rejected
Reason: Category mismatch: expected fox, detected gray wolf
```

### When no image clears the bar, the system answers "no confident match"

Both non-animal posts (coffee, hiking) reject all 50 images. The category
check catches every candidate because the post text contains no animal words:

```
Post: 'Brewing a Better Cup of Coffee at Home'
Rank  Image            Subject              Sim Verdict    Reason
------------------------------------------------------------------------------------------
1     bear_02.jpg      polar bear           0.7321 rejected   Category mismatch: expected something in the post, detected polar bear
2     deer_10.jpg      Sika deer            0.7269 rejected   Category mismatch: expected something in the post, detected Sika deer
3     bear_06.jpg      Brown bear           0.7247 rejected   Category mismatch: expected something in the post, detected Brown bear
Suggestion: No confident match found
```

### "REST API serves image suggestions for posts"

`GET /posts/{id}/images` runs the ranking pipeline, persists suggestions,
and returns structured JSON with candidates. Non-animal posts return
`suggestion: null`. Nonexistent posts return 404.

```
GET /posts/1/images  -> 200, suggestion: fox_10.jpg
GET /posts/6/images  -> 200, suggestion: null
GET /posts/999999/images -> 404
```

### "Review workflow supports approve/reject"

`POST /suggestions/{id}/approve` and `POST /suggestions/{id}/reject` create
`Approval` rows. `GET /suggestions/{id}` returns the suggestion with any
approval attached. Nonexistent suggestion IDs return 404.

### Automated test suite covers all layers (36 tests, 100% pass)

**`tests/test_schema_validation.py` (9 tests)** — pure unit tests against
`ImageTag` Pydantic schema. Validates that confidence bounds (0.0–1.0) are
enforced, string coercion is rejected (`strict=True`), category must be
`"animal"`, and required fields are checked.

```
tests/test_schema_validation.py::test_valid_image_tag PASSED
tests/test_schema_validation.py::test_confidence_above_one_raises PASSED
tests/test_schema_validation.py::test_confidence_below_zero_raises PASSED
tests/test_schema_validation.py::test_confidence_string_raises PASSED
tests/test_schema_validation.py::test_non_animal_category_raises PASSED
tests/test_schema_validation.py::test_missing_caption_raises PASSED
tests/test_schema_validation.py::test_missing_subject_raises PASSED
tests/test_schema_validation.py::test_boundary_confidence_zero PASSED
tests/test_schema_validation.py::test_boundary_confidence_one PASSED
```

**`tests/test_mismatch_guard.py` (8 tests)** — unit tests against
`evaluate_guard()` and `category_match()` with hand-constructed fake objects.
Covers all three rejection paths (category mismatch, similarity below floor,
confidence below floor), the accepted path, and the generic "expected
something in the post" message for non-animal posts.

```
tests/test_mismatch_guard.py::TestCategoryMatch::test_matching_category PASSED
tests/test_mismatch_guard.py::TestCategoryMatch::test_mismatch_category PASSED
tests/test_mismatch_guard.py::TestCategoryMatch::test_no_animal_words_in_post PASSED
tests/test_mismatch_guard.py::TestEvaluateGuard::test_category_mismatch_rejected PASSED
tests/test_mismatch_guard.py::TestEvaluateGuard::test_similarity_below_floor PASSED
tests/test_mismatch_guard.py::TestEvaluateGuard::test_confidence_below_floor PASSED
tests/test_mismatch_guard.py::TestEvaluateGuard::test_all_pass_accepted PASSED
tests/test_mismatch_guard.py::TestEvaluateGuard::test_no_animal_in_post_generic_rejection PASSED
```

**`tests/test_matching_accuracy.py` (4 tests)** — integration tests against
the real Postgres database. Verifies `rank_images_for_post()` returns a fox
image for the fox post, `None` for coffee and hiking posts, and that a
forced wolf-on-fox-post is rejected with "Category mismatch". Skips
gracefully if Postgres is unreachable.

```
tests/test_matching_accuracy.py::test_fox_post_returns_fox_image PASSED
tests/test_matching_accuracy.py::test_coffee_post_returns_no_suggestion PASSED
tests/test_matching_accuracy.py::test_hiking_post_returns_no_suggestion PASSED
tests/test_matching_accuracy.py::test_wolf_vs_fox_post_rejected PASSED
```

**`tests/test_api.py` (5 tests)** — FastAPI `TestClient` tests against
running endpoints. Verifies fox post returns a suggestion, coffee post
returns null, and nonexistent resources return 404.

```
tests/test_api.py::test_fox_post_images_returns_suggestion PASSED
tests/test_api.py::test_coffee_post_images_returns_null_suggestion PASSED
tests/test_api.py::test_nonexistent_post_returns_404 PASSED
tests/test_api.py::test_get_suggestion_404 PASSED
tests/test_api.py::test_approve_suggestion_404 PASSED
```

**`tests/test_low_confidence_flagging.py` (7 tests)** — verifies that
images tagged with confidence below 0.7 are flagged as
`[LOW CONFIDENCE FLAGGED]` but still saved to the database (not skipped).
Tests threshold value, flagged vs not-flagged behavior, boundary conditions
(0.7 exactly is not flagged, 0.69 is), and that low-confidence images are
persisted with all fields intact.

```
tests/test_low_confidence_flagging.py::TestLowConfidenceFlagging::test_threshold_is_0_7 PASSED
tests/test_low_confidence_flagging.py::TestLowConfidenceFlagging::test_low_confidence_image_is_flagged PASSED
tests/test_low_confidence_flagging.py::TestLowConfidenceFlagging::test_high_confidence_image_is_not_flagged PASSED
tests/test_low_confidence_flagging.py::TestLowConfidenceFlagging::test_boundary_confidence_exactly_threshold_is_not_flagged PASSED
tests/test_low_confidence_flagging.py::TestLowConfidenceFlagging::test_just_below_threshold_is_flagged PASSED
tests/test_low_confidence_flagging.py::TestLowConfidenceFlagging::test_low_confidence_image_still_saved_not_skipped PASSED
tests/test_low_confidence_flagging.py::TestLowConfidenceFlagging::test_summary_counter_increments_for_low_confidence PASSED
```

Full suite output:

```
======================== 36 passed, 2 warnings in 6.54s ========================
```

### Semantic matching handles synonyms and scientific names

The brief explicitly mentions "Vulpes vulpes" as an example of a scientific
name that should match posts about foxes. The `category_match()` function now
uses a `CATEGORY_ALIASES` dictionary and `normalize_to_category()` to map
scientific names to their common category before comparing.

Test proving it works:

```python
def test_scientific_name_matches_common_name(self):
    img = _fake_image(subject="Vulpes vulpes")
    post = _fake_post(
        title="The Secret Life of Red Foxes",
        body="Foxes live in forests.",
    )
    assert category_match(img.subject, post.title, post.body) is True
```

Before the fix, `category_match("Vulpes vulpes", "The Secret Life of Red Foxes", ...)` returned `False` because the word "vulpes" doesn't literally appear in the post text. After the fix it returns `True` because both sides normalize to the "fox" category.

### Approve/reject is idempotent

Each suggestion should have at most one approval record. Calling approve or
reject twice on the same suggestion now updates the existing row instead of
inserting a new one.

Test proving it:

```python
def test_approve_is_idempotent(fox_suggestion_id):
    # Clean slate
    db.execute(text("DELETE FROM approvals WHERE suggestion_id = :sid"),
               {"sid": fox_suggestion_id})
    db.commit()

    resp1 = client.post(f"/suggestions/{fox_suggestion_id}/approve",
                        json={"note": "first"})
    approval_id_1 = resp1.json()["approval"]["id"]

    resp2 = client.post(f"/suggestions/{fox_suggestion_id}/approve",
                        json={"note": "second"})
    approval_id_2 = resp2.json()["approval"]["id"]

    assert approval_id_1 == approval_id_2          # same row, not a new one
    assert resp2.json()["approval"]["reviewer_note"] == "second"

    count = db.execute(text("SELECT COUNT(*) FROM approvals WHERE suggestion_id = :sid"),
                       {"sid": fox_suggestion_id}).scalar()
    assert count == 1                               # only 1 row, not 2
```

Before the fix: 2 calls = 2 approval rows. After: 2 calls = 1 row, updated.

### Low-confidence classifications are flagged

Images tagged with confidence below 0.7 are saved to the database (not
skipped), but logged with `[LOW CONFIDENCE FLAGGED]` and counted in the
ingestion summary as `total_low_confidence_flagged`.

The flagging logic in `app/services/batch.py`:

```python
LOW_CONFIDENCE_THRESHOLD = 0.7
# ...
flag = " [LOW CONFIDENCE FLAGGED]" if validated.confidence < LOW_CONFIDENCE_THRESHOLD else ""
if validated.confidence < LOW_CONFIDENCE_THRESHOLD:
    low_confidence += 1
    logger.warning("Low-confidence tag flagged for review: %s", filename)

print(
    f"[{index}/{total}] {filename} -> {validated.subject} "
    f"(confidence {validated.confidence}) - ${cost:.6f}"
    f"{flag} [running total: ${total_cost:.6f}]"
)
```

Unit tests confirm:
- `confidence=0.55` → flagged (True)
- `confidence=0.95` → not flagged (False)
- `confidence=0.70` → NOT flagged (strict `<`, boundary test)
- `confidence=0.69` → flagged (just below boundary)
- Low-confidence images are still saved with all fields intact
