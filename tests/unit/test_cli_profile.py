"""Unit tests for BankTamer CLI profile automation."""

import argparse
import sys
import unittest
from unittest.mock import MagicMock, call, patch

from banktamer.cli import ConfigPaths, handle_profile_download, main, resolve_config
from banktamer.scraper import BankProfile, BrowserAutomationError, ProfileError, Step


class TestCliProfile(unittest.TestCase):
    """Unit tests for CLI profile handling."""

    def test_resolve_config_with_custom_profiles_dir(self) -> None:
        args = argparse.Namespace(config_dir="custom_cfg", schemas=None, rules_dir=None, profiles_dir="custom_profiles")
        with patch("os.path.exists", return_value=True):
            config = resolve_config(args)

        self.assertEqual(config["profiles_dir"], "custom_profiles")

    def test_handle_profile_download_none_profile(self) -> None:
        args = argparse.Namespace(profile=None, bank="santander", files=["test.xlsx"])
        config = ConfigPaths(
            schemas="schemas.json",
            rules_dir="categories",
            config_dir="config",
            profiles_dir="profiles",
        )
        handle_profile_download(args, config)
        self.assertEqual(args.bank, "santander")
        self.assertEqual(args.files, ["test.xlsx"])

    def test_handle_profile_download_non_string_profile(self) -> None:
        args = argparse.Namespace(profile=123, bank="santander", files=["test.xlsx"])
        config = ConfigPaths(
            schemas="schemas.json",
            rules_dir="categories",
            config_dir="config",
            profiles_dir="profiles",
        )
        handle_profile_download(args, config)
        self.assertEqual(args.bank, "santander")

    @patch("banktamer.cli.load_profile")
    def test_handle_profile_download_populates_bank_and_downloads_when_files_empty(
        self, mock_load_profile: MagicMock
    ) -> None:
        profile = BankProfile(
            name="santander",
            bank="santander-es",
            url="https://example.com",
            steps=(Step(action="download", selector="#btn"),),
            credentials={},
            headless=True,
            timeout_ms=5000.0,
        )
        mock_load_profile.return_value = profile

        mock_scraper = MagicMock()
        mock_scraper.download.return_value = "/tmp/downloads/transactions.xlsx"

        args = argparse.Namespace(
            profile="santander",
            bank=None,
            files=None,
            download_dir="/tmp/downloads",
            headless=False,
        )
        config = ConfigPaths(
            schemas="schemas.json",
            rules_dir="categories",
            config_dir="config",
            profiles_dir="/custom/profiles",
        )

        handle_profile_download(args, config, scraper=mock_scraper)

        self.assertEqual(mock_load_profile.call_args_list, [call("/custom/profiles", "santander")])
        self.assertEqual(args.bank, "santander-es")
        self.assertEqual(
            mock_scraper.download.call_args_list,
            [call(profile=profile, download_dir="/tmp/downloads", headless=False)],
        )
        self.assertEqual(args.files, ["/tmp/downloads/transactions.xlsx"])

    @patch("banktamer.cli.load_profile")
    def test_handle_profile_download_keeps_existing_bank_and_skips_when_files_provided(
        self, mock_load_profile: MagicMock
    ) -> None:
        profile = BankProfile(
            name="santander",
            bank="santander-es",
            url="https://example.com",
            steps=(),
            credentials={},
            headless=True,
            timeout_ms=5000.0,
        )
        mock_load_profile.return_value = profile
        mock_scraper = MagicMock()

        args = argparse.Namespace(
            profile="santander",
            bank="custom-bank",
            files=["already_existing.xlsx"],
            download_dir=None,
            headless=None,
        )
        config = ConfigPaths(
            schemas="schemas.json",
            rules_dir="categories",
            config_dir="config",
            profiles_dir="profiles",
        )

        handle_profile_download(args, config, scraper=mock_scraper)

        self.assertEqual(args.bank, "custom-bank")
        self.assertEqual(args.files, ["already_existing.xlsx"])
        self.assertEqual(mock_scraper.download.call_args_list, [])

    @patch("banktamer.cli.handle_profile_download")
    @patch("banktamer.cli.run_pipeline")
    @patch("banktamer.cli.generate_report")
    @patch("banktamer.cli.resolve_config")
    @patch("argparse.ArgumentParser.parse_args")
    def test_main_with_profile_success(
        self,
        mock_parse_args: MagicMock,
        mock_resolve_config: MagicMock,
        mock_generate_report: MagicMock,
        mock_run_pipeline: MagicMock,
        mock_handle_download: MagicMock,
    ) -> None:
        mock_parse_args.return_value = argparse.Namespace(
            bank=None,
            profile="santander",
            files=None,
            category=None,
            config_dir=None,
            schemas=None,
            rules_dir=None,
            profiles_dir=None,
            download_dir=None,
            headless=True,
            report="terminal",
            output=None,
            ai=None,
            ai_key=None,
            ai_url=None,
            ai_model=None,
        )
        mock_config = {
            "schemas": "s",
            "rules_dir": "r",
            "config_dir": "c",
            "profiles_dir": "p",
        }
        mock_resolve_config.return_value = mock_config
        mock_run_pipeline.return_value = {"2024-01": {"total_income": 0}}

        main()

        self.assertEqual(mock_handle_download.call_args_list, [call(mock_parse_args.return_value, mock_config)])
        self.assertEqual(mock_run_pipeline.call_args_list, [call(mock_parse_args.return_value, mock_config)])
        self.assertEqual(
            mock_generate_report.call_args_list,
            [call(mock_parse_args.return_value, {"2024-01": {"total_income": 0}}, mock_config)],
        )

    def test_main_validation_missing_bank_and_profile(self) -> None:
        with patch("sys.argv", ["banktamer", "--files", "f.xlsx"]), patch("sys.stderr"):
            with self.assertRaises(SystemExit) as cm:
                main()
        self.assertEqual(cm.exception.code, 2)

    def test_main_validation_missing_files_and_profile(self) -> None:
        with patch("sys.argv", ["banktamer", "--bank", "santander"]), patch("sys.stderr"):
            with self.assertRaises(SystemExit) as cm:
                main()
        self.assertEqual(cm.exception.code, 2)

    @patch("banktamer.cli.handle_profile_download")
    @patch("banktamer.cli.resolve_config")
    @patch("argparse.ArgumentParser.parse_args")
    @patch("builtins.print")
    @patch("sys.exit")
    def test_main_catches_profile_error(
        self,
        mock_exit: MagicMock,
        mock_print: MagicMock,
        mock_parse_args: MagicMock,
        mock_resolve_config: MagicMock,
        mock_handle_download: MagicMock,
    ) -> None:
        mock_parse_args.return_value = argparse.Namespace(bank=None, profile="santander", files=None)
        mock_handle_download.side_effect = ProfileError("Profile file broken")

        main()

        self.assertEqual(mock_exit.call_args_list, [call(1)])
        self.assertEqual(
            mock_print.call_args_list,
            [call("Configuration or Data Error: Profile file broken", file=sys.stderr)],
        )

    @patch("banktamer.cli.handle_profile_download")
    @patch("banktamer.cli.resolve_config")
    @patch("argparse.ArgumentParser.parse_args")
    @patch("builtins.print")
    @patch("sys.exit")
    def test_main_catches_browser_automation_error(
        self,
        mock_exit: MagicMock,
        mock_print: MagicMock,
        mock_parse_args: MagicMock,
        mock_resolve_config: MagicMock,
        mock_handle_download: MagicMock,
    ) -> None:
        mock_parse_args.return_value = argparse.Namespace(bank=None, profile="santander", files=None)
        mock_handle_download.side_effect = BrowserAutomationError("Failed to click selector")

        main()

        self.assertEqual(mock_exit.call_args_list, [call(1)])
        self.assertEqual(
            mock_print.call_args_list,
            [call("Configuration or Data Error: Failed to click selector", file=sys.stderr)],
        )


if __name__ == "__main__":
    unittest.main()
