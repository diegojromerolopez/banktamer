import unittest
from unittest.mock import patch, mock_open, MagicMock
from datetime import date
from banktamer.models import Transaction
from banktamer.categorizer import Categorizer
import yaml
from pathlib import Path


class TestCategorizer(unittest.TestCase):
    def create_path_mock(self, path_str: str, exists: bool | None = None) -> MagicMock:
        m = MagicMock(spec=Path)
        if exists is not None:
            m.exists.return_value = exists
        else:
            # Dynamic exists based on path string
            m.exists.side_effect = lambda: (".default.yaml" in path_str or "test" in path_str or "empty" in path_str)
        m.configure_mock(**{"__str__.return_value": path_str})
        m.__truediv__.side_effect = lambda other: self.create_path_mock(f"{path_str}/{other}")
        return m

    @patch("banktamer.categorizer.Path")
    def test_categorize_match(self, mock_path_cls: MagicMock) -> None:
        mock_path_cls.side_effect = lambda p: self.create_path_mock(p)
        rules = {"Utilities": ["Luz", "Endesa"], "Leisure": ["Restaurante"]}
        yaml_content = yaml.dump(rules)

        with patch("builtins.open", mock_open(read_data=yaml_content)):
            categorizer = Categorizer("test_category")
            txns = [
                Transaction(date=date(2024, 1, 1), concept="Factura LUZ Enero", amount=-50.0),
                Transaction(date=date(2024, 1, 1), concept="RESTAURANTE LA PAZ", amount=-30.0),
            ]
            categorized = categorizer.categorize(txns)
            self.assertEqual(categorized[0].category, "Utilities")
            self.assertEqual(categorized[1].category, "Leisure")

    @patch("banktamer.categorizer.Path")
    def test_categorize_unknown(self, mock_path_cls: MagicMock) -> None:
        mock_path_cls.side_effect = lambda p: self.create_path_mock(p)
        with patch("builtins.open", mock_open(read_data="{}")):
            categorizer = Categorizer("test_category")
            txns = [Transaction(date=date(2024, 1, 1), concept="Something unknown", amount=-10.0)]
            categorized = categorizer.categorize(txns)
            self.assertEqual(categorized[0].category, "Unknown")

    @patch("banktamer.categorizer.Path")
    def test_missing_config(self, mock_path_cls: MagicMock) -> None:
        # For this test, we want EVERYTHING to not exist
        def create_non_existent_path(p: str) -> MagicMock:
            m = self.create_path_mock(p, exists=False)
            m.__truediv__.side_effect = create_non_existent_path
            return m

        mock_path_cls.side_effect = create_non_existent_path
        categorizer = Categorizer("non_existent")
        self.assertEqual(categorizer.rules, {})
        txns = [Transaction(date=date(2024, 1, 1), concept="Anything", amount=-10.0)]
        categorized = categorizer.categorize(txns)
        self.assertEqual(categorized[0].category, "Unknown")

    @patch("banktamer.categorizer.Path")
    def test_default_category_only(self, mock_path_cls: MagicMock) -> None:
        yaml_content = yaml.dump({"General": ["Gasoline"]})
        
        def path_side_effect(path_str: str) -> MagicMock:
            exists = ".default.yaml" in path_str
            return self.create_path_mock(path_str, exists=exists)
        
        mock_path_cls.side_effect = path_side_effect

        with patch("builtins.open", mock_open(read_data=yaml_content)):
            categorizer = Categorizer(None)
            self.assertEqual(categorizer.rules, {"General": ["Gasoline"]})

    @patch("banktamer.categorizer.Path")
    def test_merge_default_and_specific(self, mock_path_cls: MagicMock) -> None:
        mock_path_cls.side_effect = lambda p: self.create_path_mock(p)

        default_rules = {"Utilities": ["Gas"], "Global": ["Tax"]}
        spec_rules = {"Utilities": ["Luz"], "Leisure": ["Restaurante"]}

        def open_side_effect(path: object, *args: list[object], **kwargs: dict[str, object]) -> object:
            if ".default.yaml" in str(path):
                return mock_open(read_data=yaml.dump(default_rules)).return_value
            return mock_open(read_data=yaml.dump(spec_rules)).return_value

        with patch("builtins.open", side_effect=open_side_effect):
            categorizer = Categorizer("test_category")
            self.assertEqual(categorizer.rules["Utilities"], ["Gas", "Luz"])
            self.assertIn("Global", categorizer.rules)
            self.assertIn("Leisure", categorizer.rules)

    @patch("banktamer.categorizer.Path")
    def test_fixed_regex_patterns(self, mock_path_cls: MagicMock) -> None:
        mock_path_cls.side_effect = lambda p: self.create_path_mock(p)
        # Verify that our fixes (using .* instead of *) work correctly
        rules = {"Insurance": [".*Seguros"]}
        yaml_content = yaml.dump(rules)

        with patch("builtins.open", mock_open(read_data=yaml_content)):
            categorizer = Categorizer("test_category")
            txns = [
                Transaction(date=date(2024, 1, 1), concept="COBRO SEGUROS VIDA", amount=-50.0),
                Transaction(date=date(2024, 1, 1), concept="MAPFRE SEGUROS HOGAR", amount=-30.0),
            ]
            categorized = categorizer.categorize(txns)
            self.assertEqual(categorized[0].category, "Insurance")
            self.assertEqual(categorized[1].category, "Insurance")

    @patch("banktamer.categorizer.Path")
    def test_empty_yaml(self, mock_path_cls: MagicMock) -> None:
        mock_path_cls.side_effect = lambda p: self.create_path_mock(p)
        with patch("builtins.open", mock_open(read_data="")):
            categorizer = Categorizer("empty")
            self.assertEqual(categorizer.rules, {})


if __name__ == "__main__":
    unittest.main()
