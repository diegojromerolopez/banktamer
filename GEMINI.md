# Python Coding Rules

- **Total Test Coverage**: All Python code must have 100% unit test coverage.
- **Unit Test Location**: All unit tests must be located in the `tests/unit` folder.
- **No Relative Imports**: Only absolute imports are allowed (e.g., `from banktamer.models import ...` instead of `from .models import ...`).
- **No `Any` Type Hint**: Do not use the `Any` type hint unless it is absolutely impossible to avoid. Use specific types or `TypedDict`/`dataclasses` for complex structures.

## Project Goal & Context

`banktamer` is a CLI utility for personal finance management. Its primary goal is to take messy bank transaction exports (in XLS/XLSX formats), cleanse the data, categorize each transaction using flexible regex rules, and provide clear monthly financial insights. It is designed to be bank-agnostic, relying on external configurations for different banking standards.

## Module Breakdown & Structure

The codebase is organized into a single package `banktamer` with specialized modules:

- `io.py`: **Data Ingestion**. The gateway for external data. Contains `ExcelReader`, which translates bank-specific spreadsheet formats into internal `Transaction` objects.
- `categorizer.py`: **Rule Engine**. Contains the logic to iterate over transactions and assign categories based on YAML-defined regex patterns from the `banktamer/config/categories` folder. Supports a base `.default.yaml` and optional merges with specific categories.
- `analytics.py`: **Data Processor**. Transforms a flat list of categorized transactions into structured monthly reports, calculating totals and identifying category leaders (max transactions).
- `models.py`: **Domain Entities**. Defines the core data structures used across the app (`Transaction`, `CategoryStats`).
- `cli.py`: **User Interface**. Handles command-line arguments and orchestrates the financial pipeline.
- `report/`: **Visualization Layer**. Contains logic for rendering reports.
    - `terminal.py`: Handles rich terminal output with always-on bar and pie charts.
    - `pdf.py`: Handles generation of professional PDF reports with charts and summaries.

## Architectural Overview

BankTamer follows a straightforward linear pipeline:

1.  **Ingestion (`io.py`)**: Uses `ExcelReader` to load XLS/XLSX files based on bank-specific schemas defined in `banktamer/config/schemas.json`.
2.  **Categorization (`categorizer.py`)**: Applies regex rules from `banktamer/config/categories/<category>.yaml`. If `.default.yaml` is present in the same folder, its rules are loaded first and merged with the specified category.
3.  **Analytics (`analytics.py`)**: Aggregates transactions into monthly buckets, calculates totals, and identifies the most significant transactions in each category.
4.  **Reporting (`cli.py`)**: Formats and prints the processed data to the terminal.

## Distribution & Portability

`banktamer` is designed to be distributed as a Python package.

### Configuration Resolution Order
To support both development and global installation, configuration is resolved in this order:
1.  **Direct CLI arguments**: `--schemas`, `--rules-dir`, or `--config-dir`.
2.  **Local project folder**: `./config/` relative to the current working directory.
3.  **User home directory**: `~/.banktamer/config/`.
4.  **Package internal defaults**: `banktamer/config/` (bundled with the code).

### Entry Point
The tool provides a `banktamer` console script defined in `pyproject.toml`, which maps to `banktamer.cli:main`.

## Continuous Integration

A GitHub Actions pipeline is configured in `.github/workflows/ci.yml` to automatically:
- Verify code formatting (`ruff`).
- Enforce strict typing and linting (`mypy`, `ruff`).
- Ensure 100% unit test coverage.

## Core Development Patterns

### 1. Adding Support for a New Bank
To support a new bank, two configuration updates are required:
- **Schema**: Add an entry to `banktamer/config/schemas.json`. You must specify either `amount_col` (unified) or both `income_col` and `expense_col` (split).
- **Rules**: Categories are decoupled from banks. You can use an existing category file or create a new one in `banktamer/config/categories/<category>.yaml`. Use `.default.yaml` for rules that should always be active regardless of the selected category.

### 2. Type Safety
- Use `TypedDict` for complex dictionary structures (see `MonthReport` in `analytics.py`).
- Prefer `dataclass` for immutable data objects like `Transaction` and `CategoryStats`.
- Leverage Python 3.10+ native generics (e.g., `dict[str, int]` instead of `Dict[str, int]`).

### 3. Testing Strategy
To maintain 100% coverage efficiently:
- **Mocking IO**: Use `unittest.mock.patch("builtins.open")` and `mock_open` to simulate reading config files without relying on the disk.
- **Mocking Data**: Use `pandas.DataFrame` in tests to simulate bank exports rather than providing real Excel files.
- **CLI Isolation**: When testing `cli.py`, mock `argparse`, `ExcelReader`, and `Categorizer` to focus on the reporting logic.

## Common Pitfalls
- **Categorization Order**: If multiple regex patterns match a transaction, the first one defined in the YAML file wins.
- **Pandas Date Formats**: Ensure the `date_format` in `schemas.json` matches the bank's format exactly (e.g., `%d/%m/%Y` vs `%Y-%m-%d`).
- **Floating Point**: Be aware of precision in totals; the tool uses standard `float` for reporting accuracy.

## Development Commands
- `make test`: Runs all tests and verifies coverage.
- `make lint`: Runs `ruff` and `mypy` (strict mode) on both source and tests.
- `make format`: Automatically fixes formatting issues via `ruff`.
