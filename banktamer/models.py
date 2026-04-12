from dataclasses import dataclass
from datetime import date


@dataclass
class Transaction:
    date: date
    concept: str
    amount: float
    category: str = "Unknown"

    @property
    def is_income(self) -> bool:
        return self.amount > 0

    @property
    def is_expense(self) -> bool:
        return self.amount < 0
