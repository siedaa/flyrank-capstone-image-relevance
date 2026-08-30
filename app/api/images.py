from fastapi import APIRouter, BackgroundTasks

from app.services.batch import run_batch_ingestion

router = APIRouter()


def _run_ingestion_background() -> None:
    run_batch_ingestion()


@router.post("/ingest", status_code=202)
def ingest_images(background_tasks: BackgroundTasks) -> dict:
    background_tasks.add_task(_run_ingestion_background)
    return {"status": "started", "message": "Batch ingestion running in background"}
