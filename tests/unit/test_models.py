import unittest
from datetime import date
from banktamer.models import Transaction


class TestTransaction(unittest.TestCase):
    def test_is_income(self) -> None:
        t1 = Transaction(date=date(2024, 1, 1), concept="Salary", amount=1000.0)
        self.assertTrue(t1.is_income)
        self.assertFalse(t1.is_expense)

        t2 = Transaction(date=date(2024, 1, 1), concept="Gift", amount=0.0)
        self.assertFalse(t2.is_income)
        self.assertFalse(t2.is_expense)

    def test_is_expense(self) -> None:
        t1 = Transaction(date=date(2024, 1, 1), concept="Rent", amount=-500.0)
        self.assertTrue(t1.is_expense)
        self.assertFalse(t1.is_income)

        t2 = Transaction(date=date(2024, 1, 1), concept="Zero", amount=0.0)
        self.assertFalse(t2.is_expense)
        self.assertFalse(t2.is_income)


if __name__ == "__main__":
    unittest.main()
