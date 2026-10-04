import unittest
import sys
from unittest.mock import patch, MagicMock, mock_open, call
from datetime import date
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
    @patch("banktamer.cli.open", new_callable=mock_open, read_data='{"santander": {}}')
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

        self.assertEqual(mock_print_report.call_args_list, [call(report_data)])

    @patch("banktamer.cli.ExcelReader")
    @patch("banktamer.cli.Categorizer")
    @patch("banktamer.cli.AnalyticsProcessor")
    @patch("argparse.ArgumentParser.parse_args")
    @patch("banktamer.report.pdf.PDFReporter")
    @patch("banktamer.cli.open", new_callable=mock_open, read_data='{"santander": {}}')
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

        self.assertEqual(mock_pdf_reporter.return_value.render.call_args_list, [call(report_data, "custom_report.pdf")])
        self.assertIn(call("Report generated successfully: custom_report.pdf"), mock_print.call_args_list)

    @patch("banktamer.cli.ExcelReader")
    @patch("banktamer.cli.Categorizer")
    @patch("banktamer.cli.AnalyticsProcessor")
    @patch("argparse.ArgumentParser.parse_args")
    @patch("banktamer.cli.os.getenv")
    @patch("banktamer.cli.open", new_callable=mock_open, read_data='{"santander": {}}')
    @patch("banktamer.cli.load_rules")
    @patch("builtins.print")
    def test_main_ai_missing_key(
        self,
        mock_print: MagicMock,
        mock_load_rules: MagicMock,
        mock_file: MagicMock,
        mock_getenv: MagicMock,
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
            ai="openai",
            ai_key=None,
            ai_url=None,
            ai_model=None,
        )
        mock_getenv.return_value = None

        mock_reader.return_value.read.return_value = [Transaction(date(2024, 1, 1), "Test", -10.0)]
        from banktamer.analytics import CategoryStats

        mock_processor.return_value.process.return_value = {
            "2024-01": {
                "total_income": 0.0,
                "total_expenses": -10.0,
                "categories": {"Food": CategoryStats(total=-10.0, max_txn=None)},
                "unknown_concepts": [],
            }
        }

        main()

        self.assertEqual(
            mock_print.call_args_list[-1],
            call("Error: AI provider 'openai' requires an API key (--ai-key or OPENAI_API_KEY env)."),
        )

    @patch("banktamer.cli.ExcelReader")
    @patch("argparse.ArgumentParser.parse_args")
    @patch("banktamer.cli.open", new_callable=mock_open, read_data='{"santander": {}}')
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

        self.assertEqual(
            mock_print.call_args_list[-1], call("No transactions found for bank 'santander' in the provided files.")
        )

    @patch("banktamer.cli.ExcelReader")
    @patch("argparse.ArgumentParser.parse_args")
    @patch("banktamer.cli.open", new_callable=mock_open, read_data='{"santander": {}}')
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

        self.assertEqual(mock_exit.call_args_list, [call(1)])
        self.assertIn(
            call("Configuration or Data Error: Specific logic error", file=sys.stderr), mock_print.call_args_list
        )

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
        mock_expanduser.return_value = "/home/user/.banktamer/config"
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
        mock_expanduser.return_value = "/home/user/.banktamer/config"
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

        # Pre-configured YAML contents
        default_yaml = yaml.dump({"General": ["Tax"]})
        category_yaml = yaml.dump({"General": ["Other"], "Utilities": ["Gas"]})

        # Use side_effect with a list to provide mocks in sequence
        # Order: 1. .default.yaml, 2. spec.yaml
        with patch(
            "builtins.open",
            side_effect=[
                mock_open(read_data=default_yaml).return_value,
                mock_open(read_data=category_yaml).return_value,
            ],
        ):
            rules = load_rules("rules", "spec")
            self.assertIn("General", rules)
            self.assertIn("Utilities", rules)
            self.assertEqual(rules["General"], ["Tax", "Other"])  # Merged
            self.assertEqual(rules["Utilities"], ["Gas"])

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

        self.assertEqual(mock_exit.call_args_list, [call(1)])
        self.assertIn(call("Unexpected Error: Surprise error", file=sys.stderr), mock_print.call_args_list)

    @patch("banktamer.cli.os.path.exists")
    def test_load_rules_not_found(self, mock_exists: MagicMock) -> None:
        from banktamer.cli import load_rules

        mock_exists.return_value = False
        with self.assertRaises(FileNotFoundError):
            load_rules("rules", "missing")


if __name__ == "__main__":
    unittest.main()
