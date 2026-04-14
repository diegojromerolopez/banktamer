import unittest
import os
import shutil
import tempfile
import json
import datetime
import pandas as pd
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
        for bank_name, schema in self.schemas.items():
            with self.subTest(bank=bank_name):
                # Prepare data
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
                data_rows: list[list] = []
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
                
                f = StringIO()
                with redirect_stdout(f):
                    import sys
                    old_argv = sys.argv
                    sys.argv = ["banktamer"] + args
                    try:
                        main()
                    except SystemExit as e:
                        if e.code != 0:
                            # Re-read output for debugging before failing
                            print(f.getvalue())
                            self.assertEqual(e.code, 0, f"CLI exited with code {e.code} for bank {bank_name}")
                    finally:
                        sys.argv = old_argv
                
                output = f.getvalue()
                
                # Verification
                self.assertIn("REPORT FOR 2024-01", output, f"Missing report header for {bank_name}")
                self.assertIn("Grocery shopping", output, f"Missing categorization for {bank_name}")
                self.assertIn("50.0", output, f"Missing amount for {bank_name}")

if __name__ == "__main__":
    unittest.main()
