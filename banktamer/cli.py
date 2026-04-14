import argparse
import os
import sys
from banktamer.io import ExcelReader
from banktamer.categorizer import Categorizer
from banktamer.analytics import AnalyticsProcessor
from banktamer.report.terminal import print_report


def main() -> None:
    parser = argparse.ArgumentParser(description="BankTamer CLI - Process bank transaction files.")
    parser.add_argument("--bank", required=True, help="Bank name (e.g., santander)")
    parser.add_argument("--category", required=False, help="Category file name (e.g., common)")
    parser.add_argument("--files", required=True, nargs="+", help="Path to the XLS/XLSX file(s)")
    parser.add_argument("--config-dir", help="Base directory for configurations (default: ./config)")
    parser.add_argument("--schemas", help="Path to schemas.json")
    parser.add_argument("--rules-dir", help="Path to categories rules directory")
    parser.add_argument("--report", choices=["terminal", "pdf"], default="terminal", help="Report format (default: terminal)")
    parser.add_argument("--output", help="Output path for PDF report (default: banktamer_report.pdf)")

    args = parser.parse_args()

    # Resolve configuration paths
    config_dir = args.config_dir or "config"
    schemas_path = args.schemas or os.path.join(config_dir, "schemas.json")
    rules_dir = args.rules_dir or os.path.join(config_dir, "categories")

    # Fallback logic
    if not os.path.exists(schemas_path) and not args.schemas:
        # 1. Try home directory
        home_config = os.path.expanduser("~/.banktamer/config")
        home_schemas = os.path.join(home_config, "schemas.json")

        if os.path.exists(home_schemas):
            config_dir = home_config
            schemas_path = home_schemas
            rules_dir = os.path.join(home_config, "categories")
        else:
            # 2. Try package internal config
            package_config = os.path.join(os.path.dirname(__file__), "config")
            package_schemas = os.path.join(package_config, "schemas.json")
            if os.path.exists(package_schemas):
                config_dir = package_config
                schemas_path = package_schemas
                rules_dir = os.path.join(package_config, "categories")

    try:
        # 1. Ingestion
        reader = ExcelReader(schemas_path)
        all_transactions = []
        for file_path in args.files:
            transactions = reader.read(args.bank, file_path)
            all_transactions.extend(transactions)

        if not all_transactions:
            print(f"No transactions found for bank '{args.bank}' in the provided files.")
            return

        # 2. Categorization
        categorizer = Categorizer(args.category, rules_dir=rules_dir)
        categorized_txns = categorizer.categorize(all_transactions)

        # 3. Analytics
        processor = AnalyticsProcessor()
        report_data = processor.process(categorized_txns)

        # 4. Report Generation
        if args.report == "pdf":
            from banktamer.report.pdf import PDFReporter
            output_path = args.output or "banktamer_report.pdf"
            reporter = PDFReporter()
            reporter.render(report_data, output_path)
            print(f"Report generated successfully: {output_path}")
        else:
            print_report(report_data)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
