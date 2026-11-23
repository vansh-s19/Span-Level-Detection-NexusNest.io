"""
Filter ai4privacy open-pii-masking-500k (CC BY 4.0) into our label scheme and
merge a 5,000-row sample into the TRAINING split only.

Run from the project root (after generate.py):
    .venv/bin/python -m datagen.ai4privacy

Input : data/raw/ai4privacy/open_pii_500k_part.jsonl   (downloaded by you)
Output: data/ai4privacy/train_5k.jsonl                  the filtered sample
        data/final/{train,validation,test}.jsonl        what models train on
        data/final/stats.json

Mapping rules (agreed before writing this):
  GIVENNAME / SURNAME   -> PERSON (adjacent first + last name merged into one span)
  EMAIL                 -> EMAIL
  TELEPHONENUM          -> row dropped (mostly non-Indian formats; our PHONE = Indian)
  ID-type labels        -> row dropped (would wrongly teach "IDs are not PII")
  everything else       -> plain text (outside our 8 labels)
Only English rows are used. Validation and test stay 100% our own data.

Attribution: ai4privacy, open-pii-masking-500k-ai4privacy, CC BY 4.0.
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter
from pathlib import Path

MAP = {"GIVENNAME": "PERSON", "SURNAME": "PERSON", "EMAIL": "EMAIL"}
DROP_ROW = {"TELEPHONENUM", "IDCARDNUM", "TAXNUM", "SOCIALNUM", "PASSPORTNUM",
            "DRIVERLICENSENUM", "CREDITCARDNUMBER"}


def convert(row: dict) -> tuple[dict | None, str]:
    """Return (example, reason). Example is None when the row is rejected."""
    if row.get("language") != "en":
        return None, "not_english"
    text = row["source_text"]
    masks = sorted(row["privacy_mask"], key=lambda m: m["start"])
    if any(m["label"] in DROP_ROW for m in masks):
        return None, "has_phone_or_id_label"

    spans = []
    for m in masks:
        label = MAP.get(m["label"])
        if label is None:
            continue
        if text[m["start"]:m["end"]] != m["value"]:
            return None, "offset_mismatch"  # never trust a misaligned label
        prev = spans[-1] if spans else None
        # Merge "Priya" + "Sharma" into one PERSON span when only spaces separate them.
        if (prev and label == "PERSON" and prev["label"] == "PERSON"
                and text[prev["end"]:m["start"]].strip() == ""
                and m["start"] - prev["end"] <= 2):
            prev["end"] = m["end"]
            prev["text"] = text[prev["start"]:prev["end"]]
        else:
            spans.append({"start": m["start"], "end": m["end"], "label": label,
                          "text": text[m["start"]:m["end"]]})
    return {"text": text, "spans": spans, "kind": "positive" if spans else "negative",
            "template_id": None, "source": "ai4privacy", "source_uid": row.get("uid")}, "kept"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, default=Path("data/raw/ai4privacy/open_pii_500k_part.jsonl"))
    p.add_argument("--synthetic", type=Path, default=Path("data/synthetic"))
    p.add_argument("--out", type=Path, default=Path("data/final"))
    p.add_argument("--n", type=int, default=5000)
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    kept, reasons = [], Counter()
    with open(args.input, encoding="utf-8") as f:
        for line in f:
            ex, reason = convert(json.loads(line))
            reasons[reason] += 1
            if ex:
                kept.append(ex)

    rng = random.Random(args.seed)
    sample = rng.sample(kept, min(args.n, len(kept)))
    for i, ex in enumerate(sample, 1):
        ex["id"] = f"ai4p-{i:05d}"

    Path("data/ai4privacy").mkdir(parents=True, exist_ok=True)
    with open("data/ai4privacy/train_5k.jsonl", "w", encoding="utf-8") as f:
        for ex in sample:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    args.out.mkdir(parents=True, exist_ok=True)
    stats = {"filter": dict(reasons), "eligible_rows": len(kept), "sampled": len(sample), "splits": {}}
    for split in ("train", "validation", "test"):
        rows = [json.loads(l) for l in open(args.synthetic / f"{split}.jsonl", encoding="utf-8")]
        if split == "train":
            rows += sample
            rng.shuffle(rows)
        with open(args.out / f"{split}.jsonl", "w", encoding="utf-8") as f:
            for ex in rows:
                f.write(json.dumps(ex, ensure_ascii=False) + "\n")
        stats["splits"][split] = {
            "examples": len(rows),
            "by_source": dict(Counter(r["source"] for r in rows)),
            "spans_per_label": dict(Counter(s["label"] for r in rows for s in r["spans"])),
        }
    with open(args.out / "stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
