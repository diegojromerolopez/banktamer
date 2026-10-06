import argparse
import json
import os
import sys
import tempfile
from typing import TypedDict

from banktamer.ai import AIProviderFactory
from banktamer.analytics import AnalyticsProcessor, MonthReport
from banktamer.categorizer import Categorizer
from banktamer.io import ExcelReader
from banktamer.models import Transaction
from banktamer.report.terminal import print_ai_analysis, print_report
from banktamer.scraper import BankScraper, BrowserAutomationError, ProfileError, load_profile


class ConfigPaths(TypedDict):
    """Paths for configuration files and directories."""

    schemas: str
    rules_dir: str
    config_dir: str
    profiles_dir: str


def resolve_config(args: argparse.Namespace) -> ConfigPaths:
    """Resolve the location of configuration files based on CLI args and defaults."""
    config_dir = args.config_dir or "config"
    schemas_path = args.schemas or os.path.join(config_dir, "schemas.json")
    rules_dir = args.rules_dir or os.path.join(config_dir, "categories")
    profiles_cli = getattr(args, "profiles_dir", None)
    profiles_dir = profiles_cli if isinstance(profiles_cli, str) else os.path.join(config_dir, "profiles")

    # Fallback logic
    if not os.path.exists(schemas_path) and not args.schemas:
        # 1. Try home directory
        home_config = os.path.expanduser("~/.banktamer/config")
        home_schemas = os.path.join(home_config, "schemas.json")

        if os.path.exists(home_schemas):
            return ConfigPaths(
                schemas=home_schemas,
                rules_dir=os.path.join(home_config, "categories"),
                config_dir=home_config,
                profiles_dir=profiles_cli if isinstance(profiles_cli, str) else os.path.join(home_config, "profiles"),
            )

        # 2. Try package internal config
        package_config = os.path.join(os.path.dirname(__file__), "config")
        package_schemas = os.path.join(package_config, "schemas.json")
        if os.path.exists(package_schemas):
            return ConfigPaths(
                schemas=package_schemas,
                rules_dir=os.path.join(package_config, "categories"),
                config_dir=package_config,
                profiles_dir=profiles_cli
                if isinstance(profiles_cli, str)
                else os.path.join(package_config, "profiles"),
            )

    return ConfigPaths(schemas=schemas_path, rules_dir=rules_dir, config_dir=config_dir, profiles_dir=profiles_dir)


def load_rules(rules_dir: str, category: str | None) -> dict[str, list[str]]:
    """Load categorization rules from YAML files."""
    merged_rules: dict[str, list[str]] = {}

    # 1. Load default rules if they exist
    default_rules_path = os.path.join(rules_dir, ".default.yaml")
    if os.path.exists(default_rules_path):
        import yaml

        with open(default_rules_path, "r") as f:
            rules = yaml.safe_load(f)
            if rules:
                merged_rules.update(rules)

    # 2. Load category-specific rules
    if category:
        category_path = os.path.join(rules_dir, f"{category}.yaml")
        if not os.path.exists(category_path):
            raise FileNotFoundError(f"Category file not found: {category_path}")

        import yaml

        with open(category_path, "r") as f:
            rules = yaml.safe_load(f)
            if rules:
                for cat, patterns in rules.items():
                    if cat in merged_rules:
                        merged_rules[cat].extend(patterns)
                    else:
                        merged_rules[cat] = patterns
    return merged_rules


def run_pipeline(args: argparse.Namespace, config: ConfigPaths) -> dict[str, MonthReport]:
    """Execute the data processing pipeline."""
    # 1. Ingestion
    with open(config["schemas"], "r") as schemas_file:
        schemas = json.load(schemas_file)

    reader = ExcelReader(schemas=schemas)
    all_transactions: list[Transaction] = []
    for file_path in args.files:
        transactions = reader.read(args.bank, file_path)
        all_transactions.extend(transactions)

    if not all_transactions:
        print(f"No transactions found for bank '{args.bank}' in the provided files.")
        return {}

    # 2. Categorization
    rules = load_rules(config["rules_dir"], args.category)
    categorizer = Categorizer(rules=rules)
    categorized_txns = categorizer.categorize(all_transactions)

    # 3. Analytics
    processor = AnalyticsProcessor()
    return processor.process(categorized_txns)


def generate_report(args: argparse.Namespace, report_data: dict[str, MonthReport], config: ConfigPaths) -> None:
    """Generate the requested report type."""
    if not report_data:
        return

    if args.report == "pdf":
        from banktamer.report.pdf import PDFReporter

        output_path = args.output or "banktamer_report.pdf"
        reporter = PDFReporter()
        reporter.render(report_data, output_path)
        print(f"Report generated successfully: {output_path}")
    else:
        print_report(report_data)

    # 4. AI Analysis (Optional)
    if args.ai:
        api_key = args.ai_key or os.getenv(f"{args.ai.upper()}_API_KEY")
        if not api_key and args.ai != "ollama":
            print(f"Error: AI provider '{args.ai}' requires an API key (--ai-key or {args.ai.upper()}_API_KEY env).")
            return

        try:
            provider = AIProviderFactory.create(
                provider_name=args.ai, api_key=api_key, model=args.ai_model, base_url=args.ai_url
            )

            print(f"\n--- AI Financial Analysis ({args.ai}) ---")

            # Create a more detailed summary for the AI
            summary_parts = []
            for month, data in report_data.items():
                cat_summary = ", ".join([f"{cat}: {stats.total:.2f}" for cat, stats in data["categories"].items()])
                summary_parts.append(
                    f"Month: {month}\n"
                    f"Income: {data['total_income']:.2f}\n"
                    f"Expenses: {data['total_expenses']:.2f}\n"
                    f"Categories: {cat_summary}"
                )
            summary = "\n\n".join(summary_parts)

            # Load custom prompt from ai_settings.yaml if it exists
            prompt = (
                "You are an expert financial advisor. Analyze these bank transactions and provide:\n"
                "1. A brief summary of spending patterns.\n"
                "2. Specific, actionable money-saving suggestions.\n"
                "3. Any alarming trends or unusual category spikes.\n\n"
                f"Data:\n{summary}"
            )

            settings_path = os.path.join(config["config_dir"], "ai_settings.yaml")
            if os.path.exists(settings_path):
                import yaml

                try:
                    with open(settings_path, "r") as f:
                        settings = yaml.safe_load(f.read())
                        template = settings.get("prompt_templates", {}).get("financial_analysis")
                        if template:
                            if "{summary}" in template:
                                prompt = template.replace("{summary}", summary)
                            else:
                                prompt = f"{template}\n\nData:\n{summary}"
                except Exception:
                    pass

            response = provider.ask(prompt)
            print_ai_analysis(args.ai, response)
        except Exception as e:
            print(f"AI Analysis failed: {e}")


def load_environment(env_file: str | None = None) -> None:
    """Load environment variables from specified or default .env files."""
    from dotenv import load_dotenv

    if isinstance(env_file, str) and env_file:
        load_dotenv(dotenv_path=env_file, override=False)
        return

    if env_file is not None:
        return

    # 1. Local .env in current directory
    if os.path.exists(".env"):
        load_dotenv(dotenv_path=".env", override=False)

    # 2. Home directory ~/.banktamer/.env
    home_env = os.path.expanduser("~/.banktamer/.env")
    if os.path.exists(home_env):
        load_dotenv(dotenv_path=home_env, override=False)


def handle_profile_download(
    args: argparse.Namespace,
    config: ConfigPaths,
    scraper: BankScraper | None = None,
) -> None:
    """Download transactions using a bank profile if specified."""
    profile_name = getattr(args, "profile", None)
    if not profile_name or not isinstance(profile_name, str):
        return

    profiles_dir = config.get("profiles_dir", os.path.join(config.get("config_dir", "config"), "profiles"))
    profile = load_profile(profiles_dir, profile_name)
    if not args.bank:
        args.bank = profile.bank

    if not args.files:
        download_dir = getattr(args, "download_dir", None) or tempfile.mkdtemp(prefix="banktamer_")
        headless_val = getattr(args, "headless", None)
        active_scraper = scraper or BankScraper()
        downloaded_file = active_scraper.download(profile=profile, download_dir=download_dir, headless=headless_val)
        args.files = [downloaded_file]


def main() -> None:
    """Entry point for the BankTamer CLI."""
    parser = argparse.ArgumentParser(description="BankTamer CLI - Process bank transaction files.")
    parser.add_argument("--bank", required=False, help="Bank name (e.g., santander-es)")
    parser.add_argument("--category", required=False, help="Category file name (e.g., common)")
    parser.add_argument("--files", required=False, nargs="+", help="Path to the XLS/XLSX file(s)")
    parser.add_argument("--profile", required=False, help="Bank profile name for automated download (e.g. santander)")
    parser.add_argument("--profiles-dir", help="Path to bank profiles directory")
    parser.add_argument("--download-dir", help="Directory where downloaded files are saved")
    parser.add_argument(
        "--headless", action=argparse.BooleanOptionalAction, default=None, help="Run browser in headless mode"
    )
    parser.add_argument("--env-file", help="Path to .env file (default: ./.env or ~/.banktamer/.env)")
    parser.add_argument("--config-dir", help="Base directory for configurations (default: ./config)")
    parser.add_argument("--schemas", help="Path to schemas.json")
    parser.add_argument("--rules-dir", help="Path to categories rules directory")
    parser.add_argument(
        "--report", choices=["terminal", "pdf"], default="terminal", help="Report format (default: terminal)"
    )
    parser.add_argument("--output", help="Output path for PDF report (default: banktamer_report.pdf)")
    parser.add_argument(
        "--ai", choices=["openai", "anthropic", "gemini", "huggingface", "ollama"], help="AI provider for analysis"
    )
    parser.add_argument("--ai-key", help="API key for the AI provider (fallbacks to environment variable)")
    parser.add_argument("--ai-url", help="Base URL for the AI provider (e.g. for remote Ollama)")
    parser.add_argument("--ai-model", help="Override default model for the AI provider")

    args = parser.parse_args()
    load_environment(getattr(args, "env_file", None))

    if not args.bank and not args.profile:
        parser.error("one of the arguments --bank or --profile is required")
    if not args.files and not args.profile:
        parser.error("one of the arguments --files or --profile is required")

    config = resolve_config(args)

    try:
        handle_profile_download(args, config)
        report_data = run_pipeline(args, config)
        generate_report(args, report_data, config)
    except (ValueError, FileNotFoundError, json.JSONDecodeError, ProfileError, BrowserAutomationError) as e:
        print(f"Configuration or Data Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
