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

---

## Not yet done (Phase 4)

- [ ] POST /images/ingest endpoint (currently CLI-only)
- [ ] GET /posts/{id}/images endpoint
- [ ] POST /suggestions/{id}/approve and /reject endpoints
- [ ] Evaluation dataset and precision reporting
