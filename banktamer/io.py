import json
import pandas as pd
from banktamer.models import Transaction


class ExcelReader:
    """Read bank transactions from Excel files based on a provided schema."""

    def __init__(self, schemas: dict[str, dict]) -> None:
        """Initialize with a dictionary of bank schemas."""
        self.schemas = schemas

    def read(self, bank: str, file_path: str) -> list[Transaction]:
        """Read an Excel file and return a list of Transaction objects."""
        if bank not in self.schemas:
            raise ValueError(f"Bank '{bank}' not found in schemas.")

        schema = self.schemas[bank]
        df = pd.read_excel(file_path, skiprows=schema.get("skiprows", 0))

        # Validate columns
        required_cols = [schema["date_col"], schema["concept_col"]]
        if "amount_col" in schema:
            required_cols.append(schema["amount_col"])
        elif "income_col" in schema and "expense_col" in schema:
            required_cols.extend([schema["income_col"], schema["expense_col"]])
        else:
            raise ValueError(f"Missing amount configuration for bank '{bank}'")

        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            available_cols = ", ".join(str(c) for c in df.columns)
            raise ValueError(
                f"Missing required columns in file: {', '.join(missing_cols)}. Available columns: {available_cols}"
            )

        transactions: list[Transaction] = []
        for _, row in df.iterrows():
            try:
                # Handle date
                raw_date = row[schema["date_col"]]
                txn_date = pd.to_datetime(raw_date, format=schema.get("date_format")).date()

                # Handle concept
                concept = str(row[schema["concept_col"]])

                # Handle amount (unified into a single value) using SSA-friendly logic
                if "amount_col" in schema:
                    amount = float(row[schema["amount_col"]])
                elif "income_col" in schema and "expense_col" in schema:
                    income = row[schema["income_col"]]
                    expense = row[schema["expense_col"]]

                    income_val = float(income) if pd.notnull(income) else 0.0
                    expense_val = float(expense) if pd.notnull(expense) else 0.0

                    # Assign amount once based on which column has data
                    amount = income_val if income_val != 0 else -abs(expense_val)

                transactions.append(Transaction(date=txn_date, concept=concept, amount=amount))
            except (KeyError, ValueError, TypeError):
                # Skip rows that don't match the expected format (e.g., footers, empty lines)
                continue

        return transactions
