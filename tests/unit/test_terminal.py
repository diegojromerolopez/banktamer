import unittest
from unittest.mock import patch, MagicMock
from banktamer.report.terminal import print_ai_analysis, print_report
from banktamer.analytics import MonthReport, CategoryStats


class TestTerminalReport(unittest.TestCase):
    """Test suite for terminal reporting functions."""

    @patch("builtins.print")
    def test_print_ai_analysis(self, mock_print: MagicMock) -> None:
        """Test the AI analysis themed output."""
        print_ai_analysis("openai", "Test content")

        # Verify headers and content are printed
        mock_print.assert_any_call("Test content")
        # Check for the header (escaped colors might differ, so we check for substring)
        calls = [str(call) for call in mock_print.call_args_list]
        self.assertTrue(any("AI FINANCIAL ANALYSIS (OPENAI)" in c for c in calls))

    @patch("builtins.print")
    def test_print_report_basic(self, mock_print: MagicMock) -> None:
        """Test standard terminal report output."""
        report_data: dict[str, MonthReport] = {
            "2024-01": {
                "total_income": 1000.0,
                "total_expenses": -500.0,
                "categories": {"Food": CategoryStats(total=-500.0, max_txn=None)},
                "unknown_concepts": [],
            }
        }
        print_report(report_data)

        calls = [str(call) for call in mock_print.call_args_list]
        self.assertTrue(any("REPORT FOR 2024-01" in c for c in calls))
        self.assertTrue(any("1000.00" in c for c in calls))
        self.assertTrue(any("-500.00" in c for c in calls))
