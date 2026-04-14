from dataclasses import dataclass
from datetime import date


@dataclass
class Transaction:
    """Represent a single bank transaction."""

    date: date
    concept: str
    amount: float
    category: str = "Unknown"

    @property
    def is_income(self) -> bool:
        """Return True if the transaction is an income (positive amount)."""
        return self.amount > 0

    @property
    def is_expense(self) -> bool:
        """Return True if the transaction is an expense (negative amount)."""
        return self.amount < 0
