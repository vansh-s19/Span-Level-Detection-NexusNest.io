"""
DistilBERT span-level PII detector: load a trained model and predict spans.

    from pii_detect.model import PIIModel
    m = PIIModel.load("models/distilbert-pii")
    m.predict("my aadhar is 2798 1933 1904")
    -> [{"start": 13, "end": 27, "label": "AADHAAR", "text": "2798 1933 1904"}]

`postprocess_level=1..3` makes each value consistent: merge touching fragments,
vote one label by probability, settle PAN/IFSC/GSTIN by official format.

`checksum_filter=True` turns on the hybrid step: neural networks cannot do
checksum arithmetic, so after the model predicts, structured IDs are checked
with their official rules and dropped if invalid (Aadhaar: Verhoeff;
GSTIN: mod-36; PAN: format and holder-type letter).
"""

from __future__ import annotations

import os
import re
from pathlib import Path

# Keep downloaded model files inside the project (git-ignored), not in ~/.cache.
os.environ.setdefault("HF_HOME", str(Path(__file__).resolve().parent.parent / ".hf_cache"))

import torch  # noqa: E402
from transformers import AutoModelForTokenClassification, AutoTokenizer  # noqa: E402

from datagen.checksums import is_valid_aadhaar, is_valid_gstin  # noqa: E402

from .data import LABELS  # noqa: E402
from .tagging import TAG2ID, decode  # noqa: E402

PAN_HOLDER_TYPES = set("PCHFATBLJG")

# Official formats of the three look-alike alphanumeric codes (used in post-processing step 3).
FORMATS = {
    "PAN": re.compile(r"[A-Z]{3}[PCHFATBLJG][A-Z]\d{4}[A-Z]"),
    "IFSC": re.compile(r"[A-Z]{4}0[A-Z0-9]{6}"),
    "GSTIN": re.compile(r"\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]"),
}
# Column indices of B-<label> and I-<label> for each label.
LABEL_COLS = {l: (TAG2ID[f"B-{l}"], TAG2ID[f"I-{l}"]) for l in LABELS}


def postprocess(spans: list[dict], offsets, probs, text: str, level: int = 3) -> list[dict]:
    """Make each predicted value consistent (Option A).

    level 1: MERGE spans that touch (no character between them) into one span;
             label = the label covering the most characters.
    level 2: + VOTE: label = highest summed probability (B + I) over the span's tokens.
    level 3: + FORMAT: if a PAN/IFSC/GSTIN value fits exactly one official format,
             that format decides the label.
    """
    if level <= 0 or not spans:
        return spans
    merged: list[list[dict]] = []
    for s in sorted(spans, key=lambda x: x["start"]):
        if merged and merged[-1][-1]["end"] == s["start"]:
            merged[-1].append(s)
        else:
            merged.append([s])

    out = []
    for group in merged:
        start, end = group[0]["start"], group[-1]["end"]
        if len(group) == 1:
            label = group[0]["label"]
        else:
            chars: dict[str, int] = {}
            for s in group:
                chars[s["label"]] = chars.get(s["label"], 0) + s["end"] - s["start"]
            label = max(chars, key=chars.get)
        if level >= 2:
            toks = [i for i, (a, b) in enumerate(offsets) if a != b and a >= start and b <= end]
            if toks:
                score = {l: sum(probs[i][b] + probs[i][c] for i in toks) for l, (b, c) in LABEL_COLS.items()}
                label = max(score, key=score.get)
        if level >= 3 and label in FORMATS:
            value = text[start:end].strip().upper()
            fits = [l for l, rx in FORMATS.items() if rx.fullmatch(value)]
            if len(fits) == 1:
                label = fits[0]
        out.append({"start": start, "end": end, "label": label, "text": text[start:end]})
    return out


def pick_device() -> torch.device:
    if torch.backends.mps.is_available():
        return torch.device("mps")  # Apple-silicon GPU
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def passes_checksum(span: dict) -> bool:
    value = span["text"].strip()
    if span["label"] == "AADHAAR":
        return is_valid_aadhaar(value)
    if span["label"] == "GSTIN":
        return is_valid_gstin(value)
    if span["label"] == "PAN":
        return re.fullmatch(r"[A-Z]{5}\d{4}[A-Z]", value.upper()) is not None and value[3].upper() in PAN_HOLDER_TYPES
    return True  # labels without a checksum are kept as predicted


class PIIModel:
    def __init__(self, model, tokenizer, device, max_length: int = 256):
        self.model, self.tokenizer, self.device, self.max_length = model, tokenizer, device, max_length
        self.model.to(device).eval()

    @classmethod
    def load(cls, path: str | Path, device: torch.device | None = None) -> "PIIModel":
        tokenizer = AutoTokenizer.from_pretrained(path)
        model = AutoModelForTokenClassification.from_pretrained(path)
        return cls(model, tokenizer, device or pick_device())

    @torch.no_grad()
    def predict_batch(self, texts: list[str], batch_size: int = 64, checksum_filter: bool = False,
                      postprocess_level: int = 0) -> list[list[dict]]:
        results = []
        for i in range(0, len(texts), batch_size):
            chunk = texts[i:i + batch_size]
            enc = self.tokenizer(chunk, truncation=True, max_length=self.max_length, padding=True,
                                 return_offsets_mapping=True, return_tensors="pt")
            offsets = enc.pop("offset_mapping").tolist()
            logits = self.model(**{k: v.to(self.device) for k, v in enc.items()}).logits
            tag_ids = logits.argmax(-1).cpu().tolist()
            all_probs = logits.softmax(-1).cpu().tolist() if postprocess_level >= 2 else [None] * len(chunk)
            for text, tags, offs, mask, probs in zip(chunk, tag_ids, offsets, enc["attention_mask"].tolist(), all_probs):
                n = sum(mask)  # ignore padding positions
                spans = decode(tags[:n], offs[:n], text)
                if postprocess_level:
                    spans = postprocess(spans, offs[:n], probs, text, postprocess_level)
                if checksum_filter:
                    spans = [s for s in spans if passes_checksum(s)]
                results.append(spans)
        return results

    def predict(self, text: str, checksum_filter: bool = False, postprocess_level: int = 0) -> list[dict]:
        return self.predict_batch([text], checksum_filter=checksum_filter, postprocess_level=postprocess_level)[0]
