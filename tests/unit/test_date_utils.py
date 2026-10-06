"""Unit tests for date utilities in banktamer."""

from datetime import date, timedelta
import unittest
from banktamer.date_utils import parse_date_string


class TestDateUtils(unittest.TestCase):
    """Test suite for date parsing utilities."""

    def test_parse_empty_or_whitespace_returns_none(self) -> None:
        """Verify that empty or whitespace strings return None."""
        self.assertIsNone(parse_date_string(""))
        self.assertIsNone(parse_date_string("   "))

    def test_parse_iso_format(self) -> None:
        """Verify parsing of ISO formatted dates."""
        result = parse_date_string("2026-10-04")
        self.assertEqual(result, date(2026, 10, 4))

    def test_parse_iso_with_slashes(self) -> None:
        """Verify parsing of ISO dates with slashes."""
        result = parse_date_string("2026/05/12")
        self.assertEqual(result, date(2026, 5, 12))

    def test_parse_iso_invalid_date_falls_through(self) -> None:
        """Verify that invalid ISO date string returns None."""
        result = parse_date_string("2026-02-31")
        self.assertIsNone(result)

    def test_parse_dmy_numeric_slashes(self) -> None:
        """Verify parsing of DD/MM/YYYY numeric format."""
        result = parse_date_string("04/10/2026")
        self.assertEqual(result, date(2026, 10, 4))

    def test_parse_dmy_numeric_two_digit_year(self) -> None:
        """Verify parsing of DD-MM-YY format with 2-digit year."""
        result = parse_date_string("04-10-26")
        self.assertEqual(result, date(2026, 10, 4))

    def test_parse_dmy_invalid_date_falls_through(self) -> None:
        """Verify that invalid DMY dates return None."""
        result = parse_date_string("31/02/2026")
        self.assertIsNone(result)

    def test_parse_spanish_textual_full_date(self) -> None:
        """Verify parsing of full Spanish textual date with 'de'."""
        result = parse_date_string("4 de octubre de 2026")
        self.assertEqual(result, date(2026, 10, 4))

    def test_parse_spanish_textual_with_del(self) -> None:
        """Verify parsing of Spanish textual date with 'del'."""
        result = parse_date_string("15 de mayo del 2025")
        self.assertEqual(result, date(2025, 5, 15))

    def test_parse_spanish_textual_abbreviated_month(self) -> None:
        """Verify parsing of Spanish abbreviated month."""
        result = parse_date_string("4 oct 2026")
        self.assertEqual(result, date(2026, 10, 4))

    def test_parse_spanish_textual_two_digit_year(self) -> None:
        """Verify parsing of Spanish textual date with 2-digit year."""
        result = parse_date_string("4 oct. 26")
        self.assertEqual(result, date(2026, 10, 4))

    def test_parse_spanish_textual_without_year_past_month(self) -> None:
        """Verify parsing of Spanish textual date without year resolves to same year when past."""
        ref = date(2026, 10, 4)
        result = parse_date_string("4 de mayo", reference_date=ref)
        self.assertEqual(result, date(2026, 5, 4))

    def test_parse_spanish_textual_without_year_future_month(self) -> None:
        """Verify parsing of Spanish textual date without year resolves to previous year when future."""
        ref = date(2026, 10, 4)
        result = parse_date_string("4 de noviembre", reference_date=ref)
        self.assertEqual(result, date(2025, 11, 4))

    def test_parse_spanish_weekday_and_day_month(self) -> None:
        """Verify parsing of Spanish date format 'Lunes, 27 Julio'."""
        ref = date(2026, 10, 4)
        result = parse_date_string("Lunes, 27 Julio", reference_date=ref)
        self.assertEqual(result, date(2026, 7, 27))

    def test_parse_spanish_weekday_with_accent_and_single_digit_day(self) -> None:
        """Verify parsing of accented weekday with single digit day."""
        ref = date(2026, 10, 4)
        result = parse_date_string("Miércoles, 5 Agosto", reference_date=ref)
        self.assertEqual(result, date(2026, 8, 5))

    def test_parse_spanish_textual_invalid_date_falls_through(self) -> None:
        """Verify that invalid textual date falls through to None."""
        result = parse_date_string("31 de febrero de 2026")
        self.assertIsNone(result)

    def test_parse_spanish_month_and_year_only(self) -> None:
        """Verify parsing of month and year only format."""
        result = parse_date_string("Octubre de 2026")
        self.assertEqual(result, date(2026, 10, 1))

    def test_parse_hoy_keyword(self) -> None:
        """Verify parsing of 'Hoy' keyword."""
        ref = date(2026, 10, 4)
        result = parse_date_string("Hoy", reference_date=ref)
        self.assertEqual(result, ref)

    def test_parse_ayer_keyword(self) -> None:
        """Verify parsing of 'Ayer' keyword."""
        ref = date(2026, 10, 4)
        result = parse_date_string("Ayer", reference_date=ref)
        self.assertEqual(result, ref - timedelta(days=1))

    def test_parse_unrecognized_text_returns_none(self) -> None:
        """Verify that unrecognized non-date text returns None."""
        result = parse_date_string("Texto no relacionado con fechas")
        self.assertIsNone(result)
