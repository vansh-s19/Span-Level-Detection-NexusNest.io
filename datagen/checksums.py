"""
Checksum algorithms used by Indian identifiers.

Why this file exists
--------------------
A real Aadhaar number is not "any 12 digits": its last digit is a Verhoeff
check digit computed from the first 11. A real GSTIN's 15th character is a
mod-36 check character. Generating values that pass these checks makes the
synthetic data realistic, and the same functions are reused later as a
post-filter on the model's predictions (the "hybrid" step).
"""

# ---------------------------------------------------------------------------
# Verhoeff (used by Aadhaar)
# ---------------------------------------------------------------------------
# Three fixed tables from the dihedral group D5. `_D` is the group
# multiplication table, `_P` permutes a digit depending on its position, and
# `_INV` gives each element's inverse. Verhoeff catches every single-digit
# error and every swap of two adjacent digits, which a simple sum cannot.

_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]
_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]
_INV = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]


def verhoeff_check_digit(digits: str) -> str:
    """Return the check digit to append to `digits` (a string of 0-9)."""
    c = 0
    # Walk the digits right-to-left. Position starts at 1 because the check
    # digit itself will occupy position 0 once appended.
    for i, ch in enumerate(reversed(digits)):
        c = _D[c][_P[(i + 1) % 8][int(ch)]]
    return str(_INV[c])


def verhoeff_is_valid(number: str) -> bool:
    """True if a digit string (check digit included) passes Verhoeff."""
    digits = "".join(ch for ch in number if ch.isdigit())
    if not digits:
        return False
    c = 0
    for i, ch in enumerate(reversed(digits)):
        c = _D[c][_P[i % 8][int(ch)]]
    return c == 0


def is_valid_aadhaar(value: str) -> bool:
    """12 digits, first digit 2-9, valid Verhoeff check digit."""
    digits = "".join(ch for ch in value if ch.isdigit())
    return len(digits) == 12 and digits[0] in "23456789" and verhoeff_is_valid(digits)


# ---------------------------------------------------------------------------
# GSTIN check character (mod 36)
# ---------------------------------------------------------------------------
_GST_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def gstin_check_char(first14: str) -> str:
    """Return the 15th (check) character for the first 14 GSTIN characters."""
    total = 0
    for i, ch in enumerate(first14.upper()):
        value = _GST_CHARS.index(ch)
        factor = 1 if i % 2 == 0 else 2
        product = value * factor
        total += product // 36 + product % 36
    return _GST_CHARS[(36 - total % 36) % 36]


def is_valid_gstin(value: str) -> bool:
    value = value.strip().upper()
    return len(value) == 15 and gstin_check_char(value[:14]) == value[14]
