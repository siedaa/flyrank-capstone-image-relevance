# Design Doc — AI Image Understanding & Content Matching Engine

## Problem

Match blog post content to the correct image from a small image library, 

using semantic meaning rather than filenames or keywords, while refusing 

to suggest an image when no confident match exists.

## Data model

- images: id, filename, subject, category, attributes (JSON list), caption, 

  confidence, embedding (float array), created_at

- posts: id, title, body, embedding (float array), created_at

- suggestions: id, post_id (FK), image_id (FK), similarity_score, 

  guard_verdict (accepted/rejected), reason, created_at

- approvals: id, suggestion_id (FK), decision (approved/rejected), 

  reviewer_note, created_at

## API surface

- GET /health

- POST /images/ingest — triggers batch vision tagging job

- GET /posts/{id}/images — ranked image suggestions for a post

- POST /suggestions/{id}/approve

- POST /suggestions/{id}/reject

## Mismatch guard rule

An image is only suggested for a post if it passes all three checks:

1. Category match — the image's `subject` must correspond to the animal/topic 

   the post is actually about. A literal or near-literal mismatch (e.g. wolf 

   image on a fox post) fails this check immediately.

2. Semantic similarity floor — cosine similarity between the image caption's 

   embedding and the post's embedding must clear a minimum threshold. This 

   catches both loosely-related false positives (e.g. a generic dog image on 

   a wolf post) and correctly accepts synonym/scientific-name matches (e.g. 

   "Vulpes vulpes" matching "red fox") that Check 1 alone would miss, since 

   it compares meaning rather than exact words.

3. Confidence floor — the image's own Gemini-assigned confidence score must 

   clear a minimum threshold. Low-confidence tags are never used as the basis 

   of a suggestion, even if they otherwise match.

If any check fails, the suggestion is rejected with a human-readable reason 

naming which check failed (e.g. "Category mismatch: expected fox, detected 

wolf"). If every candidate image fails, the system returns "no confident 

match" with the specific reasons.

Exact threshold values for checks 2 and 3 are placeholders until Phase 3/4, 

where they will be tuned against a labeled evaluation dataset and reported 

as a top-1 precision number.

## Non-goal

No frontend UI. The review workflow is exposed as API endpoints only.
