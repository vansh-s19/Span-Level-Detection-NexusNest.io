"""Load the JSONL datasets produced by datagen/."""

from __future__ import annotations

import json
from pathlib import Path

LABELS = ["AADHAAR", "PAN", "PHONE", "EMAIL", "BANK_ACCOUNT", "IFSC", "GSTIN", "PERSON"]

TEST_SETS = {
    "synthetic_test": Path("data/final/test.jsonl"),
    "handwritten_test": Path("data/handwritten/test.jsonl"),
}


def load_jsonl(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]
