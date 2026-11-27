"""
DistilBERT span-level PII detector: load a trained model and predict spans.

    from pii_detect.model import PIIModel
    m = PIIModel.load("models/distilbert-pii")
    m.predict("my aadhar is 2798 1933 1904")
    -> [{"start": 13, "end": 27, "label": "AADHAAR", "text": "2798 1933 1904"}]

LONG TEXT. The model was fine-tuned on inputs of at most 128 tokens. Longer
text is read with a SLIDING WINDOW: overlapping 128-token windows (overlap
`stride` tokens), all run as one batch. Each token keeps the prediction from
the window where it sits furthest from an edge (it saw the most context
there). Spans are built once, on the joined result, so nothing is cut off and
nothing is counted twice.

`postprocess_level=1..5` makes each value consistent:
    1 merge touching fragments
    2 + vote one label by probability
    3 + settle PAN/IFSC/GSTIN by official format
    4 + WORDS: snap PERSON / EMAIL spans to whole words, and trim titles,
        honorifics and Hinglish function words from PERSON spans
    5 + CODES and NAMES: snap PAN / IFSC / GSTIN pieces to the whole code
        ("IDIB" + "39456" -> "IDIB0139456"), and join two name pieces
        separated by one space ("om" + "prakash chaurasia")

`checksum_filter=True` turns on the hybrid step: neural networks cannot do
checksum arithmetic, so after the model predicts, structured IDs are checked
with their official rules and dropped if invalid (Aadhaar: Verhoeff;
GSTIN: mod-36; PAN: format and holder-type letter; IFSC: format; PHONE:
Indian mobile format, or an explicit +country code; EMAIL: must contain @;
BANK_ACCOUNT: 9-18 digits). This is the old VETO behaviour.

`repair=True` replaces the veto with REPAIR (the "cures" in docs/edge_cases.md):
a value that fails its own check is not simply deleted. In order:
    masked ID (XXXX XXXX 1904)            -> dropped on purpose (safe by design)
    number glued to TXN / UTR / REF ...   -> dropped (transaction id, not PII)
    tracking / order / ticket cue before  -> dropped (issue 3)
    PAN / IFSC / GSTIN cut short          -> completed ("ABCPK 1234" + " F")
    cue word before it ("aadhaar", "PAN") -> kept, flagged "invalid check digit"
    fits another label's format           -> re-typed (AADHAAR '9876543210' -> PHONE)
    several values glued into one span    -> split into the valid pieces
    otherwise                             -> dropped
and then a RULE FALLBACK adds a value the model missed when it has an exact
format (and checksum) AND its cue word right before it ("UID 7343-0438-3741").

`normalise=True` undoes common hiding tricks BEFORE the model reads the text
("9 8 1 0 5 5 0 1 4 2", "nine eight ...", "rahul dot sharma at gmail dot com",
"rahul[at]gmail[.]com", full-width and Devanagari digits, zero-width spaces)
and maps every span back to its place in the ORIGINAL text.

The final system is `FINAL` (= level 5 + normalise + repair):
    m.predict(text, **FINAL)    or    m.detect(text)
"""

from __future__ import annotations

import os
import re
import unicodedata
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

# --- PHONE format (issue: 12-digit tracking numbers predicted as PHONE) ----------
# Indian mobile: 10 digits starting 6-9, optionally prefixed by 0, 91 or +91.
# A bare 12-digit number therefore must start with 91 to be a phone.
# An explicit "+<country code>" number (7-15 digits) is also accepted, so
# foreign numbers the model finds are not thrown away.
INDIAN_MOBILE_RE = re.compile(r"(?:0|91)?[6-9]\d{9}")
INTL_PHONE_RE = re.compile(r"\+\d{7,15}")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}")


def is_valid_phone(value: str) -> bool:
    compact = re.sub(r"[\s\-()./]", "", value)
    if compact.startswith("+91"):
        return re.fullmatch(r"\+91[6-9]\d{9}", compact) is not None
    if compact.startswith("+"):
        return INTL_PHONE_RE.fullmatch(compact) is not None
    return INDIAN_MOBILE_RE.fullmatch(compact) is not None


# --- WORDS step (level 4) ---------------------------------------------------------
# Characters that belong to a name word / an e-mail address. A span is
# stretched over these so it never ends in the middle of a word
# ("Arinda" -> "Arindam", "Go" -> "Golu").
def _is_name_char(ch: str) -> bool:
    # Letters and combining marks of any script (Devanagari vowel signs are marks), plus apostrophes.
    return unicodedata.category(ch)[0] in "LM" or ch in "'’"


def _is_email_char(ch: str) -> bool:
    return ch.isascii() and (ch.isalnum() or ch in "._%+-@")

# Titles before a name (the dataset convention keeps them OUTSIDE the span).
TITLES = {"mr", "mrs", "ms", "dr", "shri", "smt", "sri", "prof", "miss", "mx"}
# Honorifics and Hinglish / English function words that are never a name on
# their own. Only trimmed from the EDGES of a PERSON span, and only when written
# in lowercase, so a capitalised real name such as "Diya" is never touched.
NON_NAME_WORDS = {
    # honorifics written after a name
    "ji", "bhai", "bhaiya", "didi", "di", "sir", "madam", "maam", "ma'am", "sahab", "saab", "uncle", "aunty",
    # Hinglish pronouns, particles and postpositions
    "mera", "meri", "mere", "tera", "teri", "tere", "uska", "uski", "uske", "hamara", "apna", "apni",
    "ne", "ko", "ka", "ki", "ke", "se", "me", "mein", "pe", "par", "aur", "ya", "yaar", "bhi", "toh", "to",
    "hai", "hain", "tha", "thi", "the", "ho", "hoga", "nahi", "nahin", "haan", "kya", "kyu", "kyun", "wala", "wali",
    # Hinglish verbs (stems and common inflections)
    "kar", "karo", "karna", "karu", "karun", "karke", "kiya", "kiye", "karta", "karti",
    "de", "do", "dena", "dijiye", "dedo", "le", "lo", "lena", "liya", "liye",
    "bhej", "bhejo", "bhejna", "gaya", "gayi", "gaye", "raha", "rahi", "rahe", "chahiye", "bata", "batao",
    # English fillers that the model sometimes attaches to a name
    "ok", "okay", "done", "pls", "plz", "please", "thanks", "thx", "hi", "hello", "dear", "bro",
}
# Words that are a name ("Diya") but also the second half of a Hinglish verb
# ("kar diya" = "did it"). They are dropped only right after a verb stem.
AUX_WORDS = {"diya", "diye", "di", "gaya", "gayi", "liya", "liye", "lo", "do"}
VERB_STEMS = {"kar", "de", "ho", "le", "bhej", "chala", "chal", "aa", "ja", "rakh", "likh", "bata", "dekh",
              "nikal", "bol", "kho", "so", "mil", "ban", "lag", "bhool", "sun", "pad", "ruk", "gir", "bech"}


def _snap(span: dict, text: str) -> dict:
    """Stretch a PERSON / EMAIL span to the edges of the word(s) it touches."""
    label = span["label"]
    if label == "PERSON":
        ok = _is_name_char
    elif label == "EMAIL":
        ok = _is_email_char
    else:
        return span
    start, end = span["start"], span["end"]
    # First drop leading / trailing characters that cannot be part of the value
    # (". D'Costa" -> "D'Costa").
    while start < end and not ok(text[start]):
        start += 1
    while end > start and not ok(text[end - 1]):
        end -= 1
    if start == end:
        return {**span, "start": start, "end": end}
    while start > 0 and ok(text[start - 1]):
        start -= 1
    while end < len(text) and ok(text[end]):
        end += 1
    if label == "PERSON":  # an apostrophe belongs to a name only INSIDE it (D'Costa), not as a quote mark
        while start < end and text[start] in "'’":
            start += 1
        while end > start and text[end - 1] in "'’":
            end -= 1
    if label == "EMAIL":  # keep the longest valid address ("someone@example.com-style" -> "someone@example.com")
        m = EMAIL_RE.match(text, start, end)
        if m:
            end = m.end()
        else:
            while end > start and text[end - 1] in ".-":
                end -= 1
    return {**span, "start": start, "end": end}


_NUMBER_CHECKS = {"PHONE": is_valid_phone, "AADHAAR": is_valid_aadhaar}


def _join_split_numbers(spans: list[dict], text: str) -> list[dict]:
    """Join PHONE / AADHAAR fragments separated only by a short separator ("98765 / 43210")
    when the joined value is valid but a fragment alone is not."""
    out: list[dict] = []
    for s in sorted(spans, key=lambda x: x["start"]):
        prev = out[-1] if out else None
        if (prev and prev["label"] == s["label"] in _NUMBER_CHECKS
                and re.fullmatch(r"[\s\-/.()]{1,3}", text[prev["end"]:s["start"]])):
            check = _NUMBER_CHECKS[s["label"]]
            joined = text[prev["start"]:s["end"]]
            if check(joined) and not (check(text[prev["start"]:prev["end"]]) and check(text[s["start"]:s["end"]])):
                out[-1] = {**prev, "end": s["end"]}
                continue
        out.append(s)
    return out


def _trim_person(span: dict, text: str) -> dict | None:
    """Remove titles, honorifics and Hinglish function words from the edges of a PERSON span.

    Returns None when nothing name-like is left ("kar diya" -> None).
    """
    words = [(m.start() + span["start"], m.end() + span["start"])
             for m in re.finditer(r"\S+", text[span["start"]:span["end"]])]

    def bare(w):
        return text[w[0]:w[1]].strip(".,;:!?()'\"’").lower()

    def previous_word(pos):
        m = re.search(r"(\S+)\s*$", text[:pos])
        return m.group(1).strip(".,;:!?()").lower() if m else ""

    def droppable(w, prev):
        raw = text[w[0]:w[1]]
        b = bare(w)
        if b in TITLES:
            return True
        if not raw[:1].islower():  # capitalised: treat as a real name word
            return False
        if b in NON_NAME_WORDS and b not in AUX_WORDS:
            return True
        return b in AUX_WORDS and prev in VERB_STEMS

    while words and droppable(words[0], previous_word(words[0][0])):
        words.pop(0)
    while words and droppable(words[-1], bare(words[-2]) if len(words) > 1 else previous_word(words[-1][0])):
        words.pop()
    if not words:
        return None
    start, end = words[0][0], words[-1][1]
    end -= len(text[start:end]) - len(text[start:end].rstrip(".,;:!?"))
    if text[start:end].lower().endswith(("'s", "’s")) and end - start > 2:  # possessive: "Rohan's" -> "Rohan"
        end -= 2
    return {**span, "start": start, "end": end}


def _snap_code(span: dict, text: str) -> dict:
    """A PAN / IFSC / GSTIN piece inside a longer code ("IDIB" of "IDIB0139456"): take the
    whole alphanumeric word when that word is a valid code of the same kind."""
    if span["label"] not in FORMATS:
        return span
    a, b = span["start"], span["end"]
    while a > 0 and text[a - 1].isalnum():
        a -= 1
    while b < len(text) and text[b].isalnum():
        b += 1
    if (a, b) != (span["start"], span["end"]) and FORMATS[span["label"]].fullmatch(text[a:b].upper()):
        return {**span, "start": a, "end": b}
    return span


def _join_person(spans: list[dict], text: str) -> list[dict]:
    """Two PERSON spans separated by exactly one space are one name ("om" + "prakash chaurasia")."""
    out: list[dict] = []
    for s in spans:
        prev = out[-1] if out else None
        if prev and prev["label"] == s["label"] == "PERSON" and text[prev["end"]:s["start"]] == " ":
            out[-1] = {**prev, "end": s["end"], "text": text[prev["start"]:s["end"]]}
        else:
            out.append(s)
    return out


def postprocess(spans: list[dict], offsets, probs, text: str, level: int = 3) -> list[dict]:
    """Make each predicted value consistent.

    level 1: MERGE spans that touch or overlap into one span;
             label = the label covering the most characters.
    level 2: + VOTE: label = highest summed probability (B + I) over the span's tokens.
    level 3: + FORMAT: if a PAN/IFSC/GSTIN value fits exactly one official format,
             that format decides the label.
    level 4: + WORDS: before merging, snap PERSON / EMAIL spans to whole words;
             after labelling, trim titles / honorifics / Hinglish words from PERSON.
    level 5: + CODES and NAMES: snap PAN / IFSC / GSTIN pieces to the whole code;
             join PERSON pieces separated by one space.
    """
    if level <= 0 or not spans:
        return spans
    if level >= 4:
        spans = [_snap(s, text) for s in spans]
        spans = [s for s in spans if s["end"] > s["start"]]
        spans = _join_split_numbers(spans, text)
    if level >= 5:
        spans = [_snap_code(s, text) for s in spans]
    merged: list[list[dict]] = []
    for s in sorted(spans, key=lambda x: (x["start"], x["end"])):
        if merged and max(x["end"] for x in merged[-1]) >= s["start"]:
            merged[-1].append(s)
        else:
            merged.append([s])

    out = []
    for group in merged:
        start, end = group[0]["start"], max(s["end"] for s in group)
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
        span = {"start": start, "end": end, "label": label}
        if level >= 4 and label == "PERSON":
            span = _trim_person(span, text)
            if span is None:
                continue
        span["text"] = text[span["start"]:span["end"]]
        out.append(span)
    if level >= 5:
        out = _join_person(out, text)
    return out


def pick_device() -> torch.device:
    if torch.backends.mps.is_available():
        return torch.device("mps")  # Apple-silicon GPU
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def passes_checksum(span: dict) -> bool:
    """Does the value pass the official rule of its label? (PERSON has no rule: always True.)

    Spaces and hyphens inside a code are formatting, so they are removed first
    ("BNZPM 2501 F" is a valid PAN).
    """
    value = span["text"].strip()
    label = span["label"]
    compact = re.sub(r"[\s\-]", "", value).upper()
    if label == "AADHAAR":
        return re.fullmatch(r"[\d\s\-]+", value) is not None and is_valid_aadhaar(value)
    if label == "GSTIN":
        return is_valid_gstin(compact)
    if label == "PAN":
        return FORMATS["PAN"].fullmatch(compact) is not None
    if label == "IFSC":
        return FORMATS["IFSC"].fullmatch(compact) is not None
    if label == "PHONE":
        return is_valid_phone(value)
    if label == "EMAIL":  # a web address such as "support.example.org" is not an e-mail
        return EMAIL_RE.fullmatch(value) is not None
    if label == "BANK_ACCOUNT":  # digits only (single spaces / hyphens between groups), 9-18 of them
        return re.fullmatch(r"\d+(?:[ \-]\d+)*", value) is not None and 9 <= len(re.sub(r"\D", "", value)) <= 18
    return True  # PERSON: no rule


# --- NORMALISE step (cures M4, M5, 6.7, 6.8, 6.14) ---------------------------------
# Undo common ways of hiding PII BEFORE the model reads the text. Every change is
# recorded in an index map (clean position -> original position), so spans are
# reported at their place in the ORIGINAL text.
_TLDS = r"(?:com|in|org|net|co|io|edu|gov|info|biz|me|ai|us|uk)"
_DOT = r"(?:\s*(?:\bdot\b|\[dot\]|\(dot\)|\[\.\]|\(\.\))\s*|\.)"
_AT = r"(?:\s*(?:\bat\b|\[at\]|\(at\)|\{at\})\s*|@)"
# A written-out e-mail. It must END in a real top-level domain: that guard is what
# keeps "Mail him at arindam ..." or "meet at 5 dot 30" from being rewritten.
OBF_EMAIL_RE = re.compile(rf"\b[A-Za-z0-9_%+\-]+(?:{_DOT}[A-Za-z0-9_%+\-]+)*{_AT}"
                          rf"[A-Za-z0-9\-]+(?:{_DOT}[A-Za-z0-9\-]+)*?{_DOT}{_TLDS}\b", re.I)
SPACED_DIGITS_RE = re.compile(r"(?<!\d)\d(?:[ \-]\d){6,}(?!\d)")          # "9 8 1 0 5 5 0 1 4 2"
_DIGIT_WORDS = {w: str(i) for i, w in enumerate("zero one two three four five six seven eight nine".split())}
_DW = "|".join(_DIGIT_WORDS)
DIGIT_WORDS_RE = re.compile(rf"\b(?:{_DW})(?:[\s,\-]+(?:{_DW})){{6,}}\b", re.I)  # "nine eight seven ..."
# Words that are never the mailbox part of a written-out address ("I am at home dot com").
_NOT_A_MAILBOX = {"i", "am", "me", "him", "her", "us", "them", "you", "we", "it", "is", "are", "was", "be", "here",
                  "there", "meet", "see", "look", "call", "stay", "home", "work", "office", "back", "reach", "arrive",
                  "be", "sit", "wait", "available", "online", "live", "staying", "working"}
_INVISIBLE = {"​", "⁠", "﻿", "­"}  # zero-width space, word joiner, BOM, soft hyphen


def normalise_text(text: str) -> tuple[str, list[int]]:
    """Return (clean_text, index_map) where index_map[i] = position of clean_text[i] in `text`."""
    # 1. any Unicode digit (full-width, Devanagari, ...) -> ASCII digit; one character for one
    chars = [str(unicodedata.digit(ch)) if ch.isdigit() and not ch.isascii() else ch for ch in text]
    # 2. drop invisible characters
    idx = [i for i, ch in enumerate(chars) if ch not in _INVISIBLE]
    t = "".join(chars[i] for i in idx)
    # 3. rewrite hidden numbers and e-mails
    edits = []  # (start, end, replacement, original position of every replacement character)
    for m in SPACED_DIGITS_RE.finditer(t):
        pos = [m.start() + k for k, ch in enumerate(m.group()) if ch.isdigit()]
        edits.append((m.start(), m.end(), "".join(t[k] for k in pos), pos))
    for m in DIGIT_WORDS_RE.finditer(t):
        words = list(re.finditer(rf"{_DW}", m.group(), re.I))
        edits.append((m.start(), m.end(), "".join(_DIGIT_WORDS[w.group().lower()] for w in words),
                      [m.start() + w.start() for w in words[:-1]] + [m.start() + words[-1].end() - 1]))
    for m in OBF_EMAIL_RE.finditer(t):
        rep = re.sub(r"\s*(?:\bdot\b|\[dot\]|\(dot\)|\[\.\]|\(\.\))\s*", ".", m.group(), flags=re.I)
        rep = re.sub(r"\s*(?:\bat\b|\[at\]|\(at\)|\{at\})\s*", "@", rep, flags=re.I)
        rep = re.sub(r"\s*([.@])\s*", r"\1", rep)
        local = rep.split("@")[0].lower()
        if rep != m.group() and rep.count("@") == 1 and local not in _NOT_A_MAILBOX:
            n, a, b = len(rep), m.start(), m.end()
            edits.append((a, b, rep, [a + (k * (b - a)) // n for k in range(n - 1)] + [b - 1]))
    if not edits:
        return t, idx
    out, out_idx, pos = [], [], 0
    for a, b, rep, rep_pos in sorted(edits):
        if a < pos:  # overlapping edit: keep the first
            continue
        out.append(t[pos:a])
        out_idx += range(pos, a)
        out.append(rep)
        out_idx += rep_pos
        pos = b
    out.append(t[pos:])
    out_idx += range(pos, len(t))
    return "".join(out), [idx[j] for j in out_idx]


def _map_back(spans: list[dict], index_map: list[int], original: str) -> list[dict]:
    out = []
    for s in spans:
        a, b = index_map[s["start"]], index_map[s["end"] - 1] + 1
        out.append({**s, "start": a, "end": b, "text": original[a:b]})
    return out


# --- REPAIR step (cures M1, M2, M3, 5.1, 5.2, 5.4, 5.6, 6.2, 6.6, 6.11, 6.12) ------
# Words that say what the next value is. Searched in the ~40 characters before a value.
CUE_WORDS = {
    "AADHAAR": r"\b(?:aadhaa?r|aadhar|adhaar|aadhaar\s*card|uid|uidai)\b",
    "PAN": r"\bpan\b",
    "GSTIN": r"\bgst(?:in|n)?\b",
    "IFSC": r"(?:\bifsc\b|\bbranch\b|\bbank\b|\ba/c\b|\baccount\b)",  # an IFSC sits next to the account
    "PHONE": r"\b(?:phone|mobile|mob|cell|whatsapp|call|contact|ph|tel)\b",
    "BANK_ACCOUNT": r"(?:\ba/c\b|\bac\b|\bacc\b|\baccount\b|\bacct\b|\bkhat[ae]\b|\bkhaate\b)",
}
# Words that say the next number is NOT personal (courier, order, transaction ids...).
NEGATIVE_CUES = re.compile(r"\b(?:tracking|track|awb|docket|courier|consignment|shipment|parcel|order|booking|"
                           r"ticket|invoice|inv|txn|utr|ref|reference|transaction|otp|pnr|serial|sr|batch)\b", re.I)
# A number glued to a transaction prefix ("UTR883236914935", "TXN418217092829").
GLUED_PREFIX_RE = re.compile(r"(?:TXN|UTR|REF|ORD|INV|AWB|RRN|TX)[#:\-]?$", re.I)
MASKED_RE = re.compile(r"[Xx*•]{3,}")
NUMERIC_LABELS = {"AADHAAR", "PHONE", "BANK_ACCOUNT"}
# The SHAPE of a value without its check digit: a cue word + the right shape is kept
# even when the check digit is wrong (a typo in an Aadhaar is still an Aadhaar).
SHAPES = {"AADHAAR": re.compile(r"\d{12}"), "PAN": re.compile(r"[A-Z]{5}\d{4}[A-Z]"),
          "GSTIN": re.compile(r"\d{2}[A-Z]{5}\d{4}[A-Z][0-9A-Z]{3}")}
# Order used to re-type a value: most specific format first, the generic "9-18 digits" last.
REPAIR_ORDER = ["GSTIN", "PAN", "IFSC", "EMAIL", "AADHAAR", "PHONE", "BANK_ACCOUNT"]
# Where to look for each label's values in free text (used to split glued spans and
# by the rule fallback). Lookarounds stop a match inside a longer word or number.
CANDIDATES = {
    "GSTIN": re.compile(r"(?<![A-Za-z0-9])\d{2}[A-Z]{5}\d{4}[A-Z][1-9A-Z]Z[0-9A-Z](?![A-Za-z0-9])"),
    "PAN": re.compile(r"(?<![A-Za-z0-9])[A-Z]{5}[ \-]?\d{4}[ \-]?[A-Z](?![A-Za-z0-9])"),
    "IFSC": re.compile(r"(?<![A-Za-z0-9])[A-Z]{4}0[A-Z0-9]{6}(?![A-Za-z0-9])"),
    "EMAIL": re.compile(r"(?<![\w.%+\-])" + EMAIL_RE.pattern + r"(?![\w\-])"),
    "AADHAAR": re.compile(r"(?<![\w])[2-9]\d{3}([ \-]?)\d{4}\1\d{4}(?![\w])"),
    "PHONE": re.compile(r"(?<![\w+])(?:(?:\+91|91|0)[ \-]?)?[6-9]\d{4}[ \-]?\d{5}(?![\w])"),
    "BANK_ACCOUNT": re.compile(r"(?<![\w])\d{9,18}(?![\w])"),
}


def _window_before(text: str, start: int, floor: int = 0, size: int = 40) -> str:
    """The text just before `start`, never crossing a line break or `floor`."""
    a = max(floor, start - size, text.rfind("\n", 0, start) + 1)
    return text[a:start]


def _has_cue(text: str, start: int, label: str, floor: int = 0) -> bool:
    return label in CUE_WORDS and re.search(CUE_WORDS[label], _window_before(text, start, floor), re.I) is not None


def _negative_cue(text: str, start: int) -> bool:
    return NEGATIVE_CUES.search(_window_before(text, start, size=30)) is not None


def _glued_to_prefix(text: str, start: int) -> bool:
    return start > 0 and text[start - 1].isalnum() and GLUED_PREFIX_RE.search(text[max(0, start - 6):start]) is not None


def _complete_code(span: dict, text: str) -> dict | None:
    """PAN / IFSC / GSTIN cut short by the model: grow it by up to 3 characters on
    either side if that makes a valid code ("ABCPK 1234" + " F" -> "ABCPK 1234 F")."""
    for grow in range(1, 7):
        for left in range(0, min(grow, 3) + 1):
            right = grow - left
            if right > 3:
                continue
            a, b = span["start"] - left, span["end"] + right
            if a < 0 or b > len(text) or text[a].isspace() or text[b - 1].isspace():
                continue
            if (a > 0 and text[a - 1].isalnum()) or (b < len(text) and text[b].isalnum()):
                continue
            cand = {**span, "start": a, "end": b, "text": text[a:b]}
            if passes_checksum(cand):
                return cand
    return None


def _split_by_format(span: dict, text: str) -> list[dict]:
    """Several values glued into one span ("9876543210 9876543210"): keep each valid piece."""
    pieces: list[dict] = []
    for label in REPAIR_ORDER:
        for m in CANDIDATES[label].finditer(text, span["start"], span["end"]):
            if any(m.start() < p["end"] and p["start"] < m.end() for p in pieces):
                continue
            piece = {"start": m.start(), "end": m.end(), "label": label, "text": m.group()}
            if passes_checksum(piece):
                pieces.append({**piece, "note": f"split from a longer {span['label']} span"})
    return sorted(pieces, key=lambda p: p["start"])


def _repair_one(span: dict, text: str) -> list[dict]:
    label, start = span["label"], span["start"]
    value = text[start:span["end"]]
    if label == "PERSON":
        return [span]
    if MASKED_RE.search(value):  # decision: a masked ID (XXXX XXXX 1904) is safe by design
        return []
    if label in NUMERIC_LABELS and _glued_to_prefix(text, start):  # UTR883236914935
        return []
    if passes_checksum(span):
        return [span]
    if label in NUMERIC_LABELS and _negative_cue(text, start):  # "tracking no. 463884985568"
        return []
    if label in FORMATS:
        done = _complete_code(span, text)
        if done:
            return [done]
    compact = re.sub(r"[\s\-]", "", value).upper()
    if label in SHAPES and SHAPES[label].fullmatch(compact) and _has_cue(text, start, label):
        return [{**span, "note": "invalid check digit, kept because of the cue word"}]
    for alt in REPAIR_ORDER:
        if alt != label and passes_checksum({"label": alt, "text": value}):
            return [{**span, "label": alt, "note": f"re-typed from {label} by format"}]
    return _split_by_format(span, text)


def _rule_fallback(spans: list[dict], text: str) -> list[dict]:
    """Add values the model missed: exact format + checksum + the label's cue word right before."""
    added = []
    for label in ["AADHAAR", "PAN", "GSTIN", "IFSC", "PHONE", "BANK_ACCOUNT"]:
        for m in CANDIDATES[label].finditer(text):
            a, b = m.span()
            taken = spans + added
            if any(a < s["end"] and s["start"] < b for s in taken):
                continue
            cand = {"start": a, "end": b, "label": label, "text": m.group()}
            if not passes_checksum(cand) or MASKED_RE.search(m.group()):
                continue
            # For numbers the cue must be the nearest thing before the value (two numbers in a row
            # must not share one cue). An IFSC is a distinct code that usually follows the account.
            floor = 0 if label == "IFSC" else max([s["end"] for s in taken if s["end"] <= a], default=0)
            if not _has_cue(text, a, label, floor):
                continue
            if label in NUMERIC_LABELS and _negative_cue(text, a):
                continue
            added.append({**cand, "note": "found by rule: cue word + exact format"})
    return added


def repair_spans(spans: list[dict], text: str, fallback: bool = True) -> list[dict]:
    """Validate-or-repair every span, then add rule-found values. See the module docstring."""
    out: list[dict] = []
    for s in sorted(spans, key=lambda x: x["start"]):
        for r in _repair_one(s, text):
            if not any(r["start"] < o["end"] and o["start"] < r["end"] for o in out):
                out.append({**r, "text": text[r["start"]:r["end"]]})
    if fallback:
        out += _rule_fallback(out, text)
    return sorted(out, key=lambda x: x["start"])


# The shipped configuration (used by the demo and reported as "final" in evaluation).
FINAL = {"postprocess_level": 5, "normalise": True, "repair": True}


class PIIModel:
    def __init__(self, model, tokenizer, device, max_length: int = 128, stride: int = 32):
        # max_length = the length the model was fine-tuned on (train.py --max-length).
        # stride = tokens shared by neighbouring windows; must exceed the longest PII value.
        self.model, self.tokenizer, self.device = model, tokenizer, device
        self.max_length, self.stride = max_length, stride
        self.model.to(device).eval()

    @classmethod
    def load(cls, path: str | Path, device: torch.device | None = None) -> "PIIModel":
        tokenizer = AutoTokenizer.from_pretrained(path)
        model = AutoModelForTokenClassification.from_pretrained(path)
        return cls(model, tokenizer, device or pick_device())

    @torch.no_grad()
    def _token_predictions(self, texts: list[str], batch_size: int) -> list[tuple[list, list]]:
        """Per text: (offsets, probabilities) for every token of the WHOLE text.

        Texts longer than one window are split into overlapping windows. Where
        windows overlap, a token keeps the prediction from the window in which
        it is furthest from an edge.
        """
        enc = self.tokenizer(texts, truncation=True, max_length=self.max_length, stride=self.stride,
                             return_overflowing_tokens=True, return_offsets_mapping=True, padding=True,
                             return_tensors="pt")
        window_text = enc.pop("overflow_to_sample_mapping").tolist()
        window_offsets = enc.pop("offset_mapping").tolist()
        n_windows = len(window_text)

        best: list[dict] = [{} for _ in texts]  # per text: (start, end) -> (centrality, probs)
        for w0 in range(0, n_windows, batch_size):
            batch = {k: v[w0:w0 + batch_size].to(self.device) for k, v in enc.items()}
            probs = self.model(**batch).logits.softmax(-1).cpu().tolist()
            for k, window_probs in enumerate(probs):
                w = w0 + k
                real = [j for j, (a, b) in enumerate(window_offsets[w]) if a != b]
                if not real:
                    continue
                first, last = real[0], real[-1]
                for j in real:
                    key = tuple(window_offsets[w][j])
                    centrality = min(j - first, last - j)
                    seen = best[window_text[w]].get(key)
                    if seen is None or centrality > seen[0]:
                        best[window_text[w]][key] = (centrality, window_probs[j])

        result = []
        for table in best:
            keys = sorted(table)
            result.append((keys, [table[k][1] for k in keys]))
        return result

    def predict_batch(self, texts: list[str], batch_size: int = 64, checksum_filter: bool = False,
                      postprocess_level: int = 0, normalise: bool = False, repair: bool = False,
                      fallback: bool = True) -> list[list[dict]]:
        """checksum_filter: drop values that fail their rule (old VETO behaviour).
        repair: validate-or-repair instead of veto, plus the rule fallback (unless fallback=False).
        normalise: undo hidden numbers / e-mails first; spans still point at the original text."""
        originals = texts
        maps = None
        if normalise:
            pairs = [normalise_text(t) for t in texts]
            texts, maps = [p[0] for p in pairs], [p[1] for p in pairs]
        results = []
        for i, (text, (offsets, probs)) in enumerate(zip(texts, self._token_predictions(texts, batch_size))):
            tags = [max(range(len(p)), key=p.__getitem__) for p in probs]
            spans = decode(tags, offsets, text)
            if postprocess_level:
                spans = postprocess(spans, offsets, probs, text, postprocess_level)
            if repair:
                spans = repair_spans(spans, text, fallback=fallback)
            elif checksum_filter:
                spans = [s for s in spans if passes_checksum(s)]
            if maps is not None:
                spans = _map_back(spans, maps[i], originals[i])
            results.append(spans)
        return results

    def predict(self, text: str, **options) -> list[dict]:
        return self.predict_batch([text], **options)[0]

    def detect_batch(self, texts: list[str], batch_size: int = 64) -> list[list[dict]]:
        """The final system: model + post-processing level 5 + normalise + repair."""
        return self.predict_batch(texts, batch_size, **FINAL)

    def detect(self, text: str) -> list[dict]:
        return self.detect_batch([text])[0]
