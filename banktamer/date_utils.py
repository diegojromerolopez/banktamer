"""Utilities for parsing dates from localized bank statements and web elements."""

from datetime import date, timedelta
import re

SPANISH_MONTHS: dict[str, int] = {
    "enero": 1,
    "ene": 1,
    "febrero": 2,
    "feb": 2,
    "marzo": 3,
    "mar": 3,
    "abril": 4,
    "abr": 4,
    "mayo": 5,
    "may": 5,
    "junio": 6,
    "jun": 6,
    "julio": 7,
    "jul": 7,
    "agosto": 8,
    "ago": 8,
    "septiembre": 9,
    "sep": 9,
    "setiembre": 9,
    "octubre": 10,
    "oct": 10,
    "noviembre": 11,
    "nov": 11,
    "diciembre": 12,
    "dic": 12,
}


def parse_date_string(text: str, reference_date: date | None = None) -> date | None:
    """Parse a date from a text string supporting common formats (ISO, European, Spanish text)."""
    if not text:
        return None
    ref = reference_date or date.today()
    clean = text.lower().strip()
    clean = clean.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")

    # Check numeric YYYY-MM-DD
    iso_match = re.search(r"\b(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})\b", clean)
    if iso_match:
        try:
            return date(int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3)))
        except ValueError:
            pass

    # Check numeric DD/MM/YYYY or DD/MM/YY
    dmy_match = re.search(r"\b(\d{1,2})[-/.](\d{1,2})[-/.](\d{2,4})\b", clean)
    if dmy_match:
        try:
            d = int(dmy_match.group(1))
            m = int(dmy_match.group(2))
            y = int(dmy_match.group(3))
            if y < 100:
                y += 2000
            return date(y, m, d)
        except ValueError:
            pass

    # Check textual Spanish dates: e.g. "4 de octubre de 2026", "04 oct 2026", "4 de octubre"
    text_match = re.search(
        r"\b(\d{1,2})\s+(?:de\s+|del\s+)?([a-zñ]+)\.?(?:\s+(?:de\s+|del\s+)?(\d{2,4}))?\b",
        clean,
    )
    if text_match:
        d = int(text_match.group(1))
        m_raw = text_match.group(2).rstrip(".")
        if m_raw in SPANISH_MONTHS:
            m = SPANISH_MONTHS[m_raw]
            y_str = text_match.group(3)
            y = int(y_str) if y_str else ref.year
            if y < 100:
                y += 2000
            try:
                parsed = date(y, m, d)
                if not y_str and parsed > ref:
                    parsed = date(y - 1, m, d)
                return parsed
            except ValueError:
                return None

    # Check month + year: e.g. "Octubre 2026" or "Octubre de 2026"
    month_year_match = re.search(r"\b([a-zñ]+)\s+(?:de\s+|del\s+)?(\d{4})\b", clean)
    if month_year_match:
        m_word = month_year_match.group(1).rstrip(".")
        if m_word in SPANISH_MONTHS:
            m_val = SPANISH_MONTHS[m_word]
            y_val = int(month_year_match.group(2))
            return date(y_val, m_val, 1)

    if "hoy" in clean:
        return ref
    if "ayer" in clean:
        return ref - timedelta(days=1)

    return None
