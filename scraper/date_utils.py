"""
scraper/date_utils.py

Single source of truth for date extraction and normalization.

Government/PSU pages write dates in wildly inconsistent formats:
    20 Jun 2026 | 22 June 2026 | 09-06-2026 | 2026-06-09 | 20.06.26
    2nd June 2026 | June 20, 2026 | 20/06/2026 | Last Date: 30-06-2026

Historically the parser stored whatever raw string it found, and every
downstream consumer (filters, frontend sort) re-guessed the format —
which is why 83% of postings ended up with no usable date and the UI
"newest first" sort silently collapsed.

This module centralizes two things:
    find_date(text)      -> best raw date substring found in free text (or "")
    normalize_date(s)    -> ISO "YYYY-MM-DD" for a raw date string (or "")
    extract_iso(text)    -> convenience: find + normalize in one call

`normalize_date` assumes **day-first** for ambiguous numeric dates
(DD/MM/YYYY), which is the Indian convention.
"""

import re

# ── Month name lookup (full + abbreviated + common misspellings) ──────────
_MONTHS = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

_MONTH_ALT = "|".join(sorted(_MONTHS.keys(), key=len, reverse=True))

# ── Recognized date shapes, in priority order ────────────────────────────
# Each pattern is tried against a text blob; the FIRST match wins, so more
# specific / less ambiguous shapes are listed first.
#
# 1. ISO:            2026-06-09  or  2026/06/09
# 2. Day-Month-Year: 20 Jun 2026 | 2nd June 2026 | 20-June-2026
# 3. Month-Day-Year: June 20, 2026 | Jun 20 2026
# 4. Numeric d/m/y:  09-06-2026 | 20/06/2026 | 20.06.2026 | 20.06.26
_PATTERNS = [
    ("iso", re.compile(
        r"\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b"
    )),
    ("dmy_name", re.compile(
        r"\b(\d{1,2})\s*(?:st|nd|rd|th)?[\s\-./]*"
        r"(" + _MONTH_ALT + r")[a-z]*"
        r"[\s\-./,]*(\d{2,4})\b",
        re.IGNORECASE,
    )),
    ("mdy_name", re.compile(
        r"\b(" + _MONTH_ALT + r")[a-z]*[\s\-./]*"
        r"(\d{1,2})\s*(?:st|nd|rd|th)?[\s,]*(\d{4})\b",
        re.IGNORECASE,
    )),
    ("dmy_num", re.compile(
        r"\b(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4})\b"
    )),
]

# Combined finder used to locate *any* date substring inside free-form text.
_ANY_DATE_RE = re.compile(
    "|".join(f"(?:{p.pattern})" for _, p in _PATTERNS),
    re.IGNORECASE,
)


def _four_digit_year(y):
    """Expand a 2-digit year to 4 digits (assume 2000s)."""
    y = int(y)
    if y < 100:
        # 26 -> 2026, 99 -> 2099. Gov listings are never pre-2000.
        y += 2000
    return y


def _valid(y, m, d):
    """Cheap sanity check without pulling in datetime for every candidate."""
    if not (1 <= m <= 12):
        return False
    if not (1 <= d <= 31):
        return False
    if not (2000 <= y <= 2099):
        return False
    return True


def normalize_date(raw):
    """
    Convert a raw date string into ISO 'YYYY-MM-DD'.

    Returns "" if no recognizable date is present. Numeric ambiguous dates
    are read day-first (Indian convention). If a numeric first field is
    clearly > 12 it is treated as the day regardless of position.
    """
    if not raw or not isinstance(raw, str):
        return ""

    text = raw.strip()

    for kind, pat in _PATTERNS:
        m = pat.search(text)
        if not m:
            continue

        try:
            if kind == "iso":
                y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))

            elif kind == "dmy_name":
                d = int(m.group(1))
                mo = _MONTHS[_month_key(m.group(2))]
                y = _four_digit_year(m.group(3))

            elif kind == "mdy_name":
                mo = _MONTHS[_month_key(m.group(1))]
                d = int(m.group(2))
                y = _four_digit_year(m.group(3))

            else:  # dmy_num — ambiguous, assume day-first
                a, b, c = int(m.group(1)), int(m.group(2)), _four_digit_year(m.group(3))
                if a > 12 >= b:          # a must be the day
                    d, mo = a, b
                elif b > 12 >= a:        # b must be the day -> month-first source
                    mo, d = a, b
                else:                    # both <= 12: day-first per Indian convention
                    d, mo = a, b
                y = c

            if _valid(y, mo, d):
                return f"{y:04d}-{mo:02d}-{d:02d}"
        except (KeyError, ValueError, IndexError):
            continue

    return ""


def _month_key(token):
    """Normalize a month token to its lookup key (handles 'Sept', 'JUNE')."""
    t = token.lower().strip()
    if t in _MONTHS:
        return t
    # Trim to a known prefix (e.g. 'septem' -> 'sep')
    for length in (4, 3):
        if t[:length] in _MONTHS:
            return t[:length]
    return t


def find_date(text):
    """
    Return the first raw date substring found in free-form text, or "".
    Preserves the original substring (useful for display/debugging).
    """
    if not text:
        return ""
    m = _ANY_DATE_RE.search(text)
    return m.group(0).strip() if m else ""


def extract_iso(text):
    """Find any date in *text* and return it normalized to ISO, or ""."""
    return normalize_date(find_date(text))


def year_of(raw):
    """
    Return the 4-digit year of a raw/ISO date string as int, or None.
    Used for the 'exclude listings from 2025 and older' cutoff.
    """
    iso = normalize_date(raw)
    if iso:
        return int(iso[:4])
    # Fall back to a bare 4-digit year anywhere in the string
    m = re.search(r"\b(20\d{2})\b", raw or "")
    return int(m.group(1)) if m else None
