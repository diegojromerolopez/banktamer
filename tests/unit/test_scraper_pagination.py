"""Unit tests for scraper pagination and load_until_date action."""

from datetime import date
import os
import tempfile
import unittest
from unittest.mock import MagicMock, call

from playwright.sync_api import (
    Locator,
    Page,
    TimeoutError as PlaywrightTimeoutError,
)

from banktamer.scraper import (
    BankProfile,
    BankScraper,
    BrowserAutomationError,
    Step,
    StepExecutor,
    load_profile,
)


class TestScraperPagination(unittest.TestCase):
    """Unit tests for load_until_date action and pagination handling."""

    def setUp(self) -> None:
        """Set up test environment and mock page context."""
        self.mock_page = MagicMock(spec=Page)
        self.mock_logger = MagicMock()
        self.fixed_today = date(2026, 10, 4)
        self.profile = BankProfile(
            name="test_bank",
            bank="santander-es",
            url="https://base.example.com",
            steps=(),
            credentials={},
            headless=True,
            timeout_ms=10000.0,
        )
        self.executor = StepExecutor(
            page=self.mock_page,
            profile=self.profile,
            credentials={},
            env={},
            download_dir="/tmp/test_downloads",
            logger=self.mock_logger,
            today_getter=lambda: self.fixed_today,
        )

    def test_load_profile_with_pagination_fields(self) -> None:
        """Verify that pagination fields are parsed properly from YAML profile."""
        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, "pagination_bank.yaml")
        content = (
            "bank: 'santander-es'\n"
            "url: 'https://example.com'\n"
            "steps:\n"
            "  - action: 'load_until_date'\n"
            "    selector: 'san-action-link'\n"
            "    has_text: 'Ver más movimientos'\n"
            "    item_selector: 'san-transaction-list-item'\n"
            "    date_selector: 'san-transaction-list-header > h4'\n"
            "    days_past: 100\n"
            "    seconds: 2.0\n"
            "    max_clicks: 15\n"
        )
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        profile = load_profile(temp_dir, "pagination_bank")
        import shutil

        shutil.rmtree(temp_dir)

        self.assertEqual(len(profile.steps), 1)
        step = profile.steps[0]
        self.assertEqual(step.action, "load_until_date")
        self.assertEqual(step.selector, "san-action-link")
        self.assertEqual(step.has_text, "Ver más movimientos")
        self.assertEqual(step.item_selector, "san-transaction-list-item")
        self.assertEqual(step.date_selector, "san-transaction-list-header > h4")
        self.assertEqual(step.days_past, 100)
        self.assertEqual(step.seconds, 2.0)
        self.assertEqual(step.max_clicks, 15)

    def test_format_step_details_load_until_date(self) -> None:
        """Verify string formatting of load_until_date step."""
        step = Step(
            action="load_until_date",
            selector="san-action-link",
            date_selector="san-transaction-list-header > h4",
            days_past=90,
        )
        details = self.executor._format_step_details(step)
        expected = "selector='san-action-link' date_selector='san-transaction-list-header > h4' days_past=90"
        self.assertEqual(details, expected)

    def test_load_until_date_missing_selector_raises_error(self) -> None:
        """Verify error raised when selector is missing in load_until_date step."""
        step = Step(action="load_until_date", date_selector="h4")
        with self.assertRaises(BrowserAutomationError):
            self.executor.execute_step(step)

    def test_load_until_date_missing_date_selector_raises_error(self) -> None:
        """Verify error raised when date_selector is missing in load_until_date step."""
        step = Step(action="load_until_date", selector="san-action-link")
        with self.assertRaises(BrowserAutomationError):
            self.executor.execute_step(step)

    def test_has_reached_target_date_none_date_selector(self) -> None:
        """Verify _has_reached_target_date returns False when date_selector is None."""
        step = Step(action="load_until_date")
        result = self.executor._has_reached_target_date(step, self.fixed_today)
        self.assertFalse(result)

    def test_load_until_date_target_already_reached(self) -> None:
        """Verify that no clicks are performed if target date is already present."""
        mock_headers_locator = MagicMock(spec=Locator)
        # 100 days before 2026-10-04 is ~2026-06-26. 2026-01-15 is older than 100 days.
        mock_headers_locator.all_text_contents.return_value = ["15/01/2026"]
        self.mock_page.locator.return_value = mock_headers_locator

        step = Step(
            action="load_until_date",
            selector="san-action-link",
            date_selector="san-transaction-list-header > h4",
            days_past=100,
        )
        result = self.executor.execute_step(step)

        self.assertIsNone(result)
        self.assertEqual(
            self.mock_page.wait_for_selector.call_args_list,
            [call("san-transaction-list-header > h4", state="visible", timeout=10000.0)],
        )
        self.assertEqual(mock_headers_locator.click.call_args_list, [])

    def test_load_until_date_button_not_visible_stops_early(self) -> None:
        """Verify that loop stops if load more button is not visible."""
        mock_headers_locator = MagicMock(spec=Locator)
        mock_headers_locator.all_text_contents.return_value = ["03/10/2026"]

        mock_button_locator = MagicMock(spec=Locator)
        mock_button_locator.is_visible.return_value = False

        def locator_side_effect(selector: str, has_text: str | None = None) -> MagicMock:
            if selector == "san-transaction-list-header > h4":
                return mock_headers_locator
            return mock_button_locator

        self.mock_page.locator.side_effect = locator_side_effect

        step = Step(
            action="load_until_date",
            selector="san-action-link",
            date_selector="san-transaction-list-header > h4",
            days_past=100,
        )
        result = self.executor.execute_step(step)

        self.assertIsNone(result)
        self.assertEqual(mock_button_locator.click.call_args_list, [])

    def test_load_until_date_loops_and_stops_when_date_reached(self) -> None:
        """Verify pagination clicking button and waiting until target date is reached."""
        mock_headers_locator = MagicMock(spec=Locator)
        mock_headers_locator.all_text_contents.side_effect = [
            ["03/10/2026"],  # First iteration check: not reached
            ["15/01/2026"],  # Second iteration check: reached!
        ]

        mock_button_locator = MagicMock(spec=Locator)
        mock_button_locator.is_visible.return_value = True

        mock_items_locator = MagicMock(spec=Locator)
        mock_items_locator.count.return_value = 10

        def locator_side_effect(selector: str, has_text: str | None = None) -> MagicMock:
            if selector == "san-transaction-list-header > h4":
                return mock_headers_locator
            if selector == "san-action-link":
                return mock_button_locator
            return mock_items_locator

        self.mock_page.locator.side_effect = locator_side_effect

        step = Step(
            action="load_until_date",
            selector="san-action-link",
            item_selector="san-transaction-list-item",
            date_selector="san-transaction-list-header > h4",
            days_past=100,
            seconds=0.5,
        )
        result = self.executor.execute_step(step)

        self.assertIsNone(result)
        self.assertEqual(mock_button_locator.click.call_args_list, [call(timeout=10000.0)])
        self.assertEqual(
            self.mock_page.wait_for_function.call_args_list,
            [call("document.querySelectorAll('san-transaction-list-item').length > 10", timeout=10000.0)],
        )
        self.assertEqual(self.mock_page.wait_for_timeout.call_args_list, [call(500.0)])

    def test_load_until_date_item_timeout_logged_gracefully(self) -> None:
        """Verify that PlaywrightTimeoutError in wait_for_function is caught and logged."""
        mock_headers_locator = MagicMock(spec=Locator)
        mock_headers_locator.all_text_contents.side_effect = [
            ["03/10/2026"],
            ["15/01/2026"],
        ]

        mock_button_locator = MagicMock(spec=Locator)
        mock_button_locator.is_visible.return_value = True

        mock_items_locator = MagicMock(spec=Locator)
        mock_items_locator.count.return_value = 5

        def locator_side_effect(selector: str, has_text: str | None = None) -> MagicMock:
            if selector == "san-transaction-list-header > h4":
                return mock_headers_locator
            if selector == "san-action-link":
                return mock_button_locator
            return mock_items_locator

        self.mock_page.locator.side_effect = locator_side_effect
        self.mock_page.wait_for_function.side_effect = PlaywrightTimeoutError("timeout waiting for items")

        step = Step(
            action="load_until_date",
            selector="san-action-link",
            item_selector="san-transaction-list-item",
            date_selector="san-transaction-list-header > h4",
            days_past=100,
            seconds=0.0,
        )
        result = self.executor.execute_step(step)

        self.assertIsNone(result)
        self.assertEqual(mock_button_locator.click.call_args_list, [call(timeout=10000.0)])

    def test_load_until_date_initial_selector_timeout_handled(self) -> None:
        """Verify that timeout on initial wait_for_selector passes gracefully."""
        self.mock_page.wait_for_selector.side_effect = PlaywrightTimeoutError("selector not found")

        mock_headers_locator = MagicMock(spec=Locator)
        mock_headers_locator.all_text_contents.return_value = ["15/01/2026"]
        self.mock_page.locator.return_value = mock_headers_locator

        step = Step(
            action="load_until_date",
            selector="san-action-link",
            date_selector="san-transaction-list-header > h4",
            days_past=100,
        )
        result = self.executor.execute_step(step)
        self.assertIsNone(result)

    def test_load_until_date_max_clicks_reached(self) -> None:
        """Verify that loop stops after reaching max_clicks even if date is not reached."""
        mock_headers_locator = MagicMock(spec=Locator)
        mock_headers_locator.all_text_contents.return_value = ["03/10/2026"]

        mock_button_locator = MagicMock(spec=Locator)
        mock_button_locator.is_visible.return_value = True

        def locator_side_effect(selector: str, has_text: str | None = None) -> MagicMock:
            if selector == "san-transaction-list-header > h4":
                return mock_headers_locator
            return mock_button_locator

        self.mock_page.locator.side_effect = locator_side_effect

        step = Step(
            action="load_until_date",
            selector="san-action-link",
            date_selector="san-transaction-list-header > h4",
            days_past=100,
            max_clicks=2,
            seconds=0.0,
        )
        result = self.executor.execute_step(step)

        self.assertIsNone(result)
        self.assertEqual(
            mock_button_locator.click.call_args_list,
            [call(timeout=10000.0), call(timeout=10000.0)],
        )

    def test_bank_scraper_passes_today_getter_to_executor(self) -> None:
        """Verify that BankScraper injects today_getter into StepExecutor."""
        mock_page = MagicMock(spec=Page)
        mock_download = MagicMock()
        mock_download.suggested_filename = "export.xlsx"
        mock_download_info = MagicMock()
        mock_download_info.value = mock_download

        mock_expect_download = MagicMock()
        mock_expect_download.__enter__.return_value = mock_download_info
        mock_expect_download.__exit__.return_value = None
        mock_page.expect_download.return_value = mock_expect_download

        custom_today = date(2026, 12, 1)
        scraper = BankScraper(
            env={"MY_PASS": "pass123"},
            today_getter=lambda: custom_today,
            logger=MagicMock(),
        )

        test_profile = BankProfile(
            name="dl_profile",
            bank="santander-es",
            url="https://bank.example.com",
            steps=(Step(action="download", selector="#btn"),),
            credentials={"password": MagicMock(env_var="MY_PASS")},
            headless=True,
            timeout_ms=5000.0,
        )

        temp_dir = tempfile.mkdtemp()
        downloaded = scraper.run_steps(page=mock_page, profile=test_profile, download_dir=temp_dir)
        import shutil

        shutil.rmtree(temp_dir)

        self.assertTrue(downloaded.endswith("export.xlsx"))
