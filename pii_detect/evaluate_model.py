"""
Evaluate the trained DistilBERT model on both test sets and compare it with the
rule-based baselines, using exactly the same metric code.

    .venv/bin/python -m pii_detect.evaluate_model

Writes:
  results/model_results.md     comparison tables (overall + per label + by category)
  results/model_results.json   all numbers
  results/model_errors.md      every remaining model error on the hand-written set,
                               plus samples from the synthetic test set
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from .model import PIIModel  # sets HF_HOME first

from .baselines import PreflightRegex, RegexChecksum
from .data import LABELS, TEST_SETS, load_jsonl
from .metrics import evaluate


def fmt(x: float) -> str:
    return f"{x * 100:5.1f}"


def main(model_dir: str = "models/distilbert-pii") -> None:
    model = PIIModel.load(model_dir)
    preflight, checksum = PreflightRegex(), RegexChecksum()
    systems = {
        "Pre-flight regex": lambda texts: [preflight.predict(t) for t in texts],
        "Regex + checksum": lambda texts: [checksum.predict(t) for t in texts],
        "DistilBERT": lambda texts: model.predict_batch(texts),
        "DistilBERT + checksum filter": lambda texts: model.predict_batch(texts, checksum_filter=True),
        "DistilBERT + post-proc": lambda texts: model.predict_batch(texts, postprocess_level=3),
        "DistilBERT + post-proc + checksum (final)": lambda texts: model.predict_batch(
            texts, postprocess_level=3, checksum_filter=True),
    }

    results, md = {}, ["# DistilBERT results vs baselines\n",
                       "Strict = exact start, end and label. False alarms = share of PII-free sentences with any alert.\n"]
    errors = ["# DistilBERT errors\n"]
    for set_name, path in TEST_SETS.items():
        examples = load_jsonl(path)
        texts = [e["text"] for e in examples]
        md.append(f"\n## {set_name} ({len(examples)} sentences)\n")
        md.append("| System | Strict P | Strict R | Strict F1 | Partial F1 | Macro F1 | False alarms |")
        md.append("|---|---|---|---|---|---|---|")
        per_label, preds_by_system = {}, {}
        for name, run in systems.items():
            preds = run(texts)
            preds_by_system[name] = preds
            s, p = evaluate(examples, preds, LABELS), evaluate(examples, preds, LABELS, partial=True)
            results[f"{set_name}/{name}"] = {"strict": s, "partial": p}
            m = s["micro"]
            md.append(f"| {name} | {fmt(m['precision'])} | {fmt(m['recall'])} | {fmt(m['f1'])} | "
                      f"{fmt(p['micro']['f1'])} | {fmt(s['macro_f1'])} | {fmt(s['false_alarm_rate'])}% "
                      f"({s['negative_sentences_with_alarm']}/{s['negative_sentences']}) |")
            per_label[name] = s["per_label"]

        md.append("\nPer-label strict F1:\n")
        md.append("| Label | support | " + " | ".join(per_label) + " |")
        md.append("|---|---|" + "---|" * len(per_label))
        for label in LABELS:
            sup = per_label["DistilBERT"][label]["support"]
            md.append(f"| {label} | {sup} | " + " | ".join(fmt(per_label[n][label]["f1"]) for n in per_label) + " |")

        # Hand-written set: break down by category (where does each system fail?)
        if any("category" in e for e in examples):
            cats = defaultdict(list)
            for i, e in enumerate(examples):
                cats[e.get("category", "?")].append(i)
            md.append("\nStrict F1 by category (hard_negatives has no PII, so it shows false-alarm sentences instead):\n")
            md.append("| Category | n | " + " | ".join(systems) + " |")
            md.append("|---|---|" + "---|" * len(systems))
            for cat, idx in cats.items():
                sub = [examples[i] for i in idx]
                cells = []
                for name in systems:
                    sp = [preds_by_system[name][i] for i in idx]
                    r = evaluate(sub, sp, LABELS)
                    if cat == "hard_negatives":
                        cells.append(f"{r['negative_sentences_with_alarm']}/{r['negative_sentences']} alarms")
                    else:
                        cells.append(fmt(r["micro"]["f1"]))
                md.append(f"| {cat} | {len(idx)} | " + " | ".join(cells) + " |")

        # Error listing for the model (with checksum filter = final system)
        errors.append(f"\n## {set_name}\n")
        shown, limit = 0, (10_000 if set_name == "handwritten_test" else 25)
        for ex, pr in zip(examples, preds_by_system["DistilBERT + post-proc + checksum (final)"]):
            gold = {(s["start"], s["end"], s["label"]) for s in ex["spans"]}
            got = {(s["start"], s["end"], s["label"]) for s in pr}
            if gold != got and shown < limit:
                shown += 1
                errors.append(f"- `{ex['text'][:200]}`")
                for s, e, l in sorted(got - gold):
                    errors.append(f"  - FALSE ALARM / WRONG {l}: `{ex['text'][s:e]}`")
                for s, e, l in sorted(gold - got):
                    errors.append(f"  - MISSED {l}: `{ex['text'][s:e]}`")
        errors.append(f"\n({shown} sentences with at least one error shown)\n")

    Path("results").mkdir(exist_ok=True)
    Path("results/model_results.json").write_text(json.dumps(results, indent=2))
    Path("results/model_results.md").write_text("\n".join(md) + "\n")
    Path("results/model_errors.md").write_text("\n".join(errors) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
