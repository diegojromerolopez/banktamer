import unittest
from unittest.mock import patch, MagicMock
from datetime import date
from banktamer.report.pdf import PDFReporter
from banktamer.analytics import CategoryStats, MonthReport


class TestReportPdf(unittest.TestCase):
    @patch("banktamer.report.pdf.PDFReporter.output")
    @patch("os.path.exists")
    def test_pdf_reporter_render(self, mock_exists: MagicMock, mock_output: MagicMock) -> None:
        mock_exists.return_value = True  # Logo exists

        report_data: dict[str, MonthReport] = {
            "2024-01": {
                "total_income": 1000.0,
                "total_expenses": -500.0,
                "categories": {
                    "Salary": CategoryStats(total=1000.0, max_txn=MagicMock(amount=1000.0, concept="Work")),
                    "Food": CategoryStats(total=-500.0, max_txn=MagicMock(amount=-50.0, concept="Food")),
                },
                "unknown_concepts": [(date(2024, 1, 1), -50.0, "Misc")],
            }
        }

        reporter = PDFReporter()

        # We need to mock some internal methods of FPDF to avoid actually generating a file or needing fonts
        with patch.object(reporter, "image") as mock_image:
            reporter.render(report_data, "test.pdf")

            # Verify output was called
            mock_output.assert_called_once_with("test.pdf")
            # Verify logo was added
            mock_image.assert_called()

    @patch("banktamer.report.pdf.PDFReporter.output")
    @patch("os.path.exists")
    def test_pdf_reporter_no_logo(self, mock_exists: MagicMock, mock_output: MagicMock) -> None:
        mock_exists.return_value = False  # Logo missing

        report_data: dict[str, MonthReport] = {
            "2024-01": {
                "total_income": 100.0,
                "total_expenses": 0.0,
                "categories": {
                    "Gift": CategoryStats(total=100.0, max_txn=None),
                },
                "unknown_concepts": [],
            }
        }

        reporter = PDFReporter()
        with patch.object(reporter, "image") as mock_image:
            reporter.render(report_data, "test.pdf")
            mock_image.assert_not_called()

    @patch("banktamer.report.pdf.PDFReporter.output")
    def test_pdf_reporter_empty_data(self, mock_output: MagicMock) -> None:
        report_data: dict[str, MonthReport] = {}
        reporter = PDFReporter()
        reporter.render(report_data, "test.pdf")
        # Should still generate a PDF (empty or with header)
        mock_output.assert_called_once()

    @patch("banktamer.report.pdf.PDFReporter.output")
    def test_pdf_reporter_zero_abs_total(self, mock_output: MagicMock) -> None:
        # Case where total_abs == 0
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
        reporter = PDFReporter()
        reporter.render(report_data, "test.pdf")
        mock_output.assert_called_once()

    def test_pdf_reporter_footer_direct(self) -> None:
        # Direct call to footer for coverage
        reporter = PDFReporter()
        reporter.add_page()  # This should trigger footer internally, but let's be sure
        reporter.footer()

    @patch("banktamer.report.pdf.PDFReporter.output")
    def test_pdf_reporter_proportions_edge_case(self, mock_output: MagicMock) -> None:
        # Edge case to trigger line 155 (total_abs == 0 in proportions loop)
        report_data: dict[str, MonthReport] = {
            "2024-01": {
                "total_income": 100.0,
                "total_expenses": 0.0,
                "categories": {
                    "Food": CategoryStats(total=100.0, max_txn=None),
                },
                "unknown_concepts": [],
            }
        }
        reporter = PDFReporter()

        # Mock sum to return 0 to trigger the edge case
        with patch("banktamer.report.pdf.sum", return_value=0.0):
            reporter.render(report_data, "test.pdf")

        mock_output.assert_called_once()


if __name__ == "__main__":
    unittest.main()
