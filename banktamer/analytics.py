from collections import defaultdict
from dataclasses import dataclass
from typing import TypedDict
from datetime import date
from banktamer.models import Transaction


@dataclass
class CategoryStats:
    """Aggregated statistics for a specific category."""

    total: float = 0.0
    max_txn: Transaction | None = None


class MonthReport(TypedDict):
    """Structure for a monthly financial report."""

    categories: dict[str, CategoryStats]
    total_income: float
    total_expenses: float
    unknown_concepts: list[tuple[date, float, str]]


class AnalyticsProcessor:
    """Process a list of transactions into monthly reports."""

    def process(self, transactions: list[Transaction]) -> dict[str, MonthReport]:
        """Aggregate transactions by month and category."""
        # Group by month (YYYY-MM)
        monthly_data: dict[str, MonthReport] = defaultdict(
            lambda: MonthReport(
                categories=defaultdict(CategoryStats),
                total_income=0.0,
                total_expenses=0.0,
                unknown_concepts=[],
            )
        )

        for txn in transactions:
            month_key = txn.date.strftime("%Y-%m")
            data = monthly_data[month_key]

            # Totals
            if txn.is_income:
                data["total_income"] += txn.amount
            else:
                data["total_expenses"] += txn.amount
                if txn.category == "Unknown":
                    data["unknown_concepts"].append((txn.date, txn.amount, txn.concept))

            # Category stats
            cat_stats = data["categories"][txn.category]
            cat_stats.total += txn.amount

            # For max transaction per category, we look at the absolute value for expenses?
            # Or just the largest positive/smallest negative?
            # The plan says "max transaction (+concept)". Usually means largest impact.
            if cat_stats.max_txn is None or abs(txn.amount) > abs(cat_stats.max_txn.amount):
                cat_stats.max_txn = txn

        return dict(sorted(monthly_data.items()))

    def get_evolution_data(self, report_data: dict[str, MonthReport]) -> tuple[list[str], dict[str, list[float]]]:
        """Transform monthly reports into a category-wise evolution of totals."""
        months = sorted(report_data.keys())
        # Find all categories across all months
        all_categories: set[str] = set()
        for data in report_data.values():
            all_categories.update(data["categories"].keys())

        evolution: dict[str, list[float]] = {}
        for cat in sorted(all_categories):
            evolution[cat] = [report_data[m]["categories"].get(cat, CategoryStats()).total for m in months]

        return months, evolution
