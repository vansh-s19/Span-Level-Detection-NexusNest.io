"""
Fine-tune DistilBERT (cased) for span-level PII detection.

    .venv/bin/python -m pii_detect.train                 # full run
    .venv/bin/python -m pii_detect.train --limit 300 --epochs 1 --out models/smoke   # quick check

What happens:
  1. Load data/final/train.jsonl and validation.jsonl.
  2. Tokenise and turn spans into BIO token labels (pii_detect/tagging.py).
  3. Start from the pretrained `distilbert-base-cased` weights (general
     English knowledge) with a new classification layer of 17 outputs
     (O + B-/I- for 8 labels), then train on our data. This is FINE-TUNING.
  4. After every epoch, score span-level F1 of the FINAL system (model +
     post-processing + repair) on VALIDATION and keep the best checkpoint. The test sets are never used here, so they stay unbiased.

Loss: cross-entropy per token (special and padding tokens ignored).
Optimiser: AdamW, linear warm-up (first 10% of steps) then linear decay.
"""

from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path

from .model import PIIModel, pick_device  # sets HF_HOME before transformers import

import torch
from torch.utils.data import DataLoader
from transformers import (AutoModelForTokenClassification, AutoTokenizer,
                          DataCollatorForTokenClassification, get_linear_schedule_with_warmup)

from .data import LABELS, load_jsonl
from .metrics import evaluate
from .tagging import ID2TAG, TAG2ID, encode


def set_seed(seed: int) -> None:
    random.seed(seed)
    torch.manual_seed(seed)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--base-model", default="distilbert-base-cased")
    p.add_argument("--train", type=Path, default=Path("data/final/train.jsonl"))
    p.add_argument("--extra-train", type=Path, nargs="*", default=[],
                   help="more training-only files, e.g. data/augment/train_extra.jsonl")
    p.add_argument("--val", type=Path, default=Path("data/final/validation.jsonl"))
    p.add_argument("--out", type=Path, default=Path("models/distilbert-pii"))
    p.add_argument("--epochs", type=int, default=4)
    p.add_argument("--batch-size", type=int, default=16)
    p.add_argument("--lr", type=float, default=5e-5)
    p.add_argument("--weight-decay", type=float, default=0.01)
    p.add_argument("--max-length", type=int, default=128)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--limit", type=int, default=0, help="use only N training examples (smoke test)")
    args = p.parse_args()

    set_seed(args.seed)
    device = pick_device()
    print(f"device: {device}")

    tokenizer = AutoTokenizer.from_pretrained(args.base_model)
    model = AutoModelForTokenClassification.from_pretrained(
        args.base_model, num_labels=len(TAG2ID), id2label=ID2TAG, label2id=TAG2ID)

    train_rows = load_jsonl(args.train)
    for extra in args.extra_train:
        train_rows += load_jsonl(extra)
    val_rows = load_jsonl(args.val)
    if args.limit:
        random.Random(args.seed).shuffle(train_rows)
        train_rows = train_rows[:args.limit]
        val_rows = val_rows[:max(100, args.limit // 5)]

    features, misaligned, truncated = [], 0, 0
    for row in train_rows:
        enc, bad = encode(row, tokenizer, args.max_length)
        misaligned += bad
        truncated += len(enc["input_ids"]) >= args.max_length
        features.append(enc)
    n_spans = sum(len(r["spans"]) for r in train_rows)
    print(f"train examples: {len(features)} | spans: {n_spans} | misaligned spans: {misaligned} "
          f"| truncated examples: {truncated}")

    # Pad every batch to the SAME length. With dynamic padding each batch has a new
    # shape, and the Apple-GPU (MPS) backend keeps memory for every shape it has
    # seen: with long multi-line examples this grew past 16 GB and macOS killed
    # the process. A fixed shape keeps memory flat.
    collator = DataCollatorForTokenClassification(tokenizer, label_pad_token_id=-100,
                                                  padding="max_length", max_length=args.max_length)
    loader = DataLoader(features, batch_size=args.batch_size, shuffle=True, collate_fn=collator,
                        generator=torch.Generator().manual_seed(args.seed))

    model.to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    total_steps = len(loader) * args.epochs
    scheduler = get_linear_schedule_with_warmup(optimizer, int(0.1 * total_steps), total_steps)

    args.out.mkdir(parents=True, exist_ok=True)
    log, best_f1 = [], -1.0
    for epoch in range(1, args.epochs + 1):
        model.train()
        t0, running = time.time(), 0.0
        for step, batch in enumerate(loader, 1):
            batch = {k: v.to(device) for k, v in batch.items()}
            loss = model(**batch).loss
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad()
            if device.type == "mps" and step % 50 == 0:
                torch.mps.empty_cache()  # hand cached GPU memory back to macOS
            running += loss.item()
            if step % 100 == 0 or step == len(loader):
                print(f"epoch {epoch} step {step}/{len(loader)} loss {running / step:.4f}", flush=True)

        # --- validation: real span-level metric, same code as the baselines ---
        # The epoch is chosen on the FINAL system (what ships), and the raw model's
        # score is logged next to it: the best raw checkpoint is not always the best final one.
        detector = PIIModel(model, tokenizer, device)
        val_texts = [r["text"] for r in val_rows]
        raw = evaluate(val_rows, detector.predict_batch(val_texts), LABELS)
        scores = evaluate(val_rows, detector.detect_batch(val_texts), LABELS)
        entry = {"epoch": epoch, "train_loss": running / len(loader), "val_strict_f1": scores["micro"]["f1"],
                 "val_precision": scores["micro"]["precision"], "val_recall": scores["micro"]["recall"],
                 "val_false_alarm_rate": scores["false_alarm_rate"], "val_raw_strict_f1": raw["micro"]["f1"],
                 "minutes": (time.time() - t0) / 60}
        log.append(entry)
        print(json.dumps(entry), flush=True)

        if entry["val_strict_f1"] > best_f1:
            best_f1 = entry["val_strict_f1"]
            model.save_pretrained(args.out)
            tokenizer.save_pretrained(args.out)
            print(f"  -> new best (val strict F1 {best_f1:.4f}), saved to {args.out}", flush=True)

    (args.out / "training_log.json").write_text(json.dumps(
        {"args": {k: str(v) for k, v in vars(args).items()}, "device": str(device), "epochs": log,
         "best_val_strict_f1": best_f1, "misaligned_spans": misaligned, "truncated_examples": truncated},
        indent=2))
    print(f"done. best validation strict F1: {best_f1:.4f}")


if __name__ == "__main__":
    main()
