import unittest
from unittest.mock import patch, MagicMock
from datetime import date
from banktamer.cli import main, print_report
from banktamer.analytics import CategoryStats, MonthReport


class TestCli(unittest.TestCase):
    @patch("banktamer.cli.ExcelReader")
    @patch("banktamer.cli.Categorizer")
    @patch("banktamer.cli.AnalyticsProcessor")
    @patch("argparse.ArgumentParser.parse_args")
    @patch("builtins.print")
    def test_main_success(
        self,
        mock_print: MagicMock,
        mock_args: MagicMock,
        mock_processor: MagicMock,
        mock_categorizer: MagicMock,
        mock_reader: MagicMock,
    ) -> None:
        mock_args.return_value = MagicMock(
            bank="santander",
            category="common",
            files=["test.xlsx"],
            config_dir=None,
            schemas=None,
            rules_dir=None,
        )

        # Mock Reader to return some transactions
        mock_reader.return_value.read.return_value = [MagicMock()]

        # Mock Processor to return dummy report data
        mock_processor.return_value.process.return_value = {
            "2024-01": {"total_income": 1000.0, "total_expenses": -500.0, "categories": {}, "unknown_concepts": []}
        }

        main()

        mock_print.assert_any_call("\n==================================================")
        mock_print.assert_any_call(" REPORT FOR 2024-01")

    @patch("banktamer.cli.ExcelReader")
    @patch("banktamer.cli.Categorizer")
    @patch("banktamer.cli.AnalyticsProcessor")
    @patch("argparse.ArgumentParser.parse_args")
    @patch("os.path.exists")
    @patch("builtins.print")
    def test_main_no_category_arg(
        self,
        mock_print: MagicMock,
        mock_exists: MagicMock,
        mock_args: MagicMock,
        mock_processor: MagicMock,
        mock_categorizer: MagicMock,
        mock_reader: MagicMock,
    ) -> None:
        # Mock args WITHOUT category
        mock_args.return_value = MagicMock(
            bank="santander",
            category=None,
            files=["test.xlsx"],
            config_dir=None,
            schemas=None,
            rules_dir=None,
        )

        mock_exists.return_value = True  # Mock local config exists
        mock_reader.return_value.read.return_value = [MagicMock()]
        mock_processor.return_value.process.return_value = {
            "2024-01": {"total_income": 1000.0, "total_expenses": -500.0, "categories": {}, "unknown_concepts": []}
        }

        main()

        # Verify Categorizer was called with category=None and default rules_dir
        mock_categorizer.assert_called_with(None, rules_dir="config/categories")
        mock_print.assert_any_call(" REPORT FOR 2024-01")

    @patch("banktamer.cli.ExcelReader")
    @patch("argparse.ArgumentParser.parse_args")
    @patch("builtins.print")
    def test_main_no_transactions(self, mock_print: MagicMock, mock_args: MagicMock, mock_reader: MagicMock) -> None:
        mock_args.return_value = MagicMock(
            bank="santander",
            category="common",
            files=["test.xlsx"],
            config_dir=None,
            schemas=None,
            rules_dir=None,
        )
        mock_reader.return_value.read.return_value = []

        main()

        mock_print.assert_any_call("No transactions found for bank 'santander' in the provided files.")

    @patch("banktamer.cli.ExcelReader")
    @patch("argparse.ArgumentParser.parse_args")
    @patch("builtins.print")
    @patch("sys.exit")
    def test_main_error(
        self, mock_exit: MagicMock, mock_print: MagicMock, mock_args: MagicMock, mock_reader: MagicMock
    ) -> None:
        mock_args.return_value = MagicMock(
            bank="santander",
            category="common",
            files=["test.xlsx"],
            config_dir=None,
            schemas=None,
            rules_dir=None,
        )
        mock_reader.return_value.read.side_effect = Exception("Some error")

        main()

        mock_exit.assert_called_with(1)

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


    @patch("banktamer.cli.ExcelReader")
    @patch("banktamer.cli.Categorizer")
    @patch("banktamer.cli.AnalyticsProcessor")
    @patch("argparse.ArgumentParser.parse_args")
    @patch("os.path.exists")
    def test_main_fallback_home(
        self,
        mock_exists: MagicMock,
        mock_args: MagicMock,
        mock_processor: MagicMock,
        mock_categorizer: MagicMock,
        mock_reader: MagicMock,
    ) -> None:
        mock_args.return_value = MagicMock(
            bank="santander", category=None, files=["test.xlsx"], config_dir=None, schemas=None, rules_dir=None
        )
        # 1. Local schemas.json does not exist
        # 2. Home schemas.json DOES exist
        mock_exists.side_effect = [False, True]

        mock_reader.return_value.read.return_value = [MagicMock()]
        mock_processor.return_value.process.return_value = {"2024-01": {"total_income": 0.0, "total_expenses": 0.0, "categories": {}, "unknown_concepts": []}}

        main()
        
        # Should have called ExcelReader with the home path
        args, _ = mock_reader.call_args
        self.assertIn(".banktamer/config/schemas.json", args[0])

    @patch("banktamer.cli.ExcelReader")
    @patch("banktamer.cli.Categorizer")
    @patch("banktamer.cli.AnalyticsProcessor")
    @patch("argparse.ArgumentParser.parse_args")
    @patch("os.path.exists")
    def test_main_fallback_package(
        self,
        mock_exists: MagicMock,
        mock_args: MagicMock,
        mock_processor: MagicMock,
        mock_categorizer: MagicMock,
        mock_reader: MagicMock,
    ) -> None:
        mock_args.return_value = MagicMock(
            bank="santander", category=None, files=["test.xlsx"], config_dir=None, schemas=None, rules_dir=None
        )
        # 1. Local schemas.json does not exist
        # 2. Home schemas.json does not exist
        # 3. Package schemas.json DOES exist
        mock_exists.side_effect = [False, False, True]

        mock_reader.return_value.read.return_value = [MagicMock()]
        mock_processor.return_value.process.return_value = {"2024-01": {"total_income": 0.0, "total_expenses": 0.0, "categories": {}, "unknown_concepts": []}}

        main()
        
        # Should have called ExcelReader with the package path
        args, _ = mock_reader.call_args
        self.assertIn("banktamer/config/schemas.json", args[0])


    @patch("banktamer.cli.ExcelReader")
    @patch("banktamer.cli.Categorizer")
    @patch("banktamer.cli.AnalyticsProcessor")
    @patch("argparse.ArgumentParser.parse_args")
    @patch("builtins.print")
    def test_main_multiple_files(
        self,
        mock_print: MagicMock,
        mock_args: MagicMock,
        mock_processor: MagicMock,
        mock_categorizer: MagicMock,
        mock_reader: MagicMock,
    ) -> None:
        mock_args.return_value = MagicMock(
            bank="santander",
            category="common",
            files=["file1.xlsx", "file2.xlsx"],
            config_dir=None,
            schemas=None,
            rules_dir=None,
        )

        # Mock Reader to return different transactions for different files
        mock_reader.return_value.read.side_effect = [
            [MagicMock(concept="Txn1")],
            [MagicMock(concept="Txn2")],
        ]

        # Mock Processor
        mock_processor.return_value.process.return_value = {
            "2024-01": {"total_income": 1000.0, "total_expenses": -500.0, "categories": {}, "unknown_concepts": []}
        }

        main()

        # Verify reader was called for both files
        self.assertEqual(mock_reader.return_value.read.call_count, 2)
        mock_reader.return_value.read.assert_any_call("santander", "file1.xlsx")
        mock_reader.return_value.read.assert_any_call("santander", "file2.xlsx")

        # Verify categorizer was called with aggregated transactions (length 2)
        mock_categorizer.return_value.categorize.assert_called_once()
        args, _ = mock_categorizer.return_value.categorize.call_args
        self.assertEqual(len(args[0]), 2)

if __name__ == "__main__":
    unittest.main()
