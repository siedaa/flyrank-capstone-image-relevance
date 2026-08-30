from fastapi import FastAPI

from app.api.images import router as images_router
from app.api.posts import router as posts_router
from app.api.suggestions import router as suggestions_router

app = FastAPI()

app.include_router(images_router, prefix="/images", tags=["images"])
app.include_router(posts_router, prefix="/posts", tags=["posts"])
app.include_router(suggestions_router, prefix="/suggestions", tags=["suggestions"])


@app.get("/health")
def health():
    return {"status": "ok"}
