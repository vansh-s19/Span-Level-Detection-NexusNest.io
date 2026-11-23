"""
Convert the hand-written, human-reviewable test file into span JSONL.

    .venv/bin/python -m datagen.handwritten

Input : data/handwritten/test_annotated.txt   ([[LABEL|value]] markup)
Output: data/handwritten/test.jsonl            same format as data/final/*.jsonl

The markup lets a person read and correct the labels easily; this script
computes the exact character offsets, so nothing is counted by hand. It also
checks each value against the real format rules (Aadhaar checksum, GSTIN
checksum, PAN / IFSC / phone shape) and stops if a gold label is malformed.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from .checksums import is_valid_aadhaar, is_valid_gstin
from .values import LABELS

MARK_RE = re.compile(r"\[\[([A-Z_]+)\|(.+?)\]\]")

FORMAT_CHECKS = {
    "AADHAAR": is_valid_aadhaar,
    "GSTIN": is_valid_gstin,
    "PAN": lambda v: re.fullmatch(r"[A-Z]{5}\d{4}[A-Z]", v.upper()) is not None,
    "IFSC": lambda v: re.fullmatch(r"[A-Z]{4}0[A-Z0-9]{6}", v.upper()) is not None,
    "PHONE": lambda v: re.fullmatch(r"(\+?91[\s-]?|0)?[6-9][\d\s-]{9,12}", v) is not None
                       and len(re.sub(r"\D", "", v)[-10:]) == 10,
    "EMAIL": lambda v: re.fullmatch(r"[^@\s]+@[^@\s]+\.[A-Za-z]{2,}", v) is not None,
    "BANK_ACCOUNT": lambda v: v.isdigit() and 9 <= len(v) <= 18,
    "PERSON": lambda v: bool(v.strip()),
}


def parse_line(line: str) -> tuple[str, list[dict]]:
    line = line.replace("\\n", "\n")  # allow multi-line examples on one line
    text_parts, spans, cursor, pos = [], [], 0, 0
    for m in MARK_RE.finditer(line):
        literal = line[pos:m.start()]
        text_parts.append(literal)
        cursor += len(literal)
        label, value = m.group(1), m.group(2)
        if label not in LABELS:
            raise ValueError(f"Unknown label {label!r} in: {line}")
        if not FORMAT_CHECKS[label](value):
            raise ValueError(f"{label} value {value!r} fails its format check in: {line}")
        spans.append({"start": cursor, "end": cursor + len(value), "label": label, "text": value})
        text_parts.append(value)
        cursor += len(value)
        pos = m.end()
    text_parts.append(line[pos:])
    text = "".join(text_parts)
    for s in spans:
        assert text[s["start"]:s["end"]] == s["text"]
    return text, spans


def main() -> None:
    src = Path("data/handwritten/test_annotated.txt")
    out = Path("data/handwritten/test.jsonl")
    examples, category = [], "uncategorised"
    for raw in src.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if not line:
            continue
        if line.startswith("## "):
            category = line[3:].strip()
            continue
        if line.startswith("#"):
            continue
        text, spans = parse_line(line)
        examples.append({"id": f"hand-{len(examples) + 1:04d}", "text": text, "spans": spans,
                         "kind": "positive" if spans else "negative", "category": category,
                         "template_id": None, "source": "handwritten"})
    with open(out, "w", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    print(f"examples: {len(examples)}  (with PII: {sum(bool(e['spans']) for e in examples)}, "
          f"no PII: {sum(not e['spans'] for e in examples)})")
    print("by category:", dict(Counter(e["category"] for e in examples)))
    print("spans per label:", dict(Counter(s["label"] for e in examples for s in e["spans"])))


if __name__ == "__main__":
    main()
