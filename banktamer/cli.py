import argparse
import json
import os
import sys
from typing import TypedDict

from banktamer.analytics import AnalyticsProcessor, MonthReport
from banktamer.categorizer import Categorizer
from banktamer.io import ExcelReader
from banktamer.models import Transaction
from banktamer.report.terminal import print_report


class ConfigPaths(TypedDict):
    """Paths for configuration files and directories."""

    schemas: str
    rules_dir: str


def resolve_config(args: argparse.Namespace) -> ConfigPaths:
    """Resolve the location of configuration files based on CLI args and defaults."""
    config_dir = args.config_dir or "config"
    schemas_path = args.schemas or os.path.join(config_dir, "schemas.json")
    rules_dir = args.rules_dir or os.path.join(config_dir, "categories")

    # Fallback logic
    if not os.path.exists(schemas_path) and not args.schemas:
        # 1. Try home directory
        home_config = os.path.expanduser("~/.banktamer/config")
        home_schemas = os.path.join(home_config, "schemas.json")

        if os.path.exists(home_schemas):
            return ConfigPaths(schemas=home_schemas, rules_dir=os.path.join(home_config, "categories"))

        # 2. Try package internal config
        package_config = os.path.join(os.path.dirname(__file__), "config")
        package_schemas = os.path.join(package_config, "schemas.json")
        if os.path.exists(package_schemas):
            return ConfigPaths(schemas=package_schemas, rules_dir=os.path.join(package_config, "categories"))

    return ConfigPaths(schemas=schemas_path, rules_dir=rules_dir)


def load_rules(rules_dir: str, category: str | None) -> dict[str, list[str]]:
    """Load and merge rules from .default.yaml and the specified category file."""
    merged_rules: dict[str, list[str]] = {}
    base_dir = os.path.abspath(rules_dir)

    # 1. Load .default if present
    default_path = os.path.join(base_dir, ".default.yaml")
    if os.path.exists(default_path):
        with open(default_path, "r") as default_file:
            import yaml  # Import here to avoid global dependency if not needed

            default_rules = yaml.safe_load(default_file)
            if default_rules:
                merged_rules.update(default_rules)

    # 2. Load specified category if present and not .default
    if category and category != ".default":
        spec_path = os.path.join(base_dir, f"{category}.yaml")
        if os.path.exists(spec_path):
            with open(spec_path, "r") as spec_file:
                import yaml

                spec_rules = yaml.safe_load(spec_file)
                if spec_rules:
                    for cat, patterns in spec_rules.items():
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


def generate_report(args: argparse.Namespace, report_data: dict[str, MonthReport]) -> None:
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


def main() -> None:
    """Entry point for the BankTamer CLI."""
    parser = argparse.ArgumentParser(description="BankTamer CLI - Process bank transaction files.")
    parser.add_argument("--bank", required=True, help="Bank name (e.g., santander)")
    parser.add_argument("--category", required=False, help="Category file name (e.g., common)")
    parser.add_argument("--files", required=True, nargs="+", help="Path to the XLS/XLSX file(s)")
    parser.add_argument("--config-dir", help="Base directory for configurations (default: ./config)")
    parser.add_argument("--schemas", help="Path to schemas.json")
    parser.add_argument("--rules-dir", help="Path to categories rules directory")
    parser.add_argument(
        "--report", choices=["terminal", "pdf"], default="terminal", help="Report format (default: terminal)"
    )
    parser.add_argument("--output", help="Output path for PDF report (default: banktamer_report.pdf)")

    args = parser.parse_args()
    config = resolve_config(args)

    try:
        report_data = run_pipeline(args, config)
        generate_report(args, report_data)
    except (ValueError, FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Configuration or Data Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
