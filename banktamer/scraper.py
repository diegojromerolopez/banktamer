"""Automated bank website scraper using Playwright."""

from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
import os
import re
from typing import Literal
import yaml
from playwright.sync_api import Locator, Page, Playwright, sync_playwright


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
    ) -> None:
        """Initialize the executor with page context and configuration."""
        self._page = page
        self._profile = profile
        self._credentials = credentials
        self._env = env
        self._download_dir = download_dir

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

    def execute_step(self, step: Step) -> str | None:
        """Execute a single step and return the downloaded file path if this was a download step."""
        effective_timeout = step.timeout_ms if step.timeout_ms is not None else self._profile.timeout_ms

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


class BankScraper:
    """Automate bank website interaction to download transaction exports."""

    def __init__(
        self,
        env: dict[str, str] | None = None,
        playwright_launcher: Callable[[], AbstractContextManager[Playwright]] | None = None,
    ) -> None:
        """Initialize the scraper with environment and launcher dependencies."""
        self._env = env if env is not None else dict(os.environ)
        self._playwright_launcher = playwright_launcher or sync_playwright

    def _resolve_credentials(self, profile: BankProfile) -> dict[str, str]:
        """Verify and resolve required credentials from the environment."""
        resolved: dict[str, str] = {}
        for name, config in profile.credentials.items():
            val = self._env.get(config.env_var)
            if not val:
                raise MissingCredentialError(
                    f"Missing required environment variable '{config.env_var}' for credential '{name}'"
                )
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
        )
        downloaded_file: str | None = None
        for step in profile.steps:
            result = executor.execute_step(step)
            if result:
                downloaded_file = result

        if not downloaded_file:
            raise BrowserAutomationError(f"Profile '{profile.name}' did not download any transaction file.")

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
