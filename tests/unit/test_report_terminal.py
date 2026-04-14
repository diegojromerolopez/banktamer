import unittest
from unittest.mock import patch, MagicMock
from datetime import date
from banktamer.report.terminal import print_report
from banktamer.analytics import CategoryStats, MonthReport


class TestReportTerminal(unittest.TestCase):
    def test_print_report_calculations(self) -> None:
        # Create dummy report data to test percentage branches
        report_data: dict[str, MonthReport] = {
            "2024-01": {
                "total_income": 1000.0,
                "total_expenses": -500.0,
                "categories": {
                    "Salary": CategoryStats(total=1000.0, max_txn=MagicMock(amount=1000.0, concept="Work")),
                    "Food": CategoryStats(total=-200.0, max_txn=MagicMock(amount=-50.0, concept="Restaurant")),
                    "Zero": CategoryStats(total=0.0, max_txn=None),
                },
                "unknown_concepts": [(date(2024, 1, 1), -50.0, "Unknown Item")],
            }
        }

        with patch("builtins.print") as mock_print_call:
            print_report(report_data)

            # Check if percentages were printed (roughly)
            # Salary should be 100% of income
            # Food should be 40% of expenses (-200 / -500)
            print_calls = [str(call) for call in mock_print_call.mock_calls]
            self.assertTrue(any("100.0%" in s for s in print_calls))
            self.assertTrue(any("40.0%" in s for s in print_calls))
            self.assertTrue(any("Unknown Item" in s for s in print_calls))

    def test_print_report_with_charts(self) -> None:
        report_data: dict[str, MonthReport] = {
            "2024-01": {
                "total_income": 1000.0,
                "total_expenses": -500.0,
                "categories": {
                    "Salary": CategoryStats(total=1000.0, max_txn=MagicMock(amount=1000.0, concept="Work")),
                    "Food": CategoryStats(total=-250.0, max_txn=MagicMock(amount=-50.0, concept="Restaurant")),
                },
                "unknown_concepts": [],
            }
        }

        with patch("builtins.print") as mock_print:
            print_report(report_data)

            # Verify bar rendering
            # Salary is 100%, bar should be width 30
            # Food is 50%, bar should be width 15
            print_calls = [str(call) for call in mock_print.mock_calls]

            # Check for colors
            # Salary is positive -> GREEN (\033[92m)
            # Food is negative -> RED (\033[91m)
            self.assertTrue(any("\033[92m" in str(arg) for call in mock_print.mock_calls for arg in call.args))
            self.assertTrue(any("\033[91m" in str(arg) for call in mock_print.mock_calls for arg in call.args))
            self.assertTrue(any("█" in s for s in print_calls))

    def test_print_report_with_pie_chart(self) -> None:
        report_data: dict[str, MonthReport] = {
            "2024-01": {
                "total_income": 1000.0,
                "total_expenses": -500.0,
                "categories": {
                    "Salary": CategoryStats(total=1000.0, max_txn=MagicMock(amount=1000.0, concept="Work")),
                    "Food": CategoryStats(total=-250.0, max_txn=MagicMock(amount=-50.0, concept="Restaurant")),
                },
                "unknown_concepts": [],
            }
        }

        with patch("builtins.print") as mock_print:
            # Test with pie chart (now always shown)
            print_report(report_data)

            # Check for grid characters (they would be in a line starting with indent)
            print_calls = [str(call) for call in mock_print.mock_calls]
            self.assertTrue(any("█" in s for s in print_calls))
            self.assertTrue(any("FINANCIAL DISTRIBUTION:" in s for s in print_calls))

    def test_print_report_pie_chart_all_categories(self) -> None:
        # Pie chart now shows all categories (income and expenses)
        report_data: dict[str, MonthReport] = {
            "2024-01": {
                "total_income": 1000.0,
                "total_expenses": 0.0,
                "categories": {
                    "Salary": CategoryStats(total=1000.0, max_txn=None),
                },
                "unknown_concepts": [],
            }
        }
        with patch("builtins.print") as mock_print:
            print_report(report_data)
            print_calls = [str(call) for call in mock_print.mock_calls]
            self.assertTrue(any("█" in s for s in print_calls))

    def test_print_report_pie_chart_empty(self) -> None:
        # Pie chart should return early if no data
        report_data: dict[str, MonthReport] = {
            "2024-01": {
                "total_income": 0.0,
                "total_expenses": 0.0,
                "categories": {},
                "unknown_concepts": [],
            }
        }
        with patch("builtins.print") as mock_print:
            print_report(report_data)
            print_calls = [str(call) for call in mock_print.mock_calls]
            self.assertFalse(any("█" in s for s in print_calls))

    def test_print_report_zero_data(self) -> None:
        # Test zero income/expenses to avoid division by zero
        report_data: dict[str, MonthReport] = {
            "2024-01": {
                "total_income": 0.0,
                "total_expenses": 0.0,
                "categories": {
                    "Empty": CategoryStats(total=0.0, max_txn=None),
                },
                "unknown_concepts": [],
            }
        }
        with patch("builtins.print") as mock_print:
            print_report(report_data)
            # Should not crash and should not print bars (percentage is 0)
            print_calls = [str(call) for call in mock_print.mock_calls]
            self.assertFalse(any("█" in s for s in print_calls))

    def test_render_pie_chart_direct_empty(self) -> None:
        # Direct test for coverage of total_abs == 0 early return
        from banktamer.report.terminal import render_pie_chart

        with patch("builtins.print") as mock_print:
            render_pie_chart([], {})
            mock_print.assert_not_called()


if __name__ == "__main__":
    unittest.main()
