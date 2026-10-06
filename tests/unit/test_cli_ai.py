import unittest
from unittest.mock import patch, MagicMock, call
from datetime import date
from banktamer.cli import main
from banktamer.analytics import CategoryStats
from banktamer.models import Transaction


class TestCliAi(unittest.TestCase):
    """Unit tests for CLI AI analysis integration."""

    @patch("banktamer.cli.print_ai_analysis")
    @patch("banktamer.cli.resolve_config")
    @patch("banktamer.cli.ExcelReader")
    @patch("banktamer.cli.Categorizer")
    @patch("banktamer.cli.AnalyticsProcessor")
    @patch("argparse.ArgumentParser.parse_args")
    @patch("banktamer.cli.AIProviderFactory")
    @patch("banktamer.cli.os.getenv")
    @patch("banktamer.cli.print_report")
    @patch("banktamer.cli.os.path.exists")
    @patch("banktamer.cli.load_rules")
    @patch("builtins.print")
    @patch("banktamer.cli.open")
    def test_main_with_ai(
        self,
        mock_file: MagicMock,
        mock_print: MagicMock,
        mock_load_rules: MagicMock,
        mock_exists: MagicMock,
        mock_print_report: MagicMock,
        mock_getenv: MagicMock,
        mock_ai_factory: MagicMock,
        mock_args: MagicMock,
        mock_processor: MagicMock,
        mock_categorizer: MagicMock,
        mock_reader: MagicMock,
        mock_resolve: MagicMock,
        mock_print_ai: MagicMock,
    ) -> None:
        mock_resolve.return_value = {
            "schemas": "fake_schemas.json",
            "rules_dir": "fake_categories",
            "config_dir": "config",
            "profiles_dir": "profiles",
        }
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
            ai_key="test-key",
            ai_url="http://custom-url",
            ai_model="gpt-4",
            profile=None,
        )

        # pyrefly: ignore [implicit-any-empty-container]
        mock_load_rules.return_value = {}
        mock_reader.return_value.read.return_value = [Transaction(date(2024, 1, 1), "Test", -10.0)]

        report_data = {
            "2024-01": {
                "total_income": 0.0,
                "total_expenses": -10.0,
                "categories": {"Food": CategoryStats(total=-10.0, max_txn=None)},
                # pyrefly: ignore [implicit-any-empty-container]
                "unknown_concepts": [],
            }
        }
        mock_processor.return_value.process.return_value = report_data

        mock_provider = MagicMock()
        mock_ai_factory.create.return_value = mock_provider
        mock_provider.ask.return_value = "AI Insights"
        mock_file.return_value.__enter__.return_value.read.return_value = "{}"

        main()

        self.assertEqual(
            mock_ai_factory.create.call_args_list,
            [call(provider_name="openai", api_key="test-key", model="gpt-4", base_url="http://custom-url")],
        )
        expected_summary = "Month: 2024-01\nIncome: 0.00\nExpenses: -10.00\nCategories: Food: -10.00"
        expected_prompt = (
            "You are an expert financial advisor. Analyze these bank transactions and provide:\n"
            "1. A brief summary of spending patterns.\n"
            "2. Specific, actionable money-saving suggestions.\n"
            "3. Any alarming trends or unusual category spikes.\n\n"
            f"Data:\n{expected_summary}"
        )
        self.assertEqual(mock_provider.ask.call_args_list, [call(expected_prompt)])
        self.assertEqual(mock_print_ai.call_args_list, [call("openai", "AI Insights")])

    @patch("banktamer.cli.print_ai_analysis")
    @patch("banktamer.cli.resolve_config")
    @patch("banktamer.cli.AIProviderFactory")
    @patch("banktamer.cli.run_pipeline")
    @patch("argparse.ArgumentParser.parse_args")
    @patch("banktamer.cli.os.path.exists")
    @patch("banktamer.cli.open")
    @patch("builtins.print")
    def test_main_with_custom_prompt(
        self,
        mock_print: MagicMock,
        mock_file: MagicMock,
        mock_exists: MagicMock,
        mock_args: MagicMock,
        mock_pipeline: MagicMock,
        mock_ai_factory: MagicMock,
        mock_resolve: MagicMock,
        mock_print_ai: MagicMock,
    ) -> None:
        mock_resolve.return_value = {"config_dir": "c", "profiles_dir": "profiles"}
        mock_exists.return_value = True
        mock_file.return_value.__enter__.return_value.read.return_value = (
            'prompt_templates: {financial_analysis: "Custom {summary}"}'
        )

        mock_args.return_value = MagicMock(
            bank="santander",
            files=["test.xlsx"],
            ai="openai",
            ai_key="k",
            ai_url=None,
            ai_model=None,
            report="terminal",
            output=None,
            profile=None,
        )
        mock_pipeline.return_value = {
            # pyrefly: ignore [implicit-any-empty-container]
            "2024-01": {"total_income": 0, "total_expenses": 0, "categories": {}, "unknown_concepts": []}
        }

        mock_provider = MagicMock()
        mock_ai_factory.create.return_value = mock_provider
        mock_provider.ask.return_value = "Response"

        main()

        self.assertEqual(len(mock_provider.ask.call_args_list), 1)
        prompt = mock_provider.ask.call_args_list[0][0][0]
        self.assertIn("Custom Month: 2024-01", prompt)

    @patch("banktamer.cli.print_ai_analysis")
    @patch("banktamer.cli.resolve_config")
    @patch("banktamer.cli.AIProviderFactory")
    @patch("banktamer.cli.run_pipeline")
    @patch("argparse.ArgumentParser.parse_args")
    @patch("banktamer.cli.os.path.exists")
    @patch("banktamer.cli.open")
    @patch("builtins.print")
    def test_main_with_invalid_yaml(
        self,
        mock_print: MagicMock,
        mock_file: MagicMock,
        mock_exists: MagicMock,
        mock_args: MagicMock,
        mock_pipeline: MagicMock,
        mock_ai_factory: MagicMock,
        mock_resolve: MagicMock,
        mock_print_ai: MagicMock,
    ) -> None:
        mock_resolve.return_value = {"config_dir": "c", "profiles_dir": "profiles"}
        mock_exists.return_value = True
        mock_file.return_value.__enter__.return_value.read.return_value = "}: invalid"

        mock_args.return_value = MagicMock(
            bank="santander",
            files=["test.xlsx"],
            ai="openai",
            ai_key="k",
            ai_url=None,
            ai_model=None,
            report="terminal",
            output=None,
            profile=None,
        )
        mock_pipeline.return_value = {
            # pyrefly: ignore [implicit-any-empty-container]
            "2024-01": {"total_income": 0, "total_expenses": 0, "categories": {}, "unknown_concepts": []}
        }

        mock_provider = MagicMock()
        mock_ai_factory.create.return_value = mock_provider
        mock_provider.ask.return_value = "Response"

        main()

        self.assertEqual(len(mock_provider.ask.call_args_list), 1)
        prompt = mock_provider.ask.call_args_list[0][0][0]
        self.assertIn("You are an expert financial advisor", prompt)

    @patch("banktamer.cli.print_ai_analysis")
    @patch("banktamer.cli.resolve_config")
    @patch("banktamer.cli.AIProviderFactory")
    @patch("banktamer.cli.run_pipeline")
    @patch("argparse.ArgumentParser.parse_args")
    @patch("banktamer.cli.os.path.exists")
    @patch("banktamer.cli.open")
    @patch("builtins.print")
    def test_main_with_custom_prompt_no_placeholder(
        self,
        mock_print: MagicMock,
        mock_file: MagicMock,
        mock_exists: MagicMock,
        mock_args: MagicMock,
        mock_pipeline: MagicMock,
        mock_ai_factory: MagicMock,
        mock_resolve: MagicMock,
        mock_print_ai: MagicMock,
    ) -> None:
        mock_resolve.return_value = {"config_dir": "c", "profiles_dir": "profiles"}
        mock_exists.return_value = True
        mock_file.return_value.__enter__.return_value.read.return_value = (
            'prompt_templates: {financial_analysis: "Custom prompt"}'
        )

        mock_args.return_value = MagicMock(
            bank="santander",
            files=["test.xlsx"],
            ai="openai",
            ai_key="k",
            ai_url=None,
            ai_model=None,
            report="terminal",
            output=None,
            profile=None,
        )
        mock_pipeline.return_value = {
            # pyrefly: ignore [implicit-any-empty-container]
            "2024-01": {"total_income": 0, "total_expenses": 0, "categories": {}, "unknown_concepts": []}
        }

        mock_provider = MagicMock()
        mock_ai_factory.create.return_value = mock_provider
        mock_provider.ask.return_value = "Response"

        main()

        self.assertEqual(len(mock_provider.ask.call_args_list), 1)
        prompt = mock_provider.ask.call_args_list[0][0][0]
        self.assertTrue(prompt.startswith("Custom prompt"))
        self.assertIn("Month: 2024-01", prompt)


if __name__ == "__main__":
    unittest.main()
