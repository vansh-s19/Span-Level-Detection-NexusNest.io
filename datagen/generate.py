"""
Generate the synthetic span-level PII dataset.

Run from the project root:
    .venv/bin/python -m datagen.generate

Output (data/synthetic/):
    train.jsonl, validation.jsonl, test.jsonl   one example per line
    stats.json                                  counts per split / label
    samples.txt                                 a few readable examples

Each example:
    {"id": "train-000001",
     "text": "my aadhar is 2345 6789 0124 pls check",
     "spans": [{"start": 13, "end": 27, "label": "AADHAAR", "text": "2345 6789 0124"}],
     "kind": "positive" | "negative",
     "template_id": "P017",
     "source": "synthetic"}

`start`/`end` are character offsets (end exclusive), so text[start:end]
is always exactly the PII value. That is what "span-level" means.
"""

from __future__ import annotations

import argparse
import json
import random
import re
from collections import Counter
from pathlib import Path

from .templates import NEGATIVE_TEMPLATES, POSITIVE_TEMPLATES
from .values import FILLERS, LABELS, PII_SLOTS, make_person

SLOT_RE = re.compile(r"\{([A-Za-z0-9_]+)\}")
SPLITS = ("train", "validation", "test")


def _labels_in(template: str) -> set[str]:
    return {PII_SLOTS[s][0] for s in SLOT_RE.findall(template) if s in PII_SLOTS}


def split_templates(templates: list[str], prefix: str, rng: random.Random,
                    fractions=(0.70, 0.15, 0.15), min_templates_per_label: int = 0):
    """Assign each template to exactly one split.

    This is the key anti-leakage step: the test set is built only from
    sentence patterns the model never saw in training, so a good test score
    means the model learned the PII itself, not the template wording.

    A purely random split can leave a label out of a small split entirely
    (the first run had zero IFSC examples in validation). With
    `min_templates_per_label`, we reshuffle until every label appears in at
    least that many templates in validation AND test. The search is driven
    by the same seeded rng, so the result is still reproducible.
    """
    ids = [f"{prefix}{i:03d}" for i in range(len(templates))]
    n_train = round(len(templates) * fractions[0])
    n_val = round(len(templates) * fractions[1])
    for _attempt in range(10_000):
        order = list(range(len(templates)))
        rng.shuffle(order)
        buckets = {
            "train": order[:n_train],
            "validation": order[n_train:n_train + n_val],
            "test": order[n_train + n_val:],
        }
        if not min_templates_per_label:
            break
        ok = True
        for split in ("validation", "test"):
            counts = Counter(label for i in buckets[split] for label in _labels_in(templates[i]))
            if any(counts[label] < min_templates_per_label for label in LABELS):
                ok = False
                break
        if ok:
            break
    else:
        raise RuntimeError("Could not find a template split covering every label")
    return {split: [(ids[i], templates[i]) for i in idx] for split, idx in buckets.items()}


def render(template: str, rng: random.Random) -> tuple[str, list[dict]]:
    """Fill one template. Returns the text and its labelled spans.

    The text is built left to right, so we always know the exact character
    offset where each inserted PII value starts and ends.
    """
    persona = {"person": make_person(rng)}
    parts: list[str] = []
    spans: list[dict] = []
    cursor = 0
    pos = 0
    for match in SLOT_RE.finditer(template):
        literal = template[pos:match.start()].replace("{{", "{").replace("}}", "}")
        parts.append(literal)
        cursor += len(literal)

        slot = match.group(1)
        if slot in PII_SLOTS:
            label, maker = PII_SLOTS[slot]
            value = maker(rng, persona)
            spans.append({"start": cursor, "end": cursor + len(value), "label": label, "text": value})
        elif slot in FILLERS:
            value = FILLERS[slot](rng)
        else:
            raise KeyError(f"Unknown slot {{{slot}}} in template: {template}")
        parts.append(value)
        cursor += len(value)
        pos = match.end()
    tail = template[pos:].replace("{{", "{").replace("}}", "}")
    parts.append(tail)
    text = "".join(parts)

    # Light noise seen in real typing. Both keep character offsets unchanged.
    if rng.random() < 0.08:
        text = text.lower()
        for span in spans:
            span["text"] = span["text"].lower()
    if rng.random() < 0.15 and text.endswith((".", "!")):
        text = text[:-1]

    for span in spans:  # sanity check: offsets must point at the value
        assert text[span["start"]:span["end"]] == span["text"], (text, span)
    return text, spans


def build_split(split, pos_templates, neg_templates, n_pos, n_neg, rng):
    examples = []
    for kind, templates, n in (("positive", pos_templates, n_pos), ("negative", neg_templates, n_neg)):
        for _ in range(n):
            template_id, template = rng.choice(templates)
            text, spans = render(template, rng)
            examples.append({"text": text, "spans": spans, "kind": kind,
                             "template_id": template_id, "source": "synthetic"})
    rng.shuffle(examples)
    for i, ex in enumerate(examples, 1):
        ex["id"] = f"{split}-{i:06d}"
    return [{"id": ex.pop("id"), **ex} for ex in examples]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, default=Path("data/synthetic"))
    parser.add_argument("--train-pos", type=int, default=8000)
    parser.add_argument("--train-neg", type=int, default=2400)
    parser.add_argument("--eval-pos", type=int, default=1000, help="positives in validation and in test")
    parser.add_argument("--eval-neg", type=int, default=300, help="negatives in validation and in test")
    args = parser.parse_args()

    rng = random.Random(args.seed)
    pos_split = split_templates(POSITIVE_TEMPLATES, "P", rng, min_templates_per_label=2)
    neg_split = split_templates(NEGATIVE_TEMPLATES, "N", rng)

    args.out.mkdir(parents=True, exist_ok=True)
    stats = {"seed": args.seed, "splits": {}}
    samples = []
    for split in SPLITS:
        n_pos = args.train_pos if split == "train" else args.eval_pos
        n_neg = args.train_neg if split == "train" else args.eval_neg
        examples = build_split(split, pos_split[split], neg_split[split], n_pos, n_neg, rng)
        with open(args.out / f"{split}.jsonl", "w", encoding="utf-8") as f:
            for ex in examples:
                f.write(json.dumps(ex, ensure_ascii=False) + "\n")

        label_counts = Counter(s["label"] for ex in examples for s in ex["spans"])
        stats["splits"][split] = {
            "examples": len(examples),
            "positive_examples": sum(ex["kind"] == "positive" for ex in examples),
            "negative_examples": sum(ex["kind"] == "negative" for ex in examples),
            "positive_templates": len(pos_split[split]),
            "negative_templates": len(neg_split[split]),
            "spans_per_label": {label: label_counts.get(label, 0) for label in LABELS},
        }
        samples.extend(examples[:8])

    # Prove the template split is clean (no template used in two splits).
    for name, table in (("positive", pos_split), ("negative", neg_split)):
        seen = [tid for split in SPLITS for tid, _ in table[split]]
        assert len(seen) == len(set(seen)), f"{name} template appears in more than one split"
    stats["template_overlap_between_splits"] = 0

    with open(args.out / "stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
    with open(args.out / "samples.txt", "w", encoding="utf-8") as f:
        for ex in samples:
            f.write(f"[{ex['id']}] ({ex['kind']}, template {ex['template_id']})\n{ex['text']}\n")
            for s in ex["spans"]:
                f.write(f"    {s['label']:<13} {s['start']:>4}-{s['end']:<4} {s['text']!r}\n")
            f.write("\n")

    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
