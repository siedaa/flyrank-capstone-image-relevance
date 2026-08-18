import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.vision import test_hard_cases

if __name__ == "__main__":
    test_hard_cases()