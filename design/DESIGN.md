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

## Non-goal

No frontend UI. The review workflow is exposed as API endpoints only.
