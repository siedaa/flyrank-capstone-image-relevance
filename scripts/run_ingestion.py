import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.batch import run_batch_ingestion


def main() -> None:
    summary = run_batch_ingestion()
    print("\n===== FINAL SUMMARY =====")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()