import pandas as pd
from banktamer.models import Transaction


class ExcelReader:
    """Read bank transactions from Excel files based on a provided schema."""

    def __init__(self, schemas: dict[str, dict]) -> None:
        """Initialize with a dictionary of bank schemas."""
        self.schemas = schemas

    def _resolve_col(self, df: pd.DataFrame, col_config: str | list[str]) -> str:
        """Resolve a column name from a string or list of possible names."""
        names = [col_config] if isinstance(col_config, str) else col_config
        for name in names:
            if name in df.columns:
                return name
        raise KeyError(f"None of the columns {names} found in {list(df.columns)}")

    def read(self, bank: str, file_path: str) -> list[Transaction]:
        """Read an Excel file and return a list of Transaction objects."""
        if bank not in self.schemas:
            raise ValueError(f"Bank '{bank}' not found in schemas.")

        schema = self.schemas[bank]
        df = pd.read_excel(file_path, skiprows=schema.get("skiprows", 0))

        try:
            # Resolve actual column names used in this file
            date_col = self._resolve_col(df, schema["date_col"])
            concept_col = self._resolve_col(df, schema["concept_col"])

            amount_col: str | None = None
            income_col: str | None = None
            expense_col: str | None = None

            if "amount_col" in schema:
                amount_col = self._resolve_col(df, schema["amount_col"])
            elif "income_col" in schema and "expense_col" in schema:
                income_col = self._resolve_col(df, schema["income_col"])
                expense_col = self._resolve_col(df, schema["expense_col"])
            else:
                raise ValueError(f"Missing amount configuration for bank '{bank}'")
        except KeyError as e:
            available_cols = ", ".join(str(c) for c in df.columns)
            raise ValueError(f"{str(e)}. Available columns: {available_cols}")

        transactions: list[Transaction] = []
        formats = schema.get("date_format")
        date_formats = [formats] if isinstance(formats, str) or formats is None else formats

        for _, row in df.iterrows():
            try:
                # Handle date
                raw_date = row[date_col]
                txn_date = None
                for fmt in date_formats:
                    try:
                        txn_date = pd.to_datetime(raw_date, format=fmt).date()
                        break
                    except (ValueError, TypeError):
                        continue
                
                if txn_date is None:
                    continue

                # Handle concept
                concept = str(row[concept_col])

                # Handle amount
                if amount_col:
                    amount = float(row[amount_col])
                else:
                    # income_col and expense_col are guaranteed to be set if amount_col is not
                    income = row[income_col]  # type: ignore
                    expense = row[expense_col]  # type: ignore

                    income_val = float(income) if pd.notnull(income) else 0.0
                    expense_val = float(expense) if pd.notnull(expense) else 0.0

                    # Assign amount once based on which column has data
                    amount = income_val if income_val != 0 else -abs(expense_val)

                transactions.append(Transaction(date=txn_date, concept=concept, amount=amount))
            except (KeyError, ValueError, TypeError):
                # Skip rows that don't match the expected format (e.g., footers, empty lines)
                continue

        return transactions
