import unittest
from datetime import date
from banktamer.models import Transaction
from banktamer.analytics import AnalyticsProcessor


class TestAnalyticsProcessor(unittest.TestCase):
    def setUp(self) -> None:
        self.processor = AnalyticsProcessor()
        self.transactions = [
            Transaction(date=date(2024, 1, 15), concept="Income", amount=1000.0, category="Income"),
            Transaction(date=date(2024, 1, 20), concept="Luz", amount=-50.0, category="Utilities"),
            Transaction(date=date(2024, 1, 25), concept="Unknown expense", amount=-20.0, category="Unknown"),
            Transaction(date=date(2024, 2, 5), concept="Luz Feb", amount=-60.0, category="Utilities"),
        ]

    def test_process_monthly_totals(self) -> None:
        report = self.processor.process(self.transactions)

        self.assertIn("2024-01", report)
        self.assertIn("2024-02", report)

        jan = report["2024-01"]
        self.assertEqual(jan["total_income"], 1000.0)
        self.assertEqual(jan["total_expenses"], -70.0)
        self.assertEqual(len(jan["unknown_concepts"]), 1)
        self.assertIn("Unknown expense", [c[2] for c in jan["unknown_concepts"]])

    def test_process_category_stats(self) -> None:
        report = self.processor.process(self.transactions)
        jan_cats = report["2024-01"]["categories"]

        self.assertEqual(jan_cats["Utilities"].total, -50.0)
        self.assertIsNotNone(jan_cats["Utilities"].max_txn)
        if jan_cats["Utilities"].max_txn:
            self.assertEqual(jan_cats["Utilities"].max_txn.concept, "Luz")

    def test_get_evolution_data(self) -> None:
        report = self.processor.process(self.transactions)
        months, evolution = self.processor.get_evolution_data(report)

        self.assertEqual(months, ["2024-01", "2024-02"])
        self.assertIn("Income", evolution)
        self.assertIn("Utilities", evolution)
        self.assertIn("Unknown", evolution)

        self.assertEqual(evolution["Utilities"], [-50.0, -60.0])
        self.assertEqual(evolution["Income"], [1000.0, 0.0])


if __name__ == "__main__":
    unittest.main()
