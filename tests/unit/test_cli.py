import unittest
import sys
from unittest.mock import patch, MagicMock, mock_open
from datetime import date
from typing import Any
from banktamer.cli import main
from banktamer.analytics import CategoryStats
from banktamer.models import Transaction


class TestCli(unittest.TestCase):
    def setUp(self) -> None:
        self.dummy_schemas = {"santander": {"date_col": "Date", "concept_col": "Concept", "amount_col": "Amount"}}
        self.dummy_rules = {"Food": ["Supermarket"]}

    @patch("banktamer.cli.ExcelReader")
    @patch("banktamer.cli.Categorizer")
    @patch("banktamer.cli.AnalyticsProcessor")
    @patch("argparse.ArgumentParser.parse_args")
    @patch("banktamer.cli.print_report")
    @patch("builtins.open", new_callable=mock_open, read_data='{"santander": {}}')
    @patch("banktamer.cli.load_rules")
    @patch("builtins.print")
    def test_main_success(
        self,
        mock_print: MagicMock,
        mock_load_rules: MagicMock,
        mock_file: MagicMock,
        mock_print_report: MagicMock,
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
            schemas="fake_schemas.json",
            rules_dir=None,
            report="terminal",
            output=None,
        )

        mock_load_rules.return_value = self.dummy_rules
        mock_reader.return_value.read.return_value = [Transaction(date(2024, 1, 1), "Test", -10.0)]
        report_data = {
            "2024-01": {
                "total_income": 1000.0,
                "total_expenses": -500.0,
                "categories": {"Food": CategoryStats(total=-500.0, max_txn=None)},
                "unknown_concepts": [],
            }
        }
        mock_processor.return_value.process.return_value = report_data

        main()

        mock_print_report.assert_called_once_with(report_data)

    @patch("banktamer.cli.ExcelReader")
    @patch("banktamer.cli.Categorizer")
    @patch("banktamer.cli.AnalyticsProcessor")
    @patch("argparse.ArgumentParser.parse_args")
    @patch("banktamer.report.pdf.PDFReporter")
    @patch("builtins.open", new_callable=mock_open, read_data='{"santander": {}}')
    @patch("banktamer.cli.load_rules")
    @patch("builtins.print")
    def test_main_pdf_report(
        self,
        mock_print: MagicMock,
        mock_load_rules: MagicMock,
        mock_file: MagicMock,
        mock_pdf_reporter: MagicMock,
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
            schemas="fake_schemas.json",
            rules_dir=None,
            report="pdf",
            output="custom_report.pdf",
        )

        mock_reader.return_value.read.return_value = [MagicMock()]
        report_data = {
            "2024-01": {"total_income": 100.0, "total_expenses": -50.0, "categories": {}, "unknown_concepts": []}
        }
        mock_processor.return_value.process.return_value = report_data

        main()

        mock_pdf_reporter.return_value.render.assert_called_once_with(report_data, "custom_report.pdf")
        mock_print.assert_any_call("Report generated successfully: custom_report.pdf")

    @patch("banktamer.cli.ExcelReader")
    @patch("argparse.ArgumentParser.parse_args")
    @patch("builtins.open", new_callable=mock_open, read_data='{"santander": {}}')
    @patch("builtins.print")
    def test_main_no_transactions(
        self, mock_print: MagicMock, mock_file: MagicMock, mock_args: MagicMock, mock_reader: MagicMock
    ) -> None:
        mock_args.return_value = MagicMock(
            bank="santander",
            category="common",
            files=["test.xlsx"],
            config_dir=None,
            schemas="fake_schemas.json",
            rules_dir=None,
            report="terminal",
            output=None,
        )
        mock_reader.return_value.read.return_value = []

        main()

        mock_print.assert_any_call("No transactions found for bank 'santander' in the provided files.")

    @patch("banktamer.cli.ExcelReader")
    @patch("argparse.ArgumentParser.parse_args")
    @patch("builtins.open", new_callable=mock_open, read_data='{"santander": {}}')
    @patch("builtins.print")
    @patch("sys.exit")
    def test_main_error(
        self,
        mock_exit: MagicMock,
        mock_print: MagicMock,
        mock_file: MagicMock,
        mock_args: MagicMock,
        mock_reader: MagicMock,
    ) -> None:
        mock_args.return_value = MagicMock(
            bank="santander",
            category="common",
            files=["test.xlsx"],
            config_dir=None,
            schemas="fake_schemas.json",
            rules_dir=None,
            report="terminal",
            output=None,
        )
        mock_reader.return_value.read.side_effect = ValueError("Specific logic error")

        main()

        mock_exit.assert_called_with(1)
        mock_print.assert_any_call("Configuration or Data Error: Specific logic error", file=sys.stderr)

    @patch("os.path.exists")
    def test_resolve_config_defaults(self, mock_exists: MagicMock) -> None:
        from banktamer.cli import resolve_config

        args = MagicMock(config_dir=None, schemas=None, rules_dir=None)
        mock_exists.return_value = True
        config = resolve_config(args)
        self.assertEqual(config["schemas"], "config/schemas.json")
        self.assertEqual(config["rules_dir"], "config/categories")

    @patch("os.path.exists")
    @patch("os.path.expanduser")
    def test_resolve_config_fallback_home(self, mock_expanduser: MagicMock, mock_exists: MagicMock) -> None:
        from banktamer.cli import resolve_config

        args = MagicMock(config_dir=None, schemas=None, rules_dir=None)
        mock_expanduser.side_effect = lambda x: x.replace("~", "/home/user")
        # 1. config/schemas.json (False)
        # 2. /home/user/.banktamer/config/schemas.json (True)
        mock_exists.side_effect = [False, True]

        config = resolve_config(args)
        self.assertEqual(config["schemas"], "/home/user/.banktamer/config/schemas.json")

    @patch("os.path.exists")
    @patch("os.path.expanduser")
    @patch("os.path.dirname")
    def test_resolve_config_fallback_package(
        self, mock_dirname: MagicMock, mock_expanduser: MagicMock, mock_exists: MagicMock
    ) -> None:
        from banktamer.cli import resolve_config

        args = MagicMock(config_dir=None, schemas=None, rules_dir=None)
        mock_expanduser.side_effect = lambda x: x.replace("~", "/home/user")
        mock_dirname.return_value = "/pkg"
        # 1. config/schemas.json (False)
        # 2. /home/user/.banktamer/config/schemas.json (False)
        # 3. /pkg/config/schemas.json (True)
        mock_exists.side_effect = [False, False, True]

        config = resolve_config(args)
        self.assertEqual(config["schemas"], "/pkg/config/schemas.json")

    @patch("os.path.exists")
    def test_load_rules_merging(self, mock_exists: MagicMock) -> None:
        from banktamer.cli import load_rules
        import yaml

        # Mock .default.yaml exists and specific exists
        mock_exists.return_value = True

        # open_side_effect to return different content for default and specific
        def open_side_effect(path: str, *args: list[Any], **kwargs: dict[str, Any]) -> Any:
            if ".default.yaml" in str(path):
                return mock_open(read_data=yaml.dump({"General": ["Tax"]})).return_value
            return mock_open(read_data=yaml.dump({"General": ["Other"], "Utilities": ["Gas"]})).return_value

        with patch("builtins.open", side_effect=open_side_effect):
            rules = load_rules("rules", "spec")
            self.assertIn("General", rules)
            self.assertIn("Utilities", rules)
            self.assertEqual(rules["General"], ["Tax", "Other"])  # Merged
            self.assertEqual(rules["Utilities"], ["Gas"])

    @patch("os.path.exists")
    @patch("os.path.expanduser")
    @patch("sys.frozen", True, create=True)
    @patch("sys._MEIPASS", "/frozen_dir", create=True)
    def test_resolve_config_frozen(self, mock_expanduser: MagicMock, mock_exists: MagicMock) -> None:
        from banktamer.cli import resolve_config

        args = MagicMock(config_dir=None, schemas=None, rules_dir=None)
        mock_expanduser.side_effect = lambda x: x.replace("~", "/home/user")
        # 1. config/schemas.json (False)
        # 2. /home/user/.banktamer/config/schemas.json (False)
        # 3. /frozen_dir/banktamer/config/schemas.json (True)
        mock_exists.side_effect = [False, False, True]

        config = resolve_config(args)
        self.assertEqual(config["schemas"], "/frozen_dir/banktamer/config/schemas.json")

    @patch("banktamer.cli.run_pipeline")
    @patch("argparse.ArgumentParser.parse_args")
    @patch("builtins.print")
    @patch("sys.exit")
    def test_main_unexpected_error(
        self, mock_exit: MagicMock, mock_print: MagicMock, mock_args: MagicMock, mock_run: MagicMock
    ) -> None:
        mock_args.return_value = MagicMock(
            bank="santander", files=["test.xlsx"], config_dir=None, schemas=None, rules_dir=None
        )
        mock_run.side_effect = Exception("Surprise error")

        with patch("banktamer.cli.resolve_config"):
            main()

        mock_exit.assert_called_with(1)
        mock_print.assert_any_call("Unexpected Error: Surprise error", file=sys.stderr)


if __name__ == "__main__":
    unittest.main()
