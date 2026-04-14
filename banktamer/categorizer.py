import re
from banktamer.models import Transaction


class Categorizer:
    """Assign categories to transactions based on regex rules."""

    def __init__(self, rules: dict[str, list[str]]) -> None:
        """Initialize with a pre-loaded dictionary of regex rules."""
        self.rules = rules

    def categorize(self, transactions: list[Transaction]) -> list[Transaction]:
        """Return a new list of transactions with assigned categories."""
        categorized_transactions: list[Transaction] = []

        for txn in transactions:
            found_category = "Unknown"
            for category, patterns in self.rules.items():
                match_found = False
                for pattern in patterns:
                    if re.search(pattern, txn.concept, re.IGNORECASE):
                        found_category = category
                        match_found = True
                        break
                if match_found:
                    break

            # Create a new Transaction object to favor immutability
            categorized_transactions.append(
                Transaction(
                    date=txn.date,
                    concept=txn.concept,
                    amount=txn.amount,
                    category=found_category,
                )
            )

        return categorized_transactions
