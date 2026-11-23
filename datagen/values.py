"""
Value makers: functions that produce one realistic value for a slot.

Two kinds of slot:
  * PII slots (UPPERCASE in templates) -> become labelled spans.
  * Filler slots (lowercase in templates) -> plain text with no label. These
    include "cues" ("Aadhaar no.", "mob"), harmless context (cities, amounts),
    and HARD NEGATIVES: strings that look like PII but are not
    (a 12-digit order number, a PAN-shaped product SKU, a year range).

Every function takes `rng` (a random.Random) so the whole dataset is
reproducible from one seed. All names, numbers and e-mail addresses are
randomly generated; none belong to a real person.
"""

from __future__ import annotations

import random
import string

from .checksums import gstin_check_char, verhoeff_check_digit

# ---------------------------------------------------------------------------
# Name lists (Indian first names and surnames across regions)
# ---------------------------------------------------------------------------
FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Arjun", "Rohan", "Karan", "Rahul", "Amit",
    "Suresh", "Ramesh", "Vikram", "Anil", "Sanjay", "Manoj", "Deepak", "Nikhil",
    "Siddharth", "Harsh", "Kunal", "Pranav", "Varun", "Ishaan", "Yash", "Gaurav",
    "Abhishek", "Mohit", "Tushar", "Naveen", "Prakash", "Rajesh", "Venkatesh",
    "Srinivas", "Karthik", "Arun", "Murugan", "Balaji", "Senthil", "Ganesh",
    "Sourav", "Debashish", "Arindam", "Imran", "Faizan", "Sameer", "Irfan",
    "Gurpreet", "Harpreet", "Jaspreet", "Manpreet", "Joseph", "Thomas", "Bijoy",
    "Priya", "Ananya", "Diya", "Saanvi", "Aanya", "Isha", "Neha", "Pooja",
    "Sneha", "Kavya", "Riya", "Shreya", "Divya", "Anjali", "Meera", "Lakshmi",
    "Sunita", "Rekha", "Anita", "Kiran", "Swati", "Nandini", "Pallavi", "Rashmi",
    "Deepika", "Aishwarya", "Bhavna", "Shalini", "Revathi", "Kavitha", "Lalitha",
    "Madhuri", "Ayesha", "Fatima", "Zoya", "Sana", "Simran", "Navneet", "Mary",
    "Anupama", "Moumita", "Payel", "Trisha", "Vanshika", "Kritika", "Tanvi",
]
SURNAMES = [
    "Sharma", "Verma", "Gupta", "Agarwal", "Singh", "Kumar", "Yadav", "Mishra",
    "Pandey", "Tiwari", "Saxena", "Srivastava", "Chauhan", "Rathore", "Joshi",
    "Mehta", "Shah", "Patel", "Desai", "Modi", "Parikh", "Kulkarni", "Deshpande",
    "Patil", "Jadhav", "Pawar", "Naik", "Rao", "Reddy", "Naidu", "Iyer", "Iyengar",
    "Pillai", "Nair", "Menon", "Krishnan", "Subramanian", "Raman", "Gowda",
    "Hegde", "Shetty", "Banerjee", "Chatterjee", "Mukherjee", "Ghosh", "Bose",
    "Das", "Sen", "Dutta", "Roy", "Khan", "Ahmed", "Ansari", "Qureshi", "Sheikh",
    "Gill", "Sandhu", "Dhillon", "Grewal", "Kaur", "D'Souza", "Fernandes",
    "Thomas", "Mathew", "George", "Bhat", "Kaul", "Thakur", "Rawat", "Negi",
    "Bhatt", "Malhotra", "Kapoor", "Khanna", "Arora", "Bajaj", "Chopra", "Sethi",
]
TITLES = ["Mr.", "Ms.", "Mrs.", "Dr.", "Shri", "Smt."]

EMAIL_DOMAINS = [
    "gmail.com", "yahoo.co.in", "outlook.com", "hotmail.com", "rediffmail.com",
    "yahoo.com", "icloud.com", "protonmail.com", "acmecorp.in", "techsolutions.co.in",
]

# Real bank-code prefixes so IFSC values look authentic (the branch part is random).
IFSC_BANK_CODES = [
    "SBIN", "HDFC", "ICIC", "UTIB", "PUNB", "BARB", "KKBK", "CNRB", "UBIN",
    "IDIB", "BKID", "YESB", "INDB", "IDFB", "FDRL", "MAHB", "CBIN", "IOBA",
]
BANK_NAMES = [
    "SBI", "HDFC Bank", "ICICI Bank", "Axis Bank", "PNB", "Bank of Baroda",
    "Kotak", "Canara Bank", "Union Bank", "IDFC First", "Yes Bank", "Federal Bank",
]

CITIES = [
    "Mumbai", "Delhi", "Bengaluru", "Hyderabad", "Chennai", "Kolkata", "Pune",
    "Ahmedabad", "Jaipur", "Lucknow", "Indore", "Bhopal", "Kochi", "Noida",
    "Gurugram", "Chandigarh", "Nagpur", "Surat", "Coimbatore", "Patna",
]
COMPANIES = [
    "Acme Corp", "Zenith Infotech", "BlueLeaf Pvt Ltd", "Nimbus Solutions",
    "Orbit Retail", "Kaveri Textiles", "Sapphire Logistics", "Vistara Foods",
    "Pinnacle Finserv", "Greenfield Agro",
]
PRODUCTS = [
    "laptop", "office chairs", "printer cartridges", "router", "monitor",
    "steel rods", "cotton fabric", "spare parts", "mobile covers", "LED panels",
]

# PAN 4th character = holder type. P = individual (most common).
PAN_HOLDER_TYPES = "P" * 14 + "CHFATBLJG"


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def _digits(rng: random.Random, n: int) -> str:
    return "".join(rng.choice(string.digits) for _ in range(n))


def _letters(rng: random.Random, n: int) -> str:
    return "".join(rng.choice(string.ascii_uppercase) for _ in range(n))


def _maybe_lower(rng: random.Random, value: str, p: float) -> str:
    return value.lower() if rng.random() < p else value


# ---------------------------------------------------------------------------
# PII value makers (labelled)
# ---------------------------------------------------------------------------
def make_person(rng: random.Random) -> str:
    first, last = rng.choice(FIRST_NAMES), rng.choice(SURNAMES)
    r = rng.random()
    if r < 0.12:
        name = f"{first} {rng.choice(FIRST_NAMES)} {last}"  # middle name
    elif r < 0.20:
        name = first  # first name only ("ask Priya")
    elif r < 0.25:
        name = f"{first[0]}. {last}"  # initial
    else:
        name = f"{first} {last}"
    r = rng.random()
    if r < 0.05:
        name = name.lower()
    elif r < 0.08:
        name = name.upper()
    return name


def make_aadhaar(rng: random.Random) -> str:
    body = rng.choice("23456789") + _digits(rng, 10)
    number = body + verhoeff_check_digit(body)
    r = rng.random()
    if r < 0.50:
        return f"{number[:4]} {number[4:8]} {number[8:]}"
    if r < 0.65:
        return f"{number[:4]}-{number[4:8]}-{number[8:]}"
    return number


def make_pan(rng: random.Random, surname: str | None = None) -> str:
    # Real structure: AAA (series) + holder type + first letter of surname /
    # entity name + 4 digits + check letter.
    fifth = (surname[0].upper() if surname and surname[0].isalpha() else rng.choice(string.ascii_uppercase))
    pan = _letters(rng, 3) + rng.choice(PAN_HOLDER_TYPES) + fifth + f"{rng.randint(1, 9999):04d}" + _letters(rng, 1)
    return _maybe_lower(rng, pan, 0.10)


def make_phone(rng: random.Random) -> str:
    n = rng.choice("6789") + _digits(rng, 9)
    formats = [
        n,
        f"+91 {n[:5]} {n[5:]}",
        f"+91-{n}",
        f"+91{n}",
        f"+91 {n}",
        f"{n[:5]} {n[5:]}",
        f"{n[:5]}-{n[5:]}",
        f"0{n}",
        f"91{n}",
        f"(+91) {n}",
    ]
    weights = [30, 15, 10, 8, 8, 10, 6, 5, 4, 4]
    return rng.choices(formats, weights=weights, k=1)[0]


def make_email(rng: random.Random, person: str | None = None) -> str:
    if person and rng.random() < 0.7:
        parts = [p for p in person.replace(".", " ").split() if p.isalpha()]
        first = parts[0].lower() if parts else rng.choice(FIRST_NAMES).lower()
        last = parts[-1].lower() if len(parts) > 1 else rng.choice(SURNAMES).lower()
    else:
        first, last = rng.choice(FIRST_NAMES).lower(), rng.choice(SURNAMES).lower()
    last = last.replace("'", "")
    style = rng.randint(0, 5)
    local = [
        f"{first}.{last}",
        f"{first}{last}",
        f"{first}_{last}{rng.randint(1, 99)}",
        f"{first}{rng.randint(80, 2005)}",
        f"{first[0]}{last}",
        f"{last}.{first}{rng.randint(1, 9)}",
    ][style]
    return f"{local}@{rng.choice(EMAIL_DOMAINS)}"


def make_bank_account(rng: random.Random) -> str:
    length = rng.choice([9, 10, 11, 11, 12, 12, 13, 14, 14, 15, 16, 16, 18])
    return rng.choice("123456789") + _digits(rng, length - 1)


def make_ifsc(rng: random.Random) -> str:
    branch = _digits(rng, 6) if rng.random() < 0.85 else "".join(
        rng.choice(string.ascii_uppercase + string.digits) for _ in range(6)
    )
    return _maybe_lower(rng, f"{rng.choice(IFSC_BANK_CODES)}0{branch}", 0.08)


def make_gstin(rng: random.Random) -> str:
    state = f"{rng.randint(1, 37):02d}"
    pan = _letters(rng, 3) + rng.choice("CCCFFPHAT") + _letters(rng, 1) + f"{rng.randint(1, 9999):04d}" + _letters(rng, 1)
    first14 = state + pan + rng.choice("123456789") + "Z"
    return _maybe_lower(rng, first14 + gstin_check_char(first14), 0.06)


# ---------------------------------------------------------------------------
# Hard negatives (unlabelled look-alikes)
# ---------------------------------------------------------------------------
def neg_number12(rng: random.Random) -> str:
    """12 digits, same shapes as Aadhaar, but an order/invoice/ref number."""
    n = _digits(rng, 12)
    r = rng.random()
    if r < 0.35:
        return f"{n[:4]} {n[4:8]} {n[8:]}"
    if r < 0.45:
        return f"{n[:4]}-{n[4:8]}-{n[8:]}"
    return n


def neg_number10(rng: random.Random) -> str:
    """10 digits starting 6-9: phone-shaped ticket / AWB / reference number."""
    return rng.choice("6789") + _digits(rng, 9)


def neg_long_number(rng: random.Random) -> str:
    """9-18 digits: account-shaped transaction or consignment number."""
    return rng.choice("123456789") + _digits(rng, rng.randint(8, 17))


def neg_pan_shaped(rng: random.Random) -> str:
    """5 letters + 4 digits + 1 letter, used as a SKU / batch / model code."""
    return _letters(rng, 5) + _digits(rng, 4) + _letters(rng, 1)


def neg_ifsc_shaped(rng: random.Random) -> str:
    """4 letters + 0 + 6 chars, used as an item or part code."""
    return _letters(rng, 4) + "0" + _digits(rng, 6)


def neg_year_range(rng: random.Random) -> str:
    y = rng.randint(2015, 2026)
    sep = rng.choice(["-", " ", "/"])
    return sep.join(str(y + i) for i in range(3))


def neg_invoice(rng: random.Random) -> str:
    return rng.choice([
        f"INV-{rng.randint(2019, 2026)}-{_digits(rng, 5)}",
        f"INV{_digits(rng, 8)}",
        f"PO/{rng.randint(2019, 2026)}/{_digits(rng, 4)}",
        f"#{_digits(rng, 7)}",
    ])


def neg_txn(rng: random.Random) -> str:
    return rng.choice([
        f"TXN{_digits(rng, 12)}",
        f"UTR{_digits(rng, 12)}",
        _digits(rng, 12),
        f"T{_digits(rng, 14)}",
    ])


def neg_emp_id(rng: random.Random) -> str:
    return rng.choice([f"EMP{_digits(rng, 5)}", f"E-{_digits(rng, 4)}", f"{_letters(rng, 3)}{_digits(rng, 4)}"])


def neg_pincode(rng: random.Random) -> str:
    return rng.choice("12345678") + _digits(rng, 5)


def neg_otp(rng: random.Random) -> str:
    return _digits(rng, rng.choice([4, 6]))


def neg_version(rng: random.Random) -> str:
    return f"{rng.randint(1, 9)}.{rng.randint(0, 20)}.{rng.randint(0, 99)}"


def neg_amount(rng: random.Random) -> str:
    amount = rng.randint(100, 9_999_999)
    s = str(amount)
    # Indian grouping: last 3 digits, then groups of 2 (12,34,567).
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        s = ",".join(groups + [tail])
    return rng.choice([f"₹{s}", f"Rs. {s}", f"INR {s}", f"{s} rupees"])


def neg_date(rng: random.Random) -> str:
    d, m, y = rng.randint(1, 28), rng.randint(1, 12), rng.randint(2019, 2026)
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    return rng.choice([f"{d:02d}/{m:02d}/{y}", f"{d} {months[m - 1]} {y}", f"{y}-{m:02d}-{d:02d}"])


# ---------------------------------------------------------------------------
# Cues (words that introduce a value). Kept as unlabelled filler.
# ---------------------------------------------------------------------------
CUES = {
    "aadhaar_cue": ["Aadhaar", "Aadhaar no.", "Aadhaar number", "aadhar", "aadhar card no", "UID",
                    "Aadhaar No:", "UIDAI no.", "aadhaar card number", "Aadhar"],
    "pan_cue": ["PAN", "PAN no.", "PAN number", "pan card", "PAN Card No:", "Permanent Account Number", "pan"],
    "phone_cue": ["phone", "mobile", "mob", "contact no.", "ph", "cell", "WhatsApp", "mobile number", "Phone No:"],
    "email_cue": ["email", "e-mail", "mail id", "Email ID", "email address"],
    "acct_cue": ["A/c no", "account number", "acct", "a/c", "bank account", "Account No.", "Acc No"],
    "ifsc_cue": ["IFSC", "IFSC code", "ifsc", "IFSC Code:"],
    "gst_cue": ["GSTIN", "GST no.", "GST number", "gstin", "GST Reg. No."],
    "title": TITLES,
}

# Filler slots: name -> function(rng). Unlabelled.
FILLERS = {
    "city": lambda rng: rng.choice(CITIES),
    "company": lambda rng: rng.choice(COMPANIES),
    "product": lambda rng: rng.choice(PRODUCTS),
    "bank": lambda rng: rng.choice(BANK_NAMES),
    "amount": neg_amount,
    "date": neg_date,
    "num12": neg_number12,
    "num10": neg_number10,
    "longnum": neg_long_number,
    "sku": neg_pan_shaped,
    "itemcode": neg_ifsc_shaped,
    "years": neg_year_range,
    "invoice": neg_invoice,
    "txn": neg_txn,
    "empid": neg_emp_id,
    "pincode": neg_pincode,
    "otp": neg_otp,
    "version": neg_version,
    "qty": lambda rng: str(rng.randint(2, 500)),
}
for _cue, _options in CUES.items():
    FILLERS[_cue] = (lambda opts: (lambda rng: rng.choice(opts)))(_options)


# PII slots: template name -> (label, maker). Makers receive (rng, persona).
# `persona` holds the sentence's main person so an e-mail can be derived from
# the same name and a PAN can use that surname's initial, like real data.
def _surname(persona: dict) -> str | None:
    parts = persona.get("person", "").split()
    return parts[-1] if parts else None


PII_SLOTS = {
    "PERSON": ("PERSON", lambda rng, p: p["person"]),
    "PERSON2": ("PERSON", lambda rng, p: make_person(rng)),
    "AADHAAR": ("AADHAAR", lambda rng, p: make_aadhaar(rng)),
    "PAN": ("PAN", lambda rng, p: make_pan(rng, _surname(p))),
    "PHONE": ("PHONE", lambda rng, p: make_phone(rng)),
    "EMAIL": ("EMAIL", lambda rng, p: make_email(rng, p.get("person"))),
    "BANK_ACCOUNT": ("BANK_ACCOUNT", lambda rng, p: make_bank_account(rng)),
    "IFSC": ("IFSC", lambda rng, p: make_ifsc(rng)),
    "GSTIN": ("GSTIN", lambda rng, p: make_gstin(rng)),
}

LABELS = ["AADHAAR", "PAN", "PHONE", "EMAIL", "BANK_ACCOUNT", "IFSC", "GSTIN", "PERSON"]
