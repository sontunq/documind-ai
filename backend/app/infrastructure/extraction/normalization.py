"""Normalization utilities for dates, currency, and numerical amounts."""
from datetime import datetime
import re

MONTHS = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}

CURRENCY_SYMBOLS = {
    "$": "USD",
    "€": "EUR",
    "£": "GBP",
    "¥": "JPY",
    "₫": "VND",
    "đ": "VND",
    "VNĐ": "VND",
    "vnđ": "VND",
    "đồng": "VND",
    "Đồng": "VND",
    "₹": "INR",
}

KNOWN_CURRENCY_CODES = {
    "USD", "EUR", "GBP", "CAD", "AUD", "JPY", "VND", "SGD", "CHF", "CNY", "INR",
}


def clean_text(text: str) -> str:
    """Strip whitespace, trailing/leading colons, dashes, and fill-in underscores."""
    text = re.sub(r"[_\s]+$", "", text)
    text = re.sub(r"^[:\s\-]+", "", text)
    text = re.sub(r"[:\s\-]+$", "", text)
    return text.strip()


def normalize_date(text: str) -> str | None:
    """Normalize common date formats (English & Vietnamese) to ISO-8601 YYYY-MM-DD."""
    if not text:
        return None
    cleaned = text.strip().rstrip(".,;")

    # 1. Vietnamese natural date format: Ngày DD tháng MM năm YYYY
    vn_match = re.search(r"(?:ngày\s+)?(\d{1,2})\s+tháng\s+(\d{1,2})(?:,?\s+năm\s+|\s+năm\s+|\s+)(20\d\d|19\d\d)\b", cleaned, re.IGNORECASE)
    if vn_match:
        day, month, year = int(vn_match.group(1)), int(vn_match.group(2)), int(vn_match.group(3))
        if 1 <= month <= 12 and 1 <= day <= 31:
            return f"{year:04d}-{month:02d}-{day:02d}"

    # 2. ISO format: YYYY-MM-DD
    match = re.search(r"\b(20\d\d|19\d\d)[-/.](0?[1-9]|1[0-2])[-/.](0?[1-9]|[12]\d|3[01])\b", cleaned)
    if match:
        year, month, day = int(match.group(1)), int(match.group(2)), int(match.group(3))
        return f"{year:04d}-{month:02d}-{day:02d}"

    # 3. Month Day, Year: e.g. September 1, 2026 or Sep 01 2026
    month_names = "|".join(MONTHS.keys())
    match = re.search(rf"\b({month_names})\.?\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(20\d\d|19\d\d)\b", cleaned, re.IGNORECASE)
    if match:
        month = MONTHS[match.group(1).lower()]
        day = int(match.group(2))
        year = int(match.group(3))
        return f"{year:04d}-{month:02d}-{day:02d}"

    # 4. Day Month Year: e.g. 1 September 2026 or 01 Sep 2026
    match = re.search(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({month_names})\.?,?\s+(20\d\d|19\d\d)\b", cleaned, re.IGNORECASE)
    if match:
        day = int(match.group(1))
        month = MONTHS[match.group(2).lower()]
        year = int(match.group(3))
        return f"{year:04d}-{month:02d}-{day:02d}"

    # 5. MM/DD/YYYY or DD/MM/YYYY
    match = re.search(r"\b(0?[1-9]|[12]\d|3[01])[-/.](0?[1-9]|[12]\d|3[01])[-/.](20\d\d|19\d\d)\b", cleaned)
    if match:
        p1, p2, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
        if p1 <= 12 and p2 > 12:  # MM/DD/YYYY
            return f"{year:04d}-{p1:02d}-{p2:02d}"
        if p2 <= 12 and p1 > 12:  # DD/MM/YYYY
            return f"{year:04d}-{p2:02d}-{p1:02d}"
        # Default assume YYYY-MM-DD format if indeterminate: MM/DD/YYYY
        return f"{year:04d}-{p1:02d}-{p2:02d}"

    return None


def normalize_amount(text: str) -> float | None:
    """Extract and normalize numerical monetary amount (e.g. '$88.00' -> 88.0, '25.000.000' -> 25000000.0)."""
    if not text:
        return None
    # 1. Vietnamese dot-thousand format with optional decimal comma: e.g. 25.218.000 or 25.218.000,50
    dot_vn = re.search(r"[-+]?\s*(\d{1,3}(?:\.\d{3})+)(?:,(\d{1,2}))?", text)
    if dot_vn:
        int_part = dot_vn.group(1).replace(".", "")
        dec_part = dot_vn.group(2)
        raw_val = f"{int_part}.{dec_part}" if dec_part else int_part
        try:
            return round(float(raw_val), 2)
        except ValueError:
            pass

    # 2. Standard comma-thousand format: e.g. 25,218,000.00 or $88.00
    match = re.search(r"[-+]?\s*(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{1,2})?", text)
    if not match:
        return None
    raw = match.group(0).replace(" ", "").replace(",", "")
    try:
        val = float(raw)
        return round(val, 2)
    except ValueError:
        return None


def normalize_currency(text: str) -> str | None:
    """Find and normalize currency code from string."""
    if not text:
        return None
    for sym, code in CURRENCY_SYMBOLS.items():
        if re.search(rf"(?:^|[\s\d]){re.escape(sym)}(?:$|[\s\d])", text, re.IGNORECASE) or sym in text:
            return code
    words = re.findall(r"\b[A-Z]{3}\b", text.upper())
    for word in words:
        if word in KNOWN_CURRENCY_CODES:
            return word
    return None
