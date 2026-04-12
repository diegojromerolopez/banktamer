import re
import yaml
from pathlib import Path
from typing import cast
from banktamer.models import Transaction


class Categorizer:
    def __init__(self, category: str | None = None, rules_dir: str = "config/categories") -> None:
        self.rules_dir = Path(rules_dir)
        self.rules = self._load_rules(category)

    def _load_rules(self, category: str | None) -> dict[str, list[str]]:
        rules: dict[str, list[str]] = {}

        # 1. Load .default if present
        default_path = self.rules_dir / ".default.yaml"
        if default_path.exists():
            with open(default_path, "r") as f:
                default_rules = yaml.safe_load(f)
                if default_rules:
                    rules.update(cast(dict[str, list[str]], default_rules))

        # 2. Load specified category if present and not .default (to avoid double loading)
        if category and category != ".default":
            path = self.rules_dir / f"{category}.yaml"
            if path.exists():
                with open(path, "r") as f:
                    spec_rules = yaml.safe_load(f)
                    if spec_rules:
                        for cat, patterns in cast(dict[str, list[str]], spec_rules).items():
                            if cat in rules:
                                rules[cat].extend(patterns)
                            else:
                                rules[cat] = patterns
        return rules

    def categorize(self, transactions: list[Transaction]) -> list[Transaction]:
        for txn in transactions:
            txn.category = "Unknown"
            for category, patterns in self.rules.items():
                for pattern in patterns:
                    if re.search(pattern, txn.concept, re.IGNORECASE):
                        txn.category = category
                        break
                if txn.category != "Unknown":
                    break
        return transactions
