import argparse
import os
import sys
from banktamer.io import ExcelReader
from banktamer.categorizer import Categorizer
from banktamer.analytics import AnalyticsProcessor, MonthReport


def main() -> None:
    parser = argparse.ArgumentParser(description="BankTamer CLI - Process bank transaction files.")
    parser.add_argument("--bank", required=True, help="Bank name (e.g., santander)")
    parser.add_argument("--category", required=False, help="Category file name (e.g., common)")
    parser.add_argument("--files", required=True, nargs="+", help="Path to the XLS/XLSX file(s)")
    parser.add_argument("--config-dir", help="Base directory for configurations (default: ./config)")
    parser.add_argument("--schemas", help="Path to schemas.json")
    parser.add_argument("--rules-dir", help="Path to categories rules directory")

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
        print_report(report_data)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def print_report(report_data: dict[str, MonthReport]) -> None:
    for month, data in report_data.items():
        print(f"\n{'=' * 50}")
        print(f" REPORT FOR {month}")
        print(f"{'=' * 50}")

        print("\nCATEGORIZED BREAKDOWN:")
        print(f"{'Category':<20} | {'Total':>10} | {'%':>6} | {'Max Transaction'}")
        print("-" * 85)

        # Sort categories by total absolute amount
        sorted_categories = sorted(data["categories"].items(), key=lambda x: abs(x[1].total), reverse=True)

        for cat, stats in sorted_categories:
            percentage = 0.0
            if stats.total > 0 and data["total_income"] > 0:
                percentage = (stats.total / data["total_income"]) * 100
            elif stats.total < 0 and data["total_expenses"] < 0:
                percentage = (stats.total / data["total_expenses"]) * 100

            max_txn_str = ""
            if stats.max_txn:
                max_txn_str = f"{stats.max_txn.amount:>10.2f} ({stats.max_txn.concept})"
            print(f"{cat:<20} | {stats.total:>10.2f} | {percentage:>5.1f}% | {max_txn_str}")

        print("\nMONTHLY SUMMARY:")
        print(f"Total Income:   {data['total_income']:>10.2f}")
        print(f"Total Expenses: {data['total_expenses']:>10.2f}")
        print(f"Net Balance:    {data['total_income'] + data['total_expenses']:>10.2f}")

        if data["unknown_concepts"]:
            print("\nUNKNOWN EXPENSE CONCEPTS:")
            for date, amount, concept in sorted(data["unknown_concepts"], key=lambda x: x[0]):
                print(f"- {date} | {amount:>10.2f} | {concept}")


if __name__ == "__main__":
    main()
