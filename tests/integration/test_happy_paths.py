import unittest
import os
import shutil
import tempfile
import pandas as pd
from io import StringIO
from contextlib import redirect_stdout
from banktamer.cli import main

class TestHappyPathsIntegration(unittest.TestCase):
    """Integration tests for the BankTamer CLI happy paths."""

    def setUp(self) -> None:
        self.test_dir = tempfile.mkdtemp()
        self.old_cwd = os.getcwd()
        os.chdir(self.test_dir)

        # Create a local config structure to simulate a project
        os.makedirs("config/categories")
        
        # Copy real schemas and example categories to local config
        real_schemas = os.path.join(self.old_cwd, "banktamer/config/schemas.json")
        shutil.copy(real_schemas, "config/schemas.json")
        
        real_example = os.path.join(self.old_cwd, "banktamer/config/categories/example.yaml")
        shutil.copy(real_example, "config/categories/common.yaml")
        
        # No .default.yaml to avoid interference with specific matching

    def tearDown(self) -> None:
        os.chdir(self.old_cwd)
        shutil.rmtree(self.test_dir)

    def test_santander_happy_path(self) -> None:
        """Integration test for Santander bank format (unified amount)."""
        # Create a fake Santander Excel file
        # Santander has 7 rows of header to skip
        data = [[""] * 3] * 7  # 7 empty rows
        data.append(["FECHA OPERACIÓN", "CONCEPTO", "IMPORTE EUR"])
        data.append(["01/01/2024", "MERCADONA SUPER", -50.25])
        data.append(["02/01/2024", "AMAZON RETAIL", -120.00])
        data.append(["05/01/2024", "INGRESO NOMINA", 2500.00])
        
        # Use openpyxl engine explicitly for xlsx
        df = pd.DataFrame(data)
        excel_path = "santander_test.xlsx"
        df.to_excel(excel_path, header=False, index=False, engine="openpyxl")

        # Run CLI
        args = ["--bank", "santander", "--category", "common", "--file", excel_path]
        
        f = StringIO()
        with redirect_stdout(f):
            import sys
            old_argv = sys.argv
            sys.argv = ["banktamer"] + args
            try:
                main()
            finally:
                sys.argv = old_argv
        
        output = f.getvalue()
        
        # Asserts on terminal output
        self.assertIn("REPORT FOR 2024-01", output)
        self.assertIn("CATEGORIZED BREAKDOWN:", output)
        self.assertIn("Grocery shopping", output)  # Mercadona
        self.assertIn("Online shopping", output)   # Amazon
        self.assertIn("Income", output)            # Ingreso
        self.assertIn("50.25", output)
        self.assertIn("120.00", output)
        self.assertIn("2500.00", output)
        self.assertIn("MONTHLY SUMMARY:", output)

    def test_caja_rural_happy_path(self) -> None:
        """Integration test for Caja Rural bank format (split amounts)."""
        # Create a fake Caja Rural Excel file
        # Caja Rural has 0 skiprows
        data = {
            "Fecha": ["2024-02-01", "2024-02-15"],
            "Descripción": ["LUZ ENDESA", "REPSOL GASOLINERA"],
            "Abonos": [0.0, 0.0],
            "Cargos": [65.50, 40.00]
        }
        df = pd.DataFrame(data)
        excel_path = "caja_rural_test.xlsx"
        df.to_excel(excel_path, index=False, engine="openpyxl")

        # Run CLI
        args = ["--bank", "caja-rural", "--category", "common", "--file", excel_path]
        
        f = StringIO()
        with redirect_stdout(f):
            import sys
            old_argv = sys.argv
            sys.argv = ["banktamer"] + args
            try:
                main()
            finally:
                sys.argv = old_argv
        
        output = f.getvalue()
        
        # Asserts on terminal output
        self.assertIn("REPORT FOR 2024-02", output)
        self.assertIn("Utilities", output)      # Endesa
        self.assertIn("Car", output)            # Repsol
        self.assertIn("65.50", output)
        self.assertIn("40.00", output)
        self.assertIn("Total Expenses:", output)

    def test_multiple_files(self) -> None:
        """Integration test for processing multiple files at once."""
        # File 1: Santander format
        data1 = [[""] * 3] * 7
        data1.append(["FECHA OPERACIÓN", "CONCEPTO", "IMPORTE EUR"])
        data1.append(["01/01/2024", "MERCADONA", -10.00])
        df1 = pd.DataFrame(data1)
        df1.to_excel("file1.xlsx", header=False, index=False, engine="openpyxl")

        # File 2: Santander format
        data2 = [[""] * 3] * 7
        data2.append(["FECHA OPERACIÓN", "CONCEPTO", "IMPORTE EUR"])
        data2.append(["02/01/2024", "AMAZON", -20.00])
        df2 = pd.DataFrame(data2)
        df2.to_excel("file2.xlsx", header=False, index=False, engine="openpyxl")

        # Run CLI with both files
        args = ["--bank", "santander", "--category", "common", "--file", "file1.xlsx", "file2.xlsx"]
        
        f = StringIO()
        with redirect_stdout(f):
            import sys
            old_argv = sys.argv
            sys.argv = ["banktamer"] + args
            try:
                main()
            finally:
                sys.argv = old_argv
        
        output = f.getvalue()
        
        # Should see both categories in the output
        self.assertIn("Grocery shopping", output) # MERCADONA
        self.assertIn("Online shopping", output)  # AMAZON
        self.assertIn("10.00", output)
        self.assertIn("20.00", output)
        self.assertIn("30.00", output)  # Total expenses

    def test_unknown_categorization(self) -> None:
        """Integration test for transactions that don't match any rule."""
        data = {
            "Fecha": ["2024-03-01"],
            "Descripción": ["EXTRANJO CONCEPT"],
            "Abonos": [0.0],
            "Cargos": [99.99]
        }
        df = pd.DataFrame(data)
        excel_path = "unknown_test.xlsx"
        df.to_excel(excel_path, index=False, engine="openpyxl")

        args = ["--bank", "caja-rural", "--category", "common", "--file", excel_path]
        
        f = StringIO()
        with redirect_stdout(f):
            import sys
            old_argv = sys.argv
            sys.argv = ["banktamer"] + args
            try:
                main()
            finally:
                sys.argv = old_argv
        
        output = f.getvalue()
        
        self.assertIn("UNKNOWN EXPENSE CONCEPTS:", output)
        self.assertIn("EXTRANJO CONCEPT", output)
        self.assertIn("99.99", output)

if __name__ == "__main__":
    unittest.main()
