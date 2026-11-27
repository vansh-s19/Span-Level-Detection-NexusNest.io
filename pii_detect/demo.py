"""
Try the trained model in the terminal.

    .venv/bin/python -m pii_detect.demo                      # interactive: paste text, then an empty line
    .venv/bin/python -m pii_detect.demo "my PAN is ABCPK1234F"   # one sentence
    .venv/bin/python -m pii_detect.demo --file prompt.txt     # a whole file (any length)
    cat prompt.txt | .venv/bin/python -m pii_detect.demo      # piped input
    .venv/bin/python -m pii_detect.demo --raw                # model only (no post-processing / checksum)
    .venv/bin/python -m pii_detect.demo --model path/to/model

Interactive mode reads MULTI-LINE text: paste as many lines as you like and
press Enter on an empty line to scan them together. Long text is scanned in
full (sliding window), never cut off.

Detected PII is highlighted in the text and listed below it.
Type `q` (or press Ctrl+C) to quit.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")  # model is local; never go online

from .model import FINAL, PIIModel  # noqa: E402

COLORS = {"AADHAAR": "41", "PAN": "45", "PHONE": "44", "EMAIL": "46",
          "BANK_ACCOUNT": "43;30", "IFSC": "42;30", "GSTIN": "47;30", "PERSON": "101"}
# Default model folder, found relative to this file so the demo works from any directory.
DEFAULT_MODEL = Path(__file__).resolve().parent.parent / "models" / "distilbert-pii"


def show(text: str, spans: list[dict]) -> None:
    out, pos = [], 0
    for s in sorted(spans, key=lambda x: x["start"]):
        out.append(text[pos:s["start"]])
        out.append(f"\033[{COLORS.get(s['label'], '7')}m{text[s['start']:s['end']]}\033[0m")
        pos = s["end"]
    out.append(text[pos:])
    print("\n  " + "".join(out).replace("\n", "\n  "))
    if not spans:
        print("  \033[32mno PII found\033[0m")
    for s in spans:
        note = f"  [{s['note']}]" if "note" in s else ""
        print(f"  {s['label']:13} {s['text']!r}  (chars {s['start']}-{s['end']}){note}")


def read_block() -> str | None:
    """Read lines until an empty line. Returns None on quit / end of input."""
    lines = []
    prompt = "\ntext> "
    while True:
        try:
            line = input(prompt)
        except EOFError:
            return "\n".join(lines) if lines else None
        if not lines and line.strip().lower() in {"q", "quit", "exit"}:
            return None
        if not line.strip():
            if lines:
                return "\n".join(lines)
            continue
        lines.append(line)
        prompt = "....> "


def main() -> None:
    p = argparse.ArgumentParser(description="Scan text for PII.")
    p.add_argument("text", nargs="*", help="text to scan (omit for interactive mode)")
    p.add_argument("--raw", action="store_true", help="model only, no post-processing / checksum")
    p.add_argument("--file", type=Path, help="scan the contents of this file")
    p.add_argument("--model", type=Path, default=DEFAULT_MODEL, help="model folder")
    args = p.parse_args()
    opts = {} if args.raw else FINAL

    print("loading model ...")
    model = PIIModel.load(args.model)
    print(f"ready ({'raw model' if args.raw else 'final system: normalise + model + post-processing + repair'})")

    if args.file or args.text or not sys.stdin.isatty():
        text = (args.file.read_text(encoding="utf-8") if args.file
                else " ".join(args.text) if args.text else sys.stdin.read())
        show(text, model.predict(text, **opts))
        return
    print("paste text (multiple lines are fine), then press Enter on an empty line. q to quit.")
    try:
        while (text := read_block()) is not None:
            show(text, model.predict(text, **opts))
    except KeyboardInterrupt:
        print()


if __name__ == "__main__":
    main()
