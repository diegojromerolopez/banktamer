"""Unit tests for bank scraper and profile loading."""

import os
import tempfile
import unittest
from unittest.mock import MagicMock, call

from playwright.sync_api import Locator, Page

from banktamer.scraper import (
    BankProfile,
    BankScraper,
    BrowserAutomationError,
    CredentialConfig,
    MissingCredentialError,
    ProfileConfigError,
    ProfileNotFoundError,
    Step,
    StepExecutor,
    load_profile,
    resolve_placeholders,
)


class TestProfileLoading(unittest.TestCase):
    """Unit tests for profile loading and validation."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self) -> None:
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_load_profile_yaml_success(self) -> None:
        file_path = os.path.join(self.temp_dir, "mybank.yaml")
        content = (
            "bank: 'santander-es'\n"
            "url: 'https://example.com'\n"
            "headless: false\n"
            "timeout_ms: 15000\n"
            "credentials:\n"
            "  username:\n"
            "    env: 'MY_USER'\n"
            "  password: 'MY_PASSWORD'\n"
            "steps:\n"
            "  - action: 'navigate'\n"
            "    url: 'https://example.com/login'\n"
            "  - action: 'wait_for_selector'\n"
            "    selector: '#login'\n"
            "    state: 'visible'\n"
            "    timeout_ms: 5000\n"
        )
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        profile = load_profile(self.temp_dir, "mybank")

        self.assertEqual(profile.name, "mybank")
        self.assertEqual(profile.bank, "santander-es")
        self.assertEqual(profile.url, "https://example.com")
        self.assertFalse(profile.headless)
        self.assertEqual(profile.timeout_ms, 15000.0)
        self.assertEqual(
            profile.credentials,
            {
                "username": CredentialConfig(env_var="MY_USER"),
                "password": CredentialConfig(env_var="MY_PASSWORD"),
            },
        )
        self.assertEqual(len(profile.steps), 2)
        self.assertEqual(profile.steps[0].action, "navigate")
        self.assertEqual(profile.steps[0].url, "https://example.com/login")
        self.assertEqual(profile.steps[1].action, "wait_for_selector")
        self.assertEqual(profile.steps[1].selector, "#login")
        self.assertEqual(profile.steps[1].state, "visible")
        self.assertEqual(profile.steps[1].timeout_ms, 5000.0)

    def test_load_profile_yml_extension_success(self) -> None:
        file_path = os.path.join(self.temp_dir, "otherbank.yml")
        content = (
            "bank: 'revolut'\n"
            "steps:\n"
            "  - action: 'click'\n"
            "    selector: 'button.submit'\n"
            "    first: true\n"
            "    has_text: 'Submit'\n"
            "    seconds: 3.5\n"
        )
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        profile = load_profile(self.temp_dir, "otherbank")

        self.assertEqual(profile.name, "otherbank")
        self.assertEqual(profile.bank, "revolut")
        self.assertTrue(profile.headless)
        self.assertEqual(profile.timeout_ms, 30000.0)
        self.assertEqual(len(profile.steps), 1)
        self.assertEqual(profile.steps[0].action, "click")
        self.assertEqual(profile.steps[0].selector, "button.submit")
        self.assertTrue(profile.steps[0].first)
        self.assertEqual(profile.steps[0].has_text, "Submit")
        self.assertEqual(profile.steps[0].seconds, 3.5)

    def test_load_profile_not_found(self) -> None:
        with self.assertRaises(ProfileNotFoundError):
            load_profile(self.temp_dir, "nonexistent")

    def test_load_profile_not_a_mapping(self) -> None:
        file_path = os.path.join(self.temp_dir, "bad.yaml")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("- item1\n- item2\n")

        with self.assertRaises(ProfileConfigError):
            load_profile(self.temp_dir, "bad")

    def test_load_profile_missing_bank(self) -> None:
        file_path = os.path.join(self.temp_dir, "nobank.yaml")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("url: 'https://example.com'\nsteps: [{action: 'navigate'}]\n")

        with self.assertRaises(ProfileConfigError):
            load_profile(self.temp_dir, "nobank")

    def test_load_profile_missing_steps(self) -> None:
        file_path = os.path.join(self.temp_dir, "nosteps.yaml")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("bank: 'santander'\nsteps: []\n")

        with self.assertRaises(ProfileConfigError):
            load_profile(self.temp_dir, "nosteps")

    def test_load_profile_step_not_dict(self) -> None:
        file_path = os.path.join(self.temp_dir, "badstep.yaml")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("bank: 'santander'\nsteps:\n  - 'not_a_dict'\n")

        with self.assertRaises(ProfileConfigError):
            load_profile(self.temp_dir, "badstep")

    def test_load_profile_step_missing_action(self) -> None:
        file_path = os.path.join(self.temp_dir, "noaction.yaml")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("bank: 'santander'\nsteps:\n  - selector: '#btn'\n")

        with self.assertRaises(ProfileConfigError):
            load_profile(self.temp_dir, "noaction")


class TestPlaceholders(unittest.TestCase):
    """Unit tests for credential and environment placeholder substitution."""

    def test_resolve_placeholders_success(self) -> None:
        result = resolve_placeholders(
            text="Hello ${username}, pass=${password} and host=${HOST}",
            credentials_values={"username": "alice", "password": "secret"},
            env={"HOST": "example.org"},
        )
        self.assertEqual(result, "Hello alice, pass=secret and host=example.org")

    def test_resolve_placeholders_missing_variable(self) -> None:
        with self.assertRaises(MissingCredentialError):
            resolve_placeholders(
                text="User: ${missing_var}",
                credentials_values={},
                env={},
            )


class TestStepExecutor(unittest.TestCase):
    """Unit tests for StepExecutor on Playwright page actions."""

    def setUp(self) -> None:
        self.mock_page = MagicMock(spec=Page)
        self.profile = BankProfile(
            name="test_bank",
            bank="test-bank",
            url="https://base.example.com",
            steps=(),
            credentials={},
            headless=True,
            timeout_ms=10000.0,
        )
        self.executor = StepExecutor(
            page=self.mock_page,
            profile=self.profile,
            credentials={"user": "diego"},
            env={"PASS": "1234"},
            download_dir="/tmp/test_downloads",
        )

    def test_execute_navigate_with_step_url(self) -> None:
        step = Step(action="navigate", url="https://custom.example.com", timeout_ms=5000.0)
        result = self.executor.execute_step(step)

        self.assertIsNone(result)
        self.assertEqual(self.mock_page.goto.call_args_list, [call("https://custom.example.com", timeout=5000.0)])

    def test_execute_navigate_with_profile_url(self) -> None:
        step = Step(action="navigate")
        result = self.executor.execute_step(step)

        self.assertIsNone(result)
        self.assertEqual(self.mock_page.goto.call_args_list, [call("https://base.example.com", timeout=10000.0)])

    def test_execute_navigate_missing_url(self) -> None:
        empty_url_profile = BankProfile(
            name="empty", bank="b", url="", steps=(), credentials={}, headless=True, timeout_ms=10000.0
        )
        empty_executor = StepExecutor(
            page=self.mock_page,
            profile=empty_url_profile,
            credentials={},
            env={},
            download_dir="/tmp",
        )
        step = Step(action="navigate")
        with self.assertRaises(BrowserAutomationError):
            empty_executor.execute_step(step)

    def test_execute_fill_success(self) -> None:
        mock_locator = MagicMock(spec=Locator)
        self.mock_page.locator.return_value = mock_locator
        step = Step(action="fill", selector="#user_input", value="${user}")
        result = self.executor.execute_step(step)

        self.assertIsNone(result)
        self.assertEqual(self.mock_page.locator.call_args_list, [call("#user_input")])
        self.assertEqual(mock_locator.fill.call_args_list, [call("diego", timeout=10000.0)])

    def test_execute_fill_missing_selector(self) -> None:
        step = Step(action="fill", value="foo")
        with self.assertRaises(BrowserAutomationError):
            self.executor.execute_step(step)

    def test_execute_click_with_has_text_and_first(self) -> None:
        mock_locator = MagicMock(spec=Locator)
        mock_first = MagicMock(spec=Locator)
        mock_locator.first = mock_first
        self.mock_page.locator.return_value = mock_locator

        step = Step(action="click", selector="button.submit", has_text="Confirm", first=True, timeout_ms=3000.0)
        result = self.executor.execute_step(step)

        self.assertIsNone(result)
        self.assertEqual(self.mock_page.locator.call_args_list, [call("button.submit", has_text="Confirm")])
        self.assertEqual(mock_first.click.call_args_list, [call(timeout=3000.0)])

    def test_execute_click_missing_selector(self) -> None:
        step = Step(action="click")
        with self.assertRaises(BrowserAutomationError):
            self.executor.execute_step(step)

    def test_execute_wait_for_url_success(self) -> None:
        step = Step(action="wait_for_url", url="https://example.com/dashboard", timeout_ms=8000.0)
        result = self.executor.execute_step(step)

        self.assertIsNone(result)
        self.assertEqual(
            self.mock_page.wait_for_url.call_args_list,
            [call("https://example.com/dashboard", timeout=8000.0)],
        )

    def test_execute_wait_for_url_missing_url(self) -> None:
        step = Step(action="wait_for_url")
        with self.assertRaises(BrowserAutomationError):
            self.executor.execute_step(step)

    def test_execute_wait_for_selector_success(self) -> None:
        step = Step(action="wait_for_selector", selector=".modal", state="visible", timeout_ms=4000.0)
        result = self.executor.execute_step(step)

        self.assertIsNone(result)
        self.assertEqual(
            self.mock_page.wait_for_selector.call_args_list,
            [call(".modal", state="visible", timeout=4000.0)],
        )

    def test_execute_wait_for_selector_missing_selector(self) -> None:
        step = Step(action="wait_for_selector")
        with self.assertRaises(BrowserAutomationError):
            self.executor.execute_step(step)

    def test_execute_wait_success(self) -> None:
        step = Step(action="wait", seconds=2.5)
        result = self.executor.execute_step(step)

        self.assertIsNone(result)
        self.assertEqual(self.mock_page.wait_for_timeout.call_args_list, [call(2500.0)])

    def test_execute_download_success(self) -> None:
        mock_locator = MagicMock(spec=Locator)
        self.mock_page.locator.return_value = mock_locator

        mock_download = MagicMock()
        mock_download.suggested_filename = "transactions.xlsx"
        mock_info = MagicMock()
        mock_info.value = mock_download
        self.mock_page.expect_download.return_value.__enter__.return_value = mock_info

        step = Step(action="download", selector="button.download")
        result = self.executor.execute_step(step)

        self.assertEqual(result, "/tmp/test_downloads/transactions.xlsx")
        self.assertEqual(self.mock_page.locator.call_args_list, [call("button.download")])
        self.assertEqual(self.mock_page.expect_download.call_args_list, [call(timeout=10000.0)])
        self.assertEqual(mock_locator.click.call_args_list, [call(timeout=10000.0)])
        self.assertEqual(mock_download.save_as.call_args_list, [call("/tmp/test_downloads/transactions.xlsx")])

    def test_execute_download_missing_selector(self) -> None:
        step = Step(action="download")
        with self.assertRaises(BrowserAutomationError):
            self.executor.execute_step(step)

    def test_execute_unsupported_action(self) -> None:
        step = Step(action="unknown_action")
        with self.assertRaises(BrowserAutomationError):
            self.executor.execute_step(step)


class TestBankScraper(unittest.TestCase):
    """Unit tests for BankScraper runner and launcher."""

    def test_resolve_credentials_missing_env(self) -> None:
        profile = BankProfile(
            name="test",
            bank="test-bank",
            url="https://example.com",
            steps=(),
            credentials={"user": CredentialConfig(env_var="MISSING_USER")},
            headless=True,
            timeout_ms=10000.0,
        )
        scraper = BankScraper(env={})
        with self.assertRaises(MissingCredentialError):
            scraper.run_steps(page=MagicMock(spec=Page), profile=profile, download_dir="/tmp")

    def test_run_steps_without_download_step_raises(self) -> None:
        mock_page = MagicMock(spec=Page)
        profile = BankProfile(
            name="nodl",
            bank="test-bank",
            url="https://example.com",
            steps=(Step(action="navigate", url="https://example.com"),),
            credentials={"user": CredentialConfig(env_var="TEST_USER")},
            headless=True,
            timeout_ms=10000.0,
        )
        scraper = BankScraper(env={"TEST_USER": "diego"})
        with self.assertRaises(BrowserAutomationError):
            scraper.run_steps(page=mock_page, profile=profile, download_dir="/tmp")

    def test_download_launches_browser_and_cleans_up(self) -> None:
        mock_playwright = MagicMock()
        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_page = MagicMock(spec=Page)

        mock_playwright.chromium.launch.return_value = mock_browser
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page

        mock_download = MagicMock()
        mock_download.suggested_filename = "tx.xlsx"
        mock_info = MagicMock()
        mock_info.value = mock_download
        mock_page.expect_download.return_value.__enter__.return_value = mock_info

        mock_locator = MagicMock(spec=Locator)
        mock_page.locator.return_value = mock_locator

        mock_launcher = MagicMock()
        mock_launcher.return_value.__enter__.return_value = mock_playwright

        profile = BankProfile(
            name="p",
            bank="test-bank",
            url="https://example.com",
            steps=(Step(action="download", selector="#btn"),),
            credentials={},
            headless=False,
            timeout_ms=5000.0,
        )

        scraper = BankScraper(env={}, playwright_launcher=mock_launcher)
        result = scraper.download(profile=profile, download_dir="/tmp/dl", headless=True)

        self.assertEqual(result, "/tmp/dl/tx.xlsx")
        self.assertEqual(mock_playwright.chromium.launch.call_args_list, [call(headless=True)])
        self.assertEqual(mock_browser.new_context.call_args_list, [call(accept_downloads=True)])
        self.assertEqual(mock_context.new_page.call_args_list, [call()])
        self.assertEqual(mock_context.close.call_args_list, [call()])
        self.assertEqual(mock_browser.close.call_args_list, [call()])


if __name__ == "__main__":
    unittest.main()
