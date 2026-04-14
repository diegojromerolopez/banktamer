import unittest
from datetime import date
from banktamer.models import Transaction
from banktamer.categorizer import Categorizer


class TestCategorizer(unittest.TestCase):
    def test_categorize_match(self) -> None:
        rules = {"Utilities": ["Luz", "Endesa"], "Leisure": ["Restaurante"]}
        categorizer = Categorizer(rules)
        txns = [
            Transaction(date=date(2024, 1, 1), concept="Factura LUZ Enero", amount=-50.0),
            Transaction(date=date(2024, 1, 1), concept="RESTAURANTE LA PAZ", amount=-30.0),
        ]
        categorized = categorizer.categorize(txns)
        self.assertEqual(categorized[0].category, "Utilities")
        self.assertEqual(categorized[1].category, "Leisure")
        # Verify immutability: originals should still have "Unknown" (default)
        self.assertEqual(txns[0].category, "Unknown")

    def test_categorize_unknown(self) -> None:
        categorizer = Categorizer({})
        txns = [Transaction(date=date(2024, 1, 1), concept="Something unknown", amount=-10.0)]
        categorized = categorizer.categorize(txns)
        self.assertEqual(categorized[0].category, "Unknown")

    def test_fixed_regex_patterns(self) -> None:
        rules = {"Insurance": [".*Seguros"]}
        categorizer = Categorizer(rules)
        txns = [
            Transaction(date=date(2024, 1, 1), concept="COBRO SEGUROS VIDA", amount=-50.0),
            Transaction(date=date(2024, 1, 1), concept="MAPFRE SEGUROS HOGAR", amount=-30.0),
        ]
        categorized = categorizer.categorize(txns)
        self.assertEqual(categorized[0].category, "Insurance")
        self.assertEqual(categorized[1].category, "Insurance")


if __name__ == "__main__":
    unittest.main()
