"""
Evaluate the rule-based baselines on both test sets.

    .venv/bin/python -m pii_detect.run_baselines

Writes results/baselines.json and results/baselines.md, plus
results/baseline_errors.md with concrete false alarms and misses
(the error analysis is what explains the numbers).
"""

from __future__ import annotations

import json
from pathlib import Path

from .baselines import PreflightRegex, RegexChecksum
from .data import LABELS, TEST_SETS, load_jsonl
from .metrics import evaluate


def fmt(x: float) -> str:
    return f"{x * 100:5.1f}"


def main() -> None:
    detectors = [PreflightRegex(), RegexChecksum()]
    results, md, errors = {}, ["# Baseline results\n"], ["# Baseline error examples\n"]
    for set_name, path in TEST_SETS.items():
        examples = load_jsonl(path)
        md.append(f"\n## {set_name} ({len(examples)} sentences)\n")
        md.append("| Detector | Strict P | Strict R | Strict F1 | Partial F1 | Macro F1 | False-alarm rate on clean sentences |")
        md.append("|---|---|---|---|---|---|---|")
        per_label_rows = []
        for det in detectors:
            preds = [det.predict(ex["text"]) for ex in examples]
            strict = evaluate(examples, preds, LABELS)
            partial = evaluate(examples, preds, LABELS, partial=True)
            results[f"{set_name}/{det.name}"] = {"strict": strict, "partial": partial}
            m = strict["micro"]
            md.append(f"| {det.name} | {fmt(m['precision'])} | {fmt(m['recall'])} | {fmt(m['f1'])} | "
                      f"{fmt(partial['micro']['f1'])} | {fmt(strict['macro_f1'])} | "
                      f"{fmt(strict['false_alarm_rate'])}% ({strict['negative_sentences_with_alarm']}/{strict['negative_sentences']}) |")
            per_label_rows.append((det.name, strict["per_label"]))

            # Collect a few concrete errors per detector for the error analysis.
            errors.append(f"\n## {set_name}: {det.name}\n")
            shown = 0
            for ex, pr in zip(examples, preds):
                gold = {(s["start"], s["end"], s["label"]) for s in ex["spans"]}
                got = {(s["start"], s["end"], s["label"]) for s in pr}
                fps, fns = got - gold, gold - got
                if (fps or fns) and shown < 12:
                    shown += 1
                    errors.append(f"- `{ex['text'][:160]}`")
                    for s, e, l in sorted(fps):
                        errors.append(f"  - FALSE ALARM {l}: `{ex['text'][s:e]}`")
                    for s, e, l in sorted(fns):
                        errors.append(f"  - MISSED {l}: `{ex['text'][s:e]}`")

        md.append("\nPer-label strict F1 (support = number of gold spans):\n")
        md.append("| Label | support | " + " | ".join(n for n, _ in per_label_rows) + " |")
        md.append("|---|---|" + "---|" * len(per_label_rows))
        for label in LABELS:
            support = per_label_rows[0][1][label]["support"]
            md.append(f"| {label} | {support} | " + " | ".join(fmt(pl[label]["f1"]) for _, pl in per_label_rows) + " |")

    Path("results").mkdir(exist_ok=True)
    Path("results/baselines.json").write_text(json.dumps(results, indent=2))
    Path("results/baselines.md").write_text("\n".join(md) + "\n")
    Path("results/baseline_errors.md").write_text("\n".join(errors) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
