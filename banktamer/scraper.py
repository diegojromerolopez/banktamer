"""Automated bank website scraper using Playwright."""

from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
import os
import re
from typing import Literal
import yaml
from playwright.sync_api import (
    Error as PlaywrightError,
    Locator,
    Page,
    Playwright,
    TimeoutError as PlaywrightTimeoutError,
    sync_playwright,
)


class ProfileError(Exception):
    """Base exception for bank profile errors."""


class ProfileNotFoundError(ProfileError):
    """Raised when a bank profile file cannot be found."""


class ProfileConfigError(ProfileError):
    """Raised when a bank profile definition is invalid."""


class MissingCredentialError(ProfileError):
    """Raised when an environment variable for credentials is missing."""


class BrowserAutomationError(Exception):
    """Raised when browser automation fails during execution."""


@dataclass(frozen=True)
class CredentialConfig:
    """Configuration for a required credential."""

    env_var: str


@dataclass(frozen=True)
class Step:
    """Representation of an automation step in a bank profile."""

    action: str
    url: str | None = None
    selector: str | None = None
    value: str | None = None
    has_text: str | None = None
    first: bool = False
    state: Literal["attached", "detached", "visible", "hidden"] | None = None
    seconds: float | None = None
    timeout_ms: float | None = None


@dataclass(frozen=True)
class BankProfile:
    """Representation of a bank automation profile."""

    name: str
    bank: str
    url: str
    steps: tuple[Step, ...]
    credentials: dict[str, CredentialConfig]
    headless: bool = True
    timeout_ms: float = 30000.0


def load_profile(profiles_dir: str, profile_name: str) -> BankProfile:
    """Load and validate a bank automation profile from YAML."""
    yaml_path = os.path.join(profiles_dir, f"{profile_name}.yaml")
    yml_path = os.path.join(profiles_dir, f"{profile_name}.yml")

    target_path = yaml_path if os.path.exists(yaml_path) else yml_path
    if not os.path.exists(target_path):
        raise ProfileNotFoundError(f"Profile file not found for '{profile_name}' in '{profiles_dir}'")

    with open(target_path, "r", encoding="utf-8") as profile_file:
        data = yaml.safe_load(profile_file)

    if not isinstance(data, dict):
        raise ProfileConfigError(f"Profile '{profile_name}' must be a YAML mapping.")

    bank = data.get("bank")
    if not bank or not isinstance(bank, str):
        raise ProfileConfigError(f"Profile '{profile_name}' missing required 'bank' string field.")

    raw_steps = data.get("steps")
    if not isinstance(raw_steps, list) or not raw_steps:
        raise ProfileConfigError(f"Profile '{profile_name}' must define a non-empty 'steps' list.")

    url = str(data.get("url", ""))
    headless = bool(data.get("headless", True))
    timeout_ms = float(data.get("timeout_ms", 30000.0))

    credentials: dict[str, CredentialConfig] = {}
    raw_creds = data.get("credentials", {})
    if isinstance(raw_creds, dict):
        for key, val in raw_creds.items():
            if isinstance(val, dict) and "env" in val:
                credentials[key] = CredentialConfig(env_var=str(val["env"]))
            elif isinstance(val, str):
                credentials[key] = CredentialConfig(env_var=val)

    steps_list: list[Step] = []
    for step_data in raw_steps:
        if not isinstance(step_data, dict):
            raise ProfileConfigError(f"Step in profile '{profile_name}' must be a mapping.")
        action = step_data.get("action")
        if not action or not isinstance(action, str):
            raise ProfileConfigError(f"Step in profile '{profile_name}' missing required 'action'.")

        raw_state = step_data.get("state")
        valid_state: Literal["attached", "detached", "visible", "hidden"] | None = (
            raw_state if raw_state in ("attached", "detached", "visible", "hidden") else None
        )

        step = Step(
            action=action,
            url=step_data.get("url"),
            selector=step_data.get("selector"),
            value=step_data.get("value"),
            has_text=step_data.get("has_text"),
            first=bool(step_data.get("first", False)),
            state=valid_state,
            seconds=float(step_data["seconds"]) if "seconds" in step_data else None,
            timeout_ms=float(step_data["timeout_ms"]) if "timeout_ms" in step_data else None,
        )
        steps_list.append(step)

    return BankProfile(
        name=profile_name,
        bank=bank,
        url=url,
        steps=tuple(steps_list),
        credentials=credentials,
        headless=headless,
        timeout_ms=timeout_ms,
    )


def resolve_placeholders(text: str, credentials_values: dict[str, str], env: dict[str, str]) -> str:
    """Resolve ${placeholder} tokens using credentials and environment variables."""

    def _replacer(match: re.Match[str]) -> str:
        key = match.group(1)
        if key in credentials_values:
            return credentials_values[key]
        if key in env:
            return env[key]
        raise MissingCredentialError(f"Unknown placeholder '${{{key}}}' could not be resolved.")

    return re.sub(r"\$\{([A-Za-z0-9_]+)\}", _replacer, text)


class StepExecutor:
    """Execute automation steps on a Playwright page."""

    def __init__(
        self,
        page: Page,
        profile: BankProfile,
        credentials: dict[str, str],
        env: dict[str, str],
        download_dir: str,
        logger: Callable[[str], None] = print,
    ) -> None:
        """Initialize the executor with page context and configuration."""
        self._page = page
        self._profile = profile
        self._credentials = credentials
        self._env = env
        self._download_dir = download_dir
        self._logger = logger

    def _format_step_details(self, step: Step) -> str:
        """Format step details for console logging while masking sensitive values."""
        if step.action == "navigate":
            return f"url='{step.url or self._profile.url}'"
        if step.action == "fill":
            raw_val = step.value or ""
            is_secret = any(
                term in (step.selector or "").lower() or term in raw_val.lower() for term in ("pass", "secret", "token")
            )
            val_display = "********" if is_secret else raw_val
            return f"selector='{step.selector}' value='{val_display}'"
        if step.action == "click":
            details = f"selector='{step.selector}'"
            if step.has_text:
                details += f" has_text='{step.has_text}'"
            if step.first:
                details += " (first)"
            return details
        if step.action == "wait_for_url":
            return f"url='{step.url}'"
        if step.action == "wait_for_selector":
            return f"selector='{step.selector}' state='{step.state or 'visible'}'"
        if step.action == "wait":
            sec = step.seconds if step.seconds is not None else 1.0
            return f"{sec}s"
        if step.action == "download":
            return f"selector='{step.selector}' (waiting for file download)"
        return ""

    def _get_locator(self, step: Step) -> Locator:
        """Get the configured locator for a step."""
        selector = step.selector or ""
        locator = (
            self._page.locator(selector, has_text=step.has_text)
            if step.has_text is not None
            else self._page.locator(selector)
        )
        if step.first:
            return locator.first
        return locator

    def execute_step(self, step: Step, step_idx: int = 1, total_steps: int = 1) -> str | None:
        """Execute a single step and return the downloaded file path if this was a download step."""
        details = self._format_step_details(step)
        self._logger(f"[{step_idx}/{total_steps}] {step.action}: {details}")

        effective_timeout = step.timeout_ms if step.timeout_ms is not None else self._profile.timeout_ms

        try:
            if step.action == "navigate":
                target_url = step.url or self._profile.url
                if not target_url:
                    raise BrowserAutomationError("Navigate step requires a URL.")
                self._page.goto(target_url, timeout=effective_timeout)
                return None

            if step.action == "fill":
                if not step.selector:
                    raise BrowserAutomationError("Fill step requires a selector.")
                raw_value = step.value or ""
                resolved_value = resolve_placeholders(raw_value, self._credentials, self._env)
                self._page.locator(step.selector).fill(resolved_value, timeout=effective_timeout)
                return None

            if step.action == "click":
                if not step.selector:
                    raise BrowserAutomationError("Click step requires a selector.")
                locator = self._get_locator(step)
                locator.click(timeout=effective_timeout)
                return None

            if step.action == "wait_for_url":
                if not step.url:
                    raise BrowserAutomationError("Wait_for_url step requires a URL.")
                self._page.wait_for_url(step.url, timeout=effective_timeout)
                return None

            if step.action == "wait_for_selector":
                if not step.selector:
                    raise BrowserAutomationError("Wait_for_selector step requires a selector.")
                target_state = step.state or "visible"
                self._page.wait_for_selector(step.selector, state=target_state, timeout=effective_timeout)
                return None

            if step.action == "wait":
                wait_seconds = step.seconds if step.seconds is not None else 1.0
                self._page.wait_for_timeout(wait_seconds * 1000.0)
                return None

            if step.action == "download":
                if not step.selector:
                    raise BrowserAutomationError("Download step requires a selector.")
                locator = self._get_locator(step)
                with self._page.expect_download(timeout=effective_timeout) as download_info:
                    locator.click(timeout=effective_timeout)
                download = download_info.value
                filename = download.suggested_filename
                os.makedirs(self._download_dir, exist_ok=True)
                target_path = os.path.join(self._download_dir, filename)
                download.save_as(target_path)
                return target_path

            raise BrowserAutomationError(f"Unsupported action '{step.action}'.")
        except (PlaywrightTimeoutError, PlaywrightError) as e:
            current_url = getattr(self._page, "url", "unknown")
            screenshot_notice = ""
            try:
                os.makedirs(self._download_dir, exist_ok=True)
                screenshot_path = os.path.join(self._download_dir, "automation_error.png")
                self._page.screenshot(path=screenshot_path)
                screenshot_notice = f" (Saved debug screenshot to {screenshot_path})"
            except Exception:
                pass
            raise BrowserAutomationError(
                f"Browser step '{step.action}' failed on '{step.selector or step.url}'. "
                f"Current page URL: {current_url}. Error: {e}{screenshot_notice}"
            ) from e


def default_prompt_getter(name: str, env_var: str) -> str:
    """Prompt the user for a credential from terminal input."""
    import getpass
    import sys

    if not sys.stdin.isatty():
        return ""

    is_secret = any(term in name.lower() or term in env_var.lower() for term in ("pass", "secret", "token", "key"))
    prompt_text = f"Enter {name} ({env_var}): "
    try:
        if is_secret:
            return getpass.getpass(prompt_text)
        return input(prompt_text)
    except (EOFError, OSError):
        return ""


class BankScraper:
    """Automate bank website interaction to download transaction exports."""

    def __init__(
        self,
        env: dict[str, str] | None = None,
        playwright_launcher: Callable[[], AbstractContextManager[Playwright]] | None = None,
        logger: Callable[[str], None] = print,
        prompt_getter: Callable[[str, str], str] | None = None,
    ) -> None:
        """Initialize the scraper with environment and launcher dependencies."""
        self._env = env if env is not None else dict(os.environ)
        self._playwright_launcher = playwright_launcher or sync_playwright
        self._logger = logger
        self._prompt_getter = prompt_getter or default_prompt_getter

    def _resolve_credentials(self, profile: BankProfile) -> dict[str, str]:
        """Verify and resolve required credentials from the environment or user prompt."""
        resolved: dict[str, str] = {}
        for name, config in profile.credentials.items():
            val = self._env.get(config.env_var)
            if not val:
                val = self._prompt_getter(name, config.env_var)
            if not val:
                raise MissingCredentialError(f"Missing required credential '{name}' ({config.env_var})")
            resolved[name] = val
        return resolved

    def run_steps(self, page: Page, profile: BankProfile, download_dir: str) -> str:
        """Execute all steps in profile on the provided page and return downloaded file path."""
        credentials = self._resolve_credentials(profile)
        executor = StepExecutor(
            page=page,
            profile=profile,
            credentials=credentials,
            env=self._env,
            download_dir=download_dir,
            logger=self._logger,
        )
        total = len(profile.steps)
        self._logger(f"Running profile '{profile.name}' ({total} steps) for bank '{profile.bank}'...")
        downloaded_file: str | None = None
        for idx, step in enumerate(profile.steps, start=1):
            result = executor.execute_step(step, step_idx=idx, total_steps=total)
            if result:
                downloaded_file = result

        if not downloaded_file:
            raise BrowserAutomationError(f"Profile '{profile.name}' did not download any transaction file.")

        self._logger(f"Successfully downloaded: {downloaded_file}")
        return downloaded_file

    def download(self, profile: BankProfile, download_dir: str, headless: bool | None = None) -> str:
        """Launch browser, execute steps, and return downloaded file path."""
        effective_headless = headless if headless is not None else profile.headless
        with self._playwright_launcher() as playwright:
            browser = playwright.chromium.launch(headless=effective_headless)
            try:
                context = browser.new_context(accept_downloads=True)
                try:
                    page = context.new_page()
                    return self.run_steps(page=page, profile=profile, download_dir=download_dir)
                finally:
                    context.close()
            finally:
                browser.close()
