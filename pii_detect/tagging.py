"""
Convert between character spans and token-level BIO labels.

The model never sees character offsets. It sees TOKENS (sub-word pieces
produced by the DistilBERT tokenizer) and predicts one tag per token:

    text    : "Aadhaar 2798 1933 1904 and order 2061 ..."
    tokens  : Aad ##ha ##ar  279 ##8  1933  1904  and  order  206 ##1 ...
    tags    :  O   O    O   B-AADHAAR I-AADHAAR I-.. I-..   O    O     O   O

ENCODING (training): the fast tokenizer returns `offset_mapping`, the
character range each token covers. A token inside a gold span gets
B-<label> if it is the span's first token, otherwise I-<label>.

Every sub-word piece of a span is labelled (not just the first piece of
each word). Spans here often do not follow whitespace words
("+91-9876543210", values inside JSON quotes), so labelling by character
position is simpler and exact.

DECODING (prediction): consecutive B/I tokens of the same label are merged
into one span, and the token offsets give back exact character positions.
"""

from __future__ import annotations

from .data import LABELS

TAGS = ["O"] + [f"{p}-{label}" for label in LABELS for p in ("B", "I")]
TAG2ID = {t: i for i, t in enumerate(TAGS)}
ID2TAG = {i: t for t, i in TAG2ID.items()}
IGNORE = -100  # PyTorch's cross-entropy skips this label (used for [CLS], [SEP], padding)


def encode(example: dict, tokenizer, max_length: int = 128) -> tuple[dict, int]:
    """Tokenise one example and build its label ids.

    Returns (features, n_misaligned). A span is "misaligned" when no token
    starts exactly at its first character, meaning the tokenizer merged the
    value with neighbouring text. We count these so we know the encoding is
    faithful (it should be ~0).
    """
    enc = tokenizer(example["text"], truncation=True, max_length=max_length, return_offsets_mapping=True)
    labels = []
    for (start, end) in enc["offset_mapping"]:
        if start == end:  # special token ([CLS]/[SEP])
            labels.append(IGNORE)
            continue
        tag = "O"
        for span in example["spans"]:
            if start < span["end"] and span["start"] < end:  # token overlaps the span
                tag = ("B-" if start <= span["start"] else "I-") + span["label"]
                break
        labels.append(TAG2ID[tag])

    token_starts = {s for s, e in enc["offset_mapping"] if s != e}
    n_misaligned = sum(span["start"] not in token_starts for span in example["spans"])
    enc.pop("offset_mapping")
    enc["labels"] = labels
    return enc, n_misaligned


def decode(tag_ids: list[int], offsets: list[tuple[int, int]], text: str) -> list[dict]:
    """Merge per-token tags into character spans."""
    spans: list[dict] = []
    current = None
    for tag_id, (start, end) in zip(tag_ids, offsets):
        if start == end:  # special token
            continue
        tag = ID2TAG[tag_id]
        if tag == "O":
            current = None
            continue
        prefix, label = tag.split("-", 1)
        # Continue the open span on I-<same label>; otherwise start a new one.
        # (An I- tag with no open span is treated as a start: being lenient
        # here recovers a span instead of dropping it.)
        if current and prefix == "I" and current["label"] == label:
            current["end"] = end
        else:
            current = {"start": start, "end": end, "label": label}
            spans.append(current)
    for s in spans:
        s["text"] = text[s["start"]:s["end"]]
    return spans
