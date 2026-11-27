"""
Extra TRAINING-ONLY examples that target the gaps found in review
(docs/edge_cases.md, issues 1-4). Validation and test sets are not touched,
and no test template or hand-written test sentence is copied.

    .venv/bin/python -m datagen.augment            # -> data/augment/train_extra.jsonl

Gap (issue)                                  What is added
-------------------------------------------  ---------------------------------------------
2  name opens the line with no cue word       "<Name> - <phone>", "<Name> (<phone>)", contact cards, ...
3  12-digit tracking / docket numbers          courier sentences with 12-digit numbers as NEGATIVES,
   predicted as PHONE                          half of them Verhoeff-valid (pass the Aadhaar checksum)
4  Hinglish: nicknames missed, verbs such as   Hinglish sentences with nicknames and first names +
   "kar diya" / "mera" flagged as names        honorifics (ji, bhai, didi), and PII-free Hinglish
1  only single short sentences in training     multi-line documents: 3-5 training sentences joined
                                               as lines / bullets / numbered lists, and key-value forms

The held-out synthetic test template "{PERSON} {PHONE}" (P077) is deliberately
NOT added; the cue-less templates here always have a separator or extra words.
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from .checksums import verhoeff_check_digit
from .generate import NEGATIVE_TEMPLATES, POSITIVE_TEMPLATES, render, split_templates
from .values import FILLERS, FIRST_NAMES, PII_SLOTS, _digits

# Common Indian nicknames. "Golu" is left out on purpose: it is in the hand-written test set.
NICKNAMES = ["Bunty", "Pinky", "Chintu", "Monu", "Sonu", "Babloo", "Guddu", "Tinku", "Pappu", "Raju",
             "Munna", "Bittu", "Chiku", "Dolly", "Rinku", "Pintu", "Gudiya", "Babli", "Lucky", "Sweety",
             "Bablu", "Chotu", "Nikku", "Mintu", "Titu", "Happy", "Montu", "Dimpy", "Pammi", "Rocky"]
COURIERS = ["Blue Dart", "Delhivery", "DTDC", "Ecom Express", "Xpressbees", "India Post", "Shadowfax", "Ekart"]


def _num12_verhoeff(rng: random.Random) -> str:
    """12 digits that PASS the Aadhaar checksum but are not an Aadhaar (and do not start with 91)."""
    while True:
        body = rng.choice("2345678") + _digits(rng, 10)
        n = body + verhoeff_check_digit(body)
        if not n.startswith("91"):
            return n


def _register_slots() -> None:
    """Add the extra slots used below to the generator's slot tables (new keys only)."""
    PII_SLOTS.setdefault("NICK", ("PERSON", lambda rng, p: rng.choice(NICKNAMES)))
    PII_SLOTS.setdefault("FIRST", ("PERSON", lambda rng, p: rng.choice(FIRST_NAMES)))
    FILLERS.setdefault("num12v", lambda rng: _num12_verhoeff(rng) if rng.random() < 0.5 else FILLERS["num12"](rng))
    FILLERS.setdefault("courier", lambda rng: rng.choice(COURIERS))


# --- issue 2: a name that opens the line, with no cue word ----------------------------
CUELESS_NAME = [
    "{PERSON} - {PHONE}",
    "{PERSON}: {PHONE}",
    "{PERSON} | {PHONE}",
    "{PERSON} ({PHONE})",
    "{PERSON} {PHONE} {city}",
    "{PERSON} {PHONE} - call after 6 pm",
    "{PERSON} {PHONE} (office)",
    "{PERSON} – {PHONE} – {city}",
    "{PERSON} {EMAIL}",
    "{PERSON} - {EMAIL}",
    "{PERSON} {PHONE}, {EMAIL}",
    "{PERSON} {AADHAAR}",
    "{PERSON} - {PAN}",
    "{PERSON}\t{PHONE}",
    "{PERSON}\n{PHONE}\n{EMAIL}",
    "{PERSON} {PHONE}\n{PERSON2} {PHONE}",
    "{PERSON}, {city} - {PHONE}",
    "{PERSON} / {PHONE} / {EMAIL}",
]

# --- issue 3: 12-digit courier / tracking numbers are NOT PII --------------------------
TRACKING_NEG = [
    "Tracking no. {num12v} - parcel is out for delivery today.",
    "{courier} AWB {num12v} was booked on {date}.",
    "Your shipment {num12v} via {courier} will arrive on {date}.",
    "courier ref {num12v} is stuck at the {city} hub",
    "track consignment {num12v} on the {courier} website",
    "the docket number is {num12v}, pls follow up with {courier}",
    "Order id {num12}, tracking {num12v}, carrier {courier}.",
    "parcel {num12v} returned to sender, reason: address not found",
    "Shipment id {num12v} picked up from {city} warehouse.",
    "Please share the tracking number - is it {num12v} or {num12v}?",
]
TRACKING_POS = [  # same courier context, with real PII next to the tracking number
    "Tracking no. {num12v} for {PERSON}'s parcel - out for delivery.",
    "{courier} AWB {num12v} booked by {PERSON}, contact {PHONE}.",
    "{PERSON} asked about docket {num12v}; her mobile is {PHONE}.",
    "Shipment {num12v} for {FIRST} will reach {city} by {date}.",
]

# --- issue 4: Hinglish ---------------------------------------------------------------
HINGLISH_POS = [
    "{NICK} ne kal {PHONE} se call kiya tha",
    "{NICK} ko {amount} bhej do aaj",
    "{NICK} ka number {PHONE} hai, save kar lo",
    "mere dost {NICK} ka aadhaar {AADHAAR} hai",
    "abhi {NICK} se baat hui, wo kal aayega",
    "kal {FIRST} aur {NICK} aa rahe hai",
    "{NICK} bhaiya ne parcel le liya",
    "{FIRST} ji ka pan {PAN} hai",
    "{FIRST} ji se baat karke batata hu",
    "{FIRST} bhai ne payment kar diya",
    "{FIRST} didi ko bolo {EMAIL} check kare",
    "{FIRST} sir ka mail {EMAIL} pe aaya tha",
    "{PERSON} ka refund ho gaya kya?",
    "{NICK} ki mummy ka number {PHONE} hai",
    "yaar {NICK} abhi tak nahi aaya",
    "{FIRST} madam ne form sign kar diya",
    "bhai {NICK} ko bol de ki {PHONE} pe whatsapp kare",
    "{PERSON} ji, aapka {pan_cue} {PAN} verify ho gaya hai",
    "Diya {FIRST} ke saath {city} gayi hai",
]
HINGLISH_NEG = [
    "maine payment kar diya hai, ref {txn}",
    "kaam ho gaya bhai, thanks",
    "file bhej di hai, check kar lo",
    "mera refund abhi tak nahi aaya, invoice {invoice}",
    "yaar ye report jaldi bhej do",
    "booking {num12} cancel ho gayi kya?",
    "otp {otp} aaya tha par expire ho gaya",
    "sir mera kaam kab tak hoga?",
    "ok bhai done, kal milte hai",
    "app khul hi nahi raha, kya karu",
    "maine form bhar diya, ab kya karna hai",
    "paise mil gaye, shukriya",
    "pls isko fix kar do yaar",
    "usne sab kuch de diya, ab kuch baaki nahi",
    "maine pehle hi bata diya tha",
    "mera phone kharab ho gaya hai",
    "meri file kahan hai? kal tak chahiye",
    "aap mujhe call kar dijiye",
    "haan theek hai, kar dunga",
    "invoice {invoice} ka payment ho gaya",
]

# --- issue 1: key-value forms (one value per line) -------------------------------------
FORMS = [
    "Full Name: {PERSON}\nMobile: {PHONE}\nEmail: {EMAIL}\nPAN: {PAN}",
    "Name - {PERSON}\nAadhaar - {AADHAAR}\nPhone - {PHONE}\nCity - {city}",
    "• Name: {PERSON}\n• Contact: {PHONE}\n• Email ID: {EMAIL}",
    "Account holder: {PERSON}\nA/c no: {BANK_ACCOUNT}\nIFSC: {IFSC}\nBranch: {city}",
    "Vendor: {company}\nGSTIN: {GSTIN}\nContact person: {PERSON}\nPhone: {PHONE}",
    "Employee: {PERSON} ({empid})\nPAN: {PAN}\nUAN pending\nJoining date: {date}",
]

BULLETS = ["\n", "\n• ", "\n- ", "\n* "]


def _render_all(templates, n, rng, kind, prefix):
    rows = []
    for _ in range(n):
        i = rng.randrange(len(templates))
        text, spans = render(templates[i], rng)
        rows.append({"text": text, "spans": spans, "kind": kind,
                     "template_id": f"{prefix}{i:03d}", "source": "augment"})
    return rows


def _pack_document(pieces: list[dict], rng: random.Random) -> dict:
    """Join several examples into one multi-line document, shifting every span's offsets."""
    style = rng.choice(["lines", "bullets", "numbered"])
    text, spans = "", []
    for k, ex in enumerate(pieces):
        if style == "lines":
            sep = "" if k == 0 else "\n"
        elif style == "bullets":
            sep = rng.choice(BULLETS[1:]) if k else rng.choice(["", "• ", "- "])
        else:
            sep = ("" if k == 0 else "\n") + f"{k + 1}. "
        text += sep
        for s in ex["spans"]:
            spans.append({**s, "start": s["start"] + len(text), "end": s["end"] + len(text)})
        text += ex["text"]
    for s in spans:
        assert text[s["start"]:s["end"]] == s["text"]
    return {"text": text, "spans": spans, "kind": "positive" if spans else "negative",
            "template_id": "DOC", "source": "augment"}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--out", type=Path, default=Path("data/augment/train_extra.jsonl"))
    args = p.parse_args()
    _register_slots()

    # Re-create the generator's template split (same seed and calls as generate.py) so
    # documents are packed ONLY from train-split templates.
    split_rng = random.Random(42)
    pos_split = split_templates(POSITIVE_TEMPLATES, "P", split_rng, min_templates_per_label=2)
    neg_split = split_templates(NEGATIVE_TEMPLATES, "N", split_rng)
    train_templates = [t for _, t in pos_split["train"]] + [t for _, t in neg_split["train"]]

    rng = random.Random(args.seed)
    rows = []
    rows += _render_all(CUELESS_NAME, 900, rng, "positive", "AC")
    rows += _render_all(TRACKING_NEG, 600, rng, "negative", "AT")
    rows += _render_all(TRACKING_POS, 200, rng, "positive", "ATP")
    rows += _render_all(HINGLISH_POS, 900, rng, "positive", "AH")
    rows += _render_all(HINGLISH_NEG, 600, rng, "negative", "AHN")
    rows += _render_all(FORMS, 400, rng, "positive", "AF")

    pool = rows + [{"text": t, "spans": s} for t, s in
                   (render(rng.choice(train_templates), rng) for _ in range(3000))]
    for _ in range(700):
        rows.append(_pack_document(rng.sample(pool, rng.randint(3, 5)), rng))

    rng.shuffle(rows)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for i, r in enumerate(rows, 1):
            f.write(json.dumps({"id": f"aug-{i:06d}", **r}, ensure_ascii=False) + "\n")
    print(f"wrote {len(rows)} examples to {args.out}")


if __name__ == "__main__":
    main()
