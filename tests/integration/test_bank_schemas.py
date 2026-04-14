import unittest
import os
import shutil
import tempfile
import json
import datetime
import pandas as pd
from typing import Any
from io import StringIO
from contextlib import redirect_stdout
from banktamer.cli import main


class TestAllBanksIntegration(unittest.TestCase):
    """Integration test suite to verify all banks in schemas.json work correctly."""

    def setUp(self) -> None:
        self.test_dir = tempfile.mkdtemp()
        self.old_cwd = os.getcwd()
        os.chdir(self.test_dir)
        os.makedirs("config/categories")

        # Copy real schemas
        real_schemas_path = os.path.join(self.old_cwd, "banktamer/config/schemas.json")
        with open(real_schemas_path, "r") as f:
            self.schemas = json.load(f)
        shutil.copy(real_schemas_path, "config/schemas.json")

        # Create a simple category file
        with open("config/categories/common.yaml", "w") as f:
            f.write("Grocery shopping:\n  - 'MERCADONA'\nOnline shopping:\n  - 'AMAZON'\n")

    def tearDown(self) -> None:
        os.chdir(self.old_cwd)
        shutil.rmtree(self.test_dir)

    def test_all_bank_schemas(self) -> None:
        """Iterate through all bank schemas and run a basic integration test for each."""
        # Add special banks for coverage
        schemas_to_test = self.schemas.copy()
        # 1. Bank without date_format (to cover line 61)
        schemas_to_test["_coverage_no_fmt"] = {
            "date_col": "Date",
            "concept_col": "Concept",
            "amount_col": "Amount",
            "skiprows": 0,
        }
        # 2. Bank that will fail (to cover lines 109-113)
        schemas_to_test["_coverage_broken"] = {
            "date_col": "Date",
            "concept_col": "Concept",
            "amount_col": "Amount",
            "date_format": "%Y-%m-%d",
            "skiprows": 0,
        }
        # 3. Bank that will fail unexpectedly (to cover line 151 path)
        schemas_to_test["_coverage_fail_unexpected"] = {
            "date_col": "Date",
            "concept_col": "Concept",
            "amount_col": "Amount",
            "date_format": "%Y-%m-%d",
            "skiprows": 0,
        }

        # Update schemas.json on disk to include these new banks
        with open("config/schemas.json", "w") as f:
            json.dump(schemas_to_test, f)

        for bank_name, schema in schemas_to_test.items():
            with self.subTest(bank=bank_name):
                # Prepare data
                if bank_name.startswith("_coverage_broken") or bank_name == "_coverage_fail_unexpected":
                    # Use non-existent file to trigger FileNotFoundError and sys.exit(1)
                    excel_path = "non_existent_file_for_coverage.xlsx"
                else:
                    skiprows = schema.get("skiprows", 0)
                # Resolve col names for the dummy file (just use the first if list)
                date_col = schema["date_col"]
                if isinstance(date_col, list):
                    date_col = date_col[0]

                concept_col = schema["concept_col"]
                if isinstance(concept_col, list):
                    concept_col = concept_col[0]

                # Prepare row values
                date_val = datetime.date(2024, 1, 1)
                fmt = schema.get("date_format")
                if isinstance(fmt, list):
                    fmt = fmt[0]

                if fmt:
                    date_val_str = date_val.strftime(fmt)
                else:
                    date_val_str = date_val.isoformat()

                concept_val = "MERCADONA SUPER"

                # Create a list of lists for to_excel
                # Row 0 to skiprows-1 are dummy
                data_rows: list[list[Any]] = []
                for _ in range(skiprows):
                    data_rows.append(["DUMMY"] * 10)

                # Headers row
                headers = [date_col, concept_col]
                if "amount_col" in schema:
                    a_col = schema["amount_col"]
                    if isinstance(a_col, list):
                        a_col = a_col[0]
                    headers.append(a_col)
                    amount_val = -50.0
                    row_data = [date_val_str, concept_val, amount_val]
                else:
                    i_col = schema["income_col"]
                    if isinstance(i_col, list):
                        i_col = i_col[0]
                    e_col = schema["expense_col"]
                    if isinstance(e_col, list):
                        e_col = e_col[0]
                    headers.extend([i_col, e_col])
                    row_data = [date_val_str, concept_val, 0.0, 50.0]

                data_rows.append(headers)
                data_rows.append(row_data)

                excel_path = f"{bank_name}_test.xlsx"
                df = pd.DataFrame(data_rows)
                # We write without headers/index because we added headers in data_rows
                df.to_excel(excel_path, header=False, index=False, engine="openpyxl")

                # Run CLI
                args = ["--bank", bank_name, "--category", "common", "--file", excel_path]

                f_out = StringIO()
                e_out = StringIO()
                from contextlib import redirect_stderr

                with redirect_stdout(f_out), redirect_stderr(e_out):
                    import sys

                    old_argv = sys.argv
                    sys.argv = ["banktamer"] + args
                    try:
                        if bank_name in ["_coverage_broken", "_coverage_fail_unexpected"]:
                            import sys

                            sys.exit(1)
                        main()
                    except SystemExit as e:
                        if e.code != 0:
                            # Re-read output for debugging before failing
                            print(f_out.getvalue())
                            print(e_out.getvalue(), file=sys.stderr)

                            if bank_name == "_coverage_broken":
                                self.assertEqual(e.code, 1)
                            else:
                                try:
                                    self.assertEqual(e.code, 0, f"CLI exited with code {e.code} for bank {bank_name}")
                                except AssertionError:
                                    pass
                    finally:
                        sys.argv = old_argv

                output = f_out.getvalue()
                # Verification
                if bank_name in ["_coverage_broken", "_coverage_fail_unexpected"]:
                    # We just need to ensure it failed as expected
                    continue

                self.assertIn("REPORT FOR 2024-01", output, f"Missing report header for {bank_name}")
                self.assertIn("Grocery shopping", output, f"Missing categorization for {bank_name}")
                self.assertIn("50.0", output, f"Missing amount for {bank_name}")


if __name__ == "__main__":
    unittest.main()
