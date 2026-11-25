"""
Try the trained model in the terminal.

    .venv/bin/python -m pii_detect.demo                      # interactive: type sentences
    .venv/bin/python -m pii_detect.demo "my PAN is ABCPK1234F"   # one sentence
    .venv/bin/python -m pii_detect.demo --raw                # model only (no post-processing / checksum)

Detected PII is highlighted in the sentence and listed below it.
Type `q` (or press Ctrl+C) to quit.
"""

from __future__ import annotations

import os
import sys

os.environ.setdefault("HF_HUB_OFFLINE", "1")  # model is local; never go online

from .model import PIIModel  # noqa: E402

COLORS = {"AADHAAR": "41", "PAN": "45", "PHONE": "44", "EMAIL": "46",
          "BANK_ACCOUNT": "43;30", "IFSC": "42;30", "GSTIN": "47;30", "PERSON": "101"}


def show(text: str, spans: list[dict]) -> None:
    out, pos = [], 0
    for s in sorted(spans, key=lambda x: x["start"]):
        out.append(text[pos:s["start"]])
        out.append(f"\033[{COLORS.get(s['label'], '7')}m{text[s['start']:s['end']]}\033[0m")
        pos = s["end"]
    out.append(text[pos:])
    print("\n  " + "".join(out))
    if not spans:
        print("  \033[32mno PII found\033[0m")
    for s in spans:
        print(f"  {s['label']:13} {s['text']!r}  (chars {s['start']}-{s['end']})")


def main() -> None:
    args = sys.argv[1:]
    raw = "--raw" in args
    args = [a for a in args if a != "--raw"]
    opts = {} if raw else {"postprocess_level": 3, "checksum_filter": True}

    print("loading model ...")
    model = PIIModel.load("models/distilbert-pii")
    print(f"ready ({'raw model' if raw else 'final system: model + post-processing + checksum'})")

    if args:
        text = " ".join(args)
        show(text, model.predict(text, **opts))
        return
    try:
        while True:
            text = input("\ntext> ").strip()
            if text.lower() in {"q", "quit", "exit"}:
                break
            if text:
                show(text, model.predict(text, **opts))
    except (KeyboardInterrupt, EOFError):
        print()


if __name__ == "__main__":
    main()
