# Python Coding Rules

- **Total Test Coverage**: All Python code must have 100% unit test coverage.
- **Unit Test Location**: All unit tests must be located in the `tests/unit` folder.
- **Integration Test Location**: All integration tests must be located in the `tests/integration` folder.
- **Happy Path Integration**: All happy paths must be covered by integration tests to ensure end-to-end functionality.
- **No Relative Imports**: Only absolute imports are allowed (e.g., `from banktamer.models import ...` instead of `from .models import ...`).
- **No `Any` Type Hint**: Do not use the `Any` type hint unless it is absolutely impossible to avoid. Use specific types or `TypedDict`/`dataclasses` for complex structures.
- **SOLID Principles**: Follow the SOLID principles to ensure a maintainable and scalable codebase.
- **Dependency Injection**: Use dependency injection to decouple components and improve testability.
- **Immutability**: Favor immutability by returning new objects instead of modifying existing ones, especially for domain models.
- **Docstrings**: All classes and public methods must have descriptive docstrings following PEP 257.
- **Specific Exceptions**: Avoid broad `except Exception:` blocks. Catch specific exceptions and handle them appropriately.
- **Static Single-Assignment (SSA)**: Prefer SSA form; do not reuse variables for different purposes (except when unavoidable, e.g., in loops).
- **Maximum File Length**: No Python file can have more than 500 lines of code. If a file exceeds this limit, it must be split into smaller, modular files.
- **Always Passing Tests**: All unit and integration tests must pass successfully after any change to the codebase.
- **Always Passing Lint**: After each change, `make lint` must be successful.
- **No Conditions in Tests**: Do not add branching logic (if/else, try/except) in tests; each test should correspond to a single, clear scenario.
- **Explicit Mock Assertions**: Use `self.assertEqual` on `call_args_list` to verify the exact sequence and parameters for every mock used. Avoid generic `assert_called()` or `call_args` without parameter verification. Each mock used must have its calls fully accounted for in the assertions.

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
- **Verification**: Every new bank schema MUST be verified by an integration test (e.g., in `tests/integration/test_bank_schemas.py`) to ensure the parsing logic works with its specific column names and date formats.

### 2. Type Safety
- Use `TypedDict` for complex dictionary structures (see `MonthReport` in `analytics.py`).
- Prefer `dataclass` for immutable data objects like `Transaction` and `CategoryStats`.
- Leverage Python 3.10+ native generics (e.g., `dict[str, int]` instead of `Dict[str, int]`).

### 3. Testing Strategy
To maintain 100% coverage efficiently:
- **Mocking IO**: Use `unittest.mock.patch("builtins.open")` and `mock_open` to simulate reading config files without relying on the disk.
- **Mocking Data**: Use `pandas.DataFrame` in tests to simulate bank exports rather than providing real Excel files.
- **CLI Isolation**: When testing `cli.py`, mock `argparse`, `ExcelReader`, and `Categorizer` to focus on the reporting logic.

### 4. Integration Testing
Integration tests ensure that all components work together correctly:
- **No Mocking**: Do not mock internal application logic (Categorizer, ExcelReader, etc.). Only mock external services if absolutely necessary.
- **File-Based**: Use real (or programmatically generated) XLS/XLSX files for testing.
- **Output-First**: Assertions should primarily verify the correct terminal output or generated report files.
- **Schema Coverage**: Every bank defined in `banktamer/config/schemas.json` MUST be covered by an integration test. The test suite should dynamically iterate through all schemas to ensure broad coverage.
- **Location**: Use `tests/integration/` for all end-to-end scenarios.

## Common Pitfalls
- **Categorization Order**: If multiple regex patterns match a transaction, the first one defined in the YAML file wins.
- **Pandas Date Formats**: Ensure the `date_format` in `schemas.json` matches the bank's format exactly (e.g., `%d/%m/%Y` vs `%Y-%m-%d`).
- **Floating Point**: Be aware of precision in totals; the tool uses standard `float` for reporting accuracy.

## Development Commands
- `make test`: Runs all tests and verifies coverage.
- `make lint`: Runs `ruff` and `mypy` (strict mode) on both source and tests.
- `make format`: Automatically fixes formatting issues via `ruff`.
- `make dist-exe`: Builds a standalone executable using Nuitka.
- `make tag`: Creates a git tag using the version from `pyproject.toml` and pushes it. This triggers a GitHub Release and publishes the package to PyPI.

## Distribution & Releases

### Standalone Executables
To provide a friction-less experience, `banktamer` is distributed as a standalone executable for Linux, macOS, and Windows. This bundles the Python interpreter and all dependencies into a single file by compiling the Python code to C++.

- **Local Build**: Run `make dist-exe`. The resulting binary will be in the `dist/` directory. This requires a C++ compiler (like clang, gcc, or msvc) to be installed on your system.
- **Automated Releases**: The project uses GitHub Actions to automatically build and attach these executables to GitHub Releases whenever a new version tag (e.g., `v0.1.0`) pushed to the repository.
