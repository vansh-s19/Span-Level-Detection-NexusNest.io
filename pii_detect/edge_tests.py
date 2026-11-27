"""
Edge-case regression suite (docs/edge_cases.md, item 7.2).

One row per edge case in the document: the input and the EXACT values the final
system must report. Rows marked `known=` are open problems that need retraining;
they are reported but do not fail the run.

    .venv/bin/python -m pii_detect.edge_tests
    .venv/bin/python -m pii_detect.edge_tests --model path/to/model

Exit code 1 if any row that is not `known` fails.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")

from .model import PIIModel  # noqa: E402

RETRAIN = "needs retraining"

# (doc section, input, expected {(label, value)}, known-open reason or None)
CASES = [
    # --- issues 1-4 -------------------------------------------------------------------
    ("2", "Arindam George 6141697365", {("PERSON", "Arindam George"), ("PHONE", "6141697365")}, RETRAIN),
    ("2", "Contact Arindam at 9876543210", {("PERSON", "Arindam"), ("PHONE", "9876543210")}, None),
    ("3", "courier tracking no. 463884985568", set(), None),
    ("3", "Order 956378276082 shipped, meet me at the office at 5 dot 30", set(), None),
    ("4", "yaar Golu ne order 956378276082 cancel kar diya", {("PERSON", "Golu")}, None),
    ("4", "maine payment kar diya hai", set(), None),
    # --- review prompt M1-M6 ------------------------------------------------------------
    ("M1", "my aadhaar is 2798 1933 1905", {("AADHAAR", "2798 1933 1905")}, None),
    ("M1", "firm's GSTIN 27BNZPM2501F1ZA was rejected", {("GSTIN", "27BNZPM2501F1ZA")}, None),
    ("M1", "my pan is ABCXK1234F", {("PAN", "ABCXK1234F")}, None),
    ("M2", "PAN BNZPM 2501 F", {("PAN", "BNZPM 2501 F")}, None),
    ("M2", "PAN: ABCPK 1234 F", {("PAN", "ABCPK 1234 F")}, None),
    ("M3", "refund mere khate 50200031874562 me daal de", {("BANK_ACCOUNT", "50200031874562")}, None),
    ("M3", "Rahul Sharma,9876543210,ABCPK1234F,rahul@gmail.com",
     {("PERSON", "Rahul Sharma"), ("PHONE", "9876543210"), ("PAN", "ABCPK1234F"), ("EMAIL", "rahul@gmail.com")}, None),
    ("M3", "INSERT INTO users VALUES ('Priya Nair','priya@x.com','9876543210');",
     {("PERSON", "Priya Nair"), ("EMAIL", "priya@x.com"), ("PHONE", "9876543210")}, None),
    ("M3", "9876543210/9123456780", {("PHONE", "9876543210"), ("PHONE", "9123456780")}, None),
    ("M4", "my number is 9 8 7 6 5 4 3 2 1 0", {("PHONE", "9 8 7 6 5 4 3 2 1 0")}, None),
    ("M5", "mail me at rahul dot sharma at gmail dot com", {("EMAIL", "rahul dot sharma at gmail dot com")}, None),
    ("M5", "meet me at the office at 5 dot 30", set(), None),
    ("M6", "His accountant om prakash chaurasia wrote", {("PERSON", "om prakash chaurasia")}, None),
    ("M7", "yaar golu ko bol dena refund mere khate 50200031874562 me daal de, IFSC HDFC0009912, aur Sunaina "
           "didi ko 9 8 1 0 5 5 0 1 4 2 pe call kar lena",
     {("PERSON", "golu"), ("BANK_ACCOUNT", "50200031874562"), ("IFSC", "HDFC0009912"), ("PERSON", "Sunaina"),
      ("PHONE", "9 8 1 0 5 5 0 1 4 2")}, RETRAIN),
    # --- section 5 ----------------------------------------------------------------------
    ("5.2", "aadhaar XXXX XXXX 1904", set(), None),  # decision: masked Aadhaar is safe by design
    ("5.2", "GSTIN 29ABCDE1234F1Z5", {("GSTIN", "29ABCDE1234F1Z5")}, None),
    ("5.4", "RAHUL.SHARMA@GMAIL.COM", {("EMAIL", "RAHUL.SHARMA@GMAIL.COM")}, None),
    ("5.5", "call 98765 / 43210", {("PHONE", "98765 / 43210")}, None),
    ("5.5", "IFSC IDIB0139456", {("IFSC", "IDIB0139456")}, None),
    ("5.6", "9876543210 9876543210 9876543210",
     {("PHONE", "9876543210")}, None),  # three identical values: compared as a set
    # --- section 6 ----------------------------------------------------------------------
    ("6.3", "Tushar 6028982601", {("PERSON", "Tushar"), ("PHONE", "6028982601")}, RETRAIN),
    ("6.4", "Mrs. D'Costa called", {("PERSON", "D'Costa")}, None),
    ("6.4", "ok Aman bhai done", {("PERSON", "Aman")}, None),
    ("6.4", "kal Mishra ji ko 50k transfer karna hai", {("PERSON", "Mishra")}, RETRAIN),
    ("6.6", "payment UTR883236914935 - Rs 5000 - Acc No 4047466106726827",
     {("BANK_ACCOUNT", "4047466106726827")}, None),
    ("6.7", "call nine eight seven six five four three two one zero", {("PHONE", "nine eight seven six five four three two one zero")}, None),
    ("6.7", "rahul.sharma[at]gmail[.]com", {("EMAIL", "rahul.sharma[at]gmail[.]com")}, None),
    ("6.8", "phone ９８７６５４３２１０", {("PHONE", "９８７６５４３２１０")}, None),
    ("6.8", "mobile ९८७६५४३२१०", {("PHONE", "९८७६५४३२१०")}, None),
    ("6.8", "मेरा नाम राहुल शर्मा है", {("PERSON", "राहुल शर्मा")}, "needs a multilingual base model"),
    ("6.9", "see https://rahul-sharma.github.io/notes and logger.info(user.email_regex)", set(), None),
    ("6.12", "Write a polite email to Prakash Dutta asking them to update UID 7343-0438-3741 on the HR portal.",
     {("PERSON", "Prakash Dutta"), ("AADHAAR", "7343-0438-3741")}, None),
    ("6.12", "Can you explain PAN structure using this example: AAACR5055K?", {("PAN", "AAACR5055K")}, None),
    ("6.14", "aadhaar 2798​1933​1904", {("AADHAAR", "2798​1933​1904")}, None),
    # --- false-alarm guards ---------------------------------------------------------------
    ("FA", "I am at home, call me at 9810550142", {("PHONE", "9810550142")}, None),
    ("FA", "I am at home dot com right now", set(), None),
    ("FA", "booking 482910375612 cancel ho gayi kya?", set(), None),
    ("FA", "payment TXN418217092829 failed", set(), None),
]

DEFAULT_MODEL = Path(__file__).resolve().parent.parent / "models" / "distilbert-pii"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    args = ap.parse_args()
    model = PIIModel.load(args.model)
    preds = model.detect_batch([c[1] for c in CASES])
    failed = known = 0
    for (sec, text, want, why), got_spans in zip(CASES, preds):
        got = {(s["label"], s["text"]) for s in got_spans}
        ok = got == want
        if ok:
            mark = "PASS"
        elif why:
            mark, known = "KNOWN", known + 1
        else:
            mark, failed = "FAIL", failed + 1
        print(f"{mark:5} {sec:5} {text[:70]!r}")
        if not ok:
            print(f"      want {sorted(want)}\n      got  {sorted(got)}" + (f"\n      ({why})" if why else ""))
    passed = len(CASES) - failed - known
    print(f"\n{passed} passed, {known} known open (need retraining), {failed} failed, of {len(CASES)}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
