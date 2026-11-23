"""
Rule-based baselines.

1. PreflightRegex  - a faithful Python port of Pre-flight's Layer 1
   (src/detectors.js) for the 8 labels in this project. Same regexes, same
   `isPlausibleAadhaar` heuristic, same rule that bank accounts need a
   nearby "account"/"a/c" label. Pre-flight has no name detector, so PERSON
   recall is 0 by design.

2. RegexChecksum   - the same patterns, plus the official validity rules:
     Aadhaar : first digit 2-9 AND valid Verhoeff check digit
     GSTIN   : valid mod-36 check character
     PAN     : 4th character must be a real holder type (P, C, H, F, A, T, B, L, J, G)
   This is the strongest "no ML" approach and the fair bar for the model.

Both return spans as {"start", "end", "label", "text"}.
"""

from __future__ import annotations

import re

from datagen.checksums import is_valid_aadhaar, is_valid_gstin

# --- regexes copied from Pre-flight src/detectors.js ---------------------
AADHAAR_RE = re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b")
PAN_RE = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", re.IGNORECASE)
GST_RE = re.compile(r"\b(?:0[1-9]|[12]\d|3[0-8])[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z]\b", re.IGNORECASE)
IFSC_RE = re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b", re.IGNORECASE)
BANK_ACCOUNT_RE = re.compile(
    r"\b(?:bank\s+)?(?:a/?c|account)(?:\s+(?:number|no\.?))?\s*[:#=-]?\s*(\d[\d\s-]{7,24}\d)\b", re.IGNORECASE)
PHONE_RE = re.compile(r"(?:^|(?<![\w]))(?:(?:\(\+?91\)|\+91|91)[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?!\w)")
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

PAN_HOLDER_TYPES = set("PCHFATBLJG")


def _is_plausible_aadhaar(value: str) -> bool:
    """Port of isPlausibleAadhaar() from detectors.js."""
    digits = re.sub(r"\D", "", value)
    if len(digits) != 12:
        return False
    if re.fullmatch(r"(\d)\1{11}", digits):
        return False
    grouped = re.fullmatch(r"\d{4}[\s-]\d{4}[\s-]\d{4}", value.strip()) is not None
    if not grouped and digits[0] in "01":
        return False
    groups = re.findall(r"\d{4}", digits)
    if all(re.fullmatch(r"(?:19|20)\d\d", g) for g in groups):
        return False
    return True


def _span(m: re.Match, label: str, group: int = 0) -> dict:
    return {"start": m.start(group), "end": m.end(group), "label": label, "text": m.group(group)}


class PreflightRegex:
    name = "Pre-flight regex (current)"

    def aadhaar_ok(self, v: str) -> bool:
        return _is_plausible_aadhaar(v)

    def pan_ok(self, v: str) -> bool:
        return True

    def gstin_ok(self, v: str) -> bool:
        return True

    def predict(self, text: str) -> list[dict]:
        spans = []
        spans += [_span(m, "AADHAAR") for m in AADHAAR_RE.finditer(text) if self.aadhaar_ok(m.group())]
        spans += [_span(m, "PAN") for m in PAN_RE.finditer(text) if self.pan_ok(m.group())]
        spans += [_span(m, "GSTIN") for m in GST_RE.finditer(text) if self.gstin_ok(m.group())]
        spans += [_span(m, "IFSC") for m in IFSC_RE.finditer(text)]
        spans += [_span(m, "BANK_ACCOUNT", 1) for m in BANK_ACCOUNT_RE.finditer(text)]
        spans += [_span(m, "PHONE") for m in PHONE_RE.finditer(text)]
        spans += [_span(m, "EMAIL") for m in EMAIL_RE.finditer(text)]
        return sorted(spans, key=lambda s: s["start"])


class RegexChecksum(PreflightRegex):
    name = "Regex + checksum"

    def aadhaar_ok(self, v: str) -> bool:
        return is_valid_aadhaar(v)

    def pan_ok(self, v: str) -> bool:
        return v[3].upper() in PAN_HOLDER_TYPES

    def gstin_ok(self, v: str) -> bool:
        return is_valid_gstin(v)
