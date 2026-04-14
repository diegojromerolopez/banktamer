import unittest
from unittest.mock import patch, mock_open
import pandas as pd
import json
from typing import Any
from banktamer.io import ExcelReader


class TestExcelReader(unittest.TestCase):
    def setUp(self) -> None:
        self.schemas = {
            "test_bank_unified": {
                "date_col": "Date",
                "concept_col": "Concept",
                "amount_col": "Amount",
                "date_format": "%Y-%m-%d",
            },
            "test_bank_split": {
                "date_col": "Date",
                "concept_col": "Concept",
                "income_col": "In",
                "expense_col": "Out",
                "date_format": "%Y-%m-%d",
            },
        }
        self.schemas_json = json.dumps(self.schemas)

    def test_init_loads_schemas(self) -> None:
        reader = ExcelReader(self.schemas)
        self.assertEqual(reader.schemas, self.schemas)

    @patch("pandas.read_excel")
    def test_read_unified(self, mock_read_excel: Any) -> None:
        # Mocking DataFrame
        df = pd.DataFrame(
            {"Date": ["2024-01-01", "2024-01-02"], "Concept": ["Salary", "Rent"], "Amount": [1000.0, -500.0]}
        )
        mock_read_excel.return_value = df

        reader = ExcelReader(self.schemas)
        txns = reader.read("test_bank_unified", "dummy.xlsx")

        self.assertEqual(len(txns), 2)
        self.assertEqual(txns[0].concept, "Salary")
        self.assertEqual(txns[0].amount, 1000.0)
        self.assertEqual(txns[1].amount, -500.0)

    @patch("pandas.read_excel")
    def test_read_split(self, mock_read_excel: Any) -> None:
        # Mocking DataFrame
        df = pd.DataFrame(
            {
                "Date": ["2024-01-01", "2024-01-02"],
                "Concept": ["Salary", "Rent"],
                "In": [1000.0, None],
                "Out": [0.0, 500.0],
            }
        )
        mock_read_excel.return_value = df

        reader = ExcelReader(self.schemas)
        txns = reader.read("test_bank_split", "dummy.xlsx")

        self.assertEqual(len(txns), 2)
        self.assertEqual(txns[0].amount, 1000.0)
        self.assertEqual(txns[1].amount, -500.0)

    @patch("pandas.read_excel")
    def test_missing_columns(self, mock_read_excel: Any) -> None:
        df = pd.DataFrame({"Wrong": [1]})
        mock_read_excel.return_value = df

        reader = ExcelReader(self.schemas)
        with self.assertRaises(ValueError) as cm:
            reader.read("test_bank_unified", "dummy.xlsx")
        self.assertIn("Missing required columns", str(cm.exception))

    def test_invalid_bank(self) -> None:
        reader = ExcelReader(self.schemas)
        with self.assertRaises(ValueError) as cm:
            reader.read("unknown_bank", "dummy.xlsx")
        self.assertIn("not found in schemas", str(cm.exception))

    @patch("pandas.read_excel")
    def test_malformed_rows_skipped(self, mock_read_excel: Any) -> None:
        df = pd.DataFrame(
            {
                "Date": ["2024-01-01", "invalid-date", "2024-01-03"],
                "Concept": ["Valid", "Invalid", "Valid"],
                "Amount": [100.0, "not-a-number", 200.0],
            }
        )
        mock_read_excel.return_value = df

        reader = ExcelReader(self.schemas)
        txns = reader.read("test_bank_unified", "dummy.xlsx")

        # Should skip the middle row
        self.assertEqual(len(txns), 2)
        self.assertEqual(txns[0].concept, "Valid")
        self.assertEqual(txns[1].concept, "Valid")

    @patch("pandas.read_excel")
    def test_missing_amount_config(self, mock_read_excel: Any) -> None:
        broken_schema = {"broken": {"date_col": "Date", "concept_col": "Concept"}}
        df = pd.DataFrame({"Date": ["2024-01-01"], "Concept": ["Test"]})
        mock_read_excel.return_value = df

        reader = ExcelReader(broken_schema)
        with self.assertRaises(ValueError) as cm:
            reader.read("broken", "dummy.xlsx")
        self.assertIn("Missing amount configuration", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
