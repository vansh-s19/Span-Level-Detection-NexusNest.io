"""
Span-level evaluation, shared by every detector (regex baselines and the ML model),
so all numbers in the results tables are computed the same way.

A prediction and a gold span are both (start, end, label) on the same text.

STRICT match  : same label AND exactly the same start and end.
                "9876543210" vs gold "+91 9876543210" is WRONG under strict.
PARTIAL match : same label AND the character ranges overlap.
                Useful to see whether errors are "missed it" or "boundary off".

For each label we count:
  TP  predicted span that matches a gold span
  FP  predicted span with no matching gold span   (false alarm)
  FN  gold span with no matching prediction       (missed PII)
Precision = TP / (TP + FP)  -> "when it flags something, how often is it right?"
Recall    = TP / (TP + FN)  -> "of all real PII, how much did it catch?"
F1        = harmonic mean of the two.
Micro-average pools all labels' counts (dominated by frequent labels);
macro-average is the plain mean of per-label F1 (every label counts equally).

We also report the FALSE-ALARM RATE: the share of sentences with NO PII where
the detector raised at least one alert. For Pre-flight this is the number a
user feels: every false alarm interrupts them before they send a prompt.
"""

from __future__ import annotations

from collections import defaultdict


def _match(pred, gold_spans, used, partial):
    for i, g in enumerate(gold_spans):
        if i in used or g["label"] != pred["label"]:
            continue
        if partial:
            if pred["start"] < g["end"] and g["start"] < pred["end"]:
                return i
        elif pred["start"] == g["start"] and pred["end"] == g["end"]:
            return i
    return None


def evaluate(examples: list[dict], predictions: list[list[dict]], labels: list[str], partial: bool = False) -> dict:
    """examples[i]["spans"] are gold; predictions[i] are predicted spans for the same text."""
    counts = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})
    neg_total = neg_alarm = 0
    for ex, preds in zip(examples, predictions):
        gold = ex["spans"]
        used: set[int] = set()
        for p in preds:
            i = _match(p, gold, used, partial)
            if i is None:
                counts[p["label"]]["fp"] += 1
            else:
                used.add(i)
                counts[p["label"]]["tp"] += 1
        for i, g in enumerate(gold):
            if i not in used:
                counts[g["label"]]["fn"] += 1
        if not gold:
            neg_total += 1
            neg_alarm += bool(preds)

    def prf(c):
        p = c["tp"] / (c["tp"] + c["fp"]) if c["tp"] + c["fp"] else 0.0
        r = c["tp"] / (c["tp"] + c["fn"]) if c["tp"] + c["fn"] else 0.0
        f = 2 * p * r / (p + r) if p + r else 0.0
        return {"precision": p, "recall": r, "f1": f, **c, "support": c["tp"] + c["fn"]}

    per_label = {label: prf(counts[label]) for label in labels}
    total = {k: sum(counts[l][k] for l in labels) for k in ("tp", "fp", "fn")}
    return {
        "per_label": per_label,
        "micro": prf(total),
        "macro_f1": sum(v["f1"] for v in per_label.values()) / len(labels),
        "false_alarm_rate": neg_alarm / neg_total if neg_total else 0.0,
        "negative_sentences": neg_total,
        "negative_sentences_with_alarm": neg_alarm,
    }
