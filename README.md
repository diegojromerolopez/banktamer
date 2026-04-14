<p align="center">
  <img src="assets/logo.png" width="300" alt="BankTamer Logo">
</p>

# BankTamer

`banktamer` is a Python 3.10+ CLI utility designed to process bank transaction files (XLS/XLSX), categorize operations using regex-based pattern matching, and generate detailed financial reports.

## Features

- **Standardized Ingestion**: Support for multiple bank formats via JSON schemas.
- **Regex Categorization**: Fully customizable category rules using YAML.
- **Monthly Analytics**: Automatic grouping by month with totals for income, expenses, and net balance.
- **Visual Insights**: Automatic generation of colorful terminal bar charts and financial distribution pie charts.
- **Modern Reporting**: Export options to professional PDF documents for easy sharing and record keeping.
- **Modern Tooling**: Managed with `uv` for high performance and strict type safety.
- **Standalone Distribution**: Ability to compile into a single-file executable for Linux, macOS, and Windows using Nuitka.
- **CI/CD Ready**: GitHub Actions pipeline for automated formatting, linting, and 100% test coverage verification.

---

## User Guide

### Prerequisites

- Python 3.10+
- `uv` (installed via `brew install uv`)

Clone the repository and install dependencies locally:

```bash
make install
```

### Installation Options

#### 1. Standalone Binary (Recommended for non-developers)
Download the latest `banktamer` executable for your OS from the [GitHub Releases](https://github.com/diegojromerolopez/banktamer/releases) page. No Python installation is required to run the binary.

#### 2. Global Installation (via `pipx`)
To install `banktamer` as a global command on your system:

```bash
# From the local repository
pipx install .

# Or from Git directly
pipx install git+https://github.com/diegojromerolopez/banktamer.git
```

### Configuration

`banktamer` looks for configuration in the following order:
1.  **CLI Flags**: `--config-dir`, `--schemas`, or `--rules-dir`.
2.  **Local Folder**: `./config/` in your current directory.
3.  **User Home**: `~/.banktamer/config/`.
4.  **Package Defaults**: Bundled internal configuration (fallback).

To set up your global configuration (optional), copy the bundled config to your home directory:
```bash
mkdir -p ~/.banktamer
cp -r banktamer/config ~/.banktamer/
```

### Usage

Once installed, use the `banktamer` command:

```bash
# General usage
banktamer --bank <bank-name> --category <category-name> --files <path-to-excel> [path-to-other-excel ...]

# Example: Santander with common rules
banktamer --bank santander --category common --files downloads/extract_2024.xlsx

# Example: Multiple files from the same bank
banktamer --bank santander --category common --files extract_jan.xlsx extract_feb.xlsx extract_mar.xlsx

# Example: Using custom config directory
banktamer --bank santander --config-dir /path/to/my/config --files data.xlsx

# Example: Generating a professional PDF report
banktamer --bank santander --category common --files data.xlsx --report pdf --output report_2024.pdf
```

#### Running directly with `uv`

If you prefer not to use `make`, you can run the tool directly using `uv run`:

```bash
uv run python -m banktamer.cli --bank santander --category common --files path/to/file.xlsx
```

### Configuration Details

#### Bank Schemas (`config/schemas.json`)
Defines column mappings and date formats.
- `date_col`: Name of the date column.
- `concept_col`: Name of the transaction description column.
- `amount_col`: Single column for amount (positive/negative).
- `income_col` / `expense_col`: Separate columns for income and expenses.
- `skiprows`: Number of header rows to ignore in the Excel file.

#### Categorization rules (`config/categories/<category>.yaml`)
Add regex patterns to classify transactions. Categories are independent of the bank schema. Patterns are matched case-insensitively by default.

#### Default Rules (`config/categories/.default.yaml`)
If present, rules in `.default.yaml` are always applied. If a specific `--category` is provided, its rules are merged with the default ones.
---

## Developer Guide

### Project Structure

```text
banktamer/
├── banktamer/           # Core source code
│   ├── analytics.py     # Aggregation logic
│   ├── categorizer.py   # Regex engine
│   ├── cli.py           # Entry point & CLI logic
│   ├── config/          # Bundled JSON schemas & YAML rules (DEFAULTS)
│   ├── io.py            # Excel ingestion
│   ├── report/          # Reporting engine
├── tests/
│   ├── unit/            # Unit tests (100% coverage mandatory)
│   ├── integration/     # Integration tests (verifying banks & happy paths)
│   └── e2e/             # End-to-end tests (verifying compiled binary)
├── GEMINI.md            # Critical AI/Developer coding rules
├── Makefile             # Development automation
└── pyproject.toml       # Dependencies & Config
```

### Development Workflow

Use the provided `Makefile` for standard tasks:

- **Format code**: `make format`
- **Lint code**: `make lint` (Ruff & Mypy)
- **Run all tests**: `make test-all`
- **Build standalone binary**: `make dist-exe`

### Testing Strategy

`banktamer` follows a strict testing hierarchy to ensure reliability:

1.  **Unit Tests (`tests/unit`)**: Fast tests focusing on individual functions and classes. **100% code coverage is mandatory.**
2.  **Integration Tests (`tests/integration`)**:
    - **Schema Verification**: Every bank defined in `config/schemas.json` is automatically verified against generated Excel files to ensure parsing logic is correct.
    - **Happy Paths**: End-to-end functional flows for different bank formats (unified vs. split amounts).
3.  **E2E Tests (`tests/e2e`)**: Verifies that the compiled Nuitka binary works correctly in an isolated environment using bundled configuration.

Run specific test suites:

```bash
make test             # Unit tests only
make test-integration # Integration tests only
make test-e2e         # E2E tests (builds binary if missing)
make test-all         # All of the above
```

### Standalone Executable (Nuitka)

`banktamer` can be compiled into a standalone executable that includes the Python interpreter, dependencies, and default configuration.

```bash
make dist-exe
```

The resulting binary will be located in the `dist/` directory. This is the same process used by the CI pipeline to generate GitHub Releases.

### Adding a New Bank

1.  Add the column mapping to `config/schemas.json`.
2.  Assign an existing category file or create a new one in `config/categories/<category>.yaml`.
3.  **Run integration tests**: `make test-integration`. The schema verification test will automatically pick up your new bank and verify it parses correctly.

### Coding Standards

- **Rules**: See [GEMINI.md](GEMINI.md) for strict requirements (100% coverage, no relative imports, etc.).
- **Line Length**: 120 characters.
- **Type Hints**: Mandatory for all functions (verified via `mypy`). No `Any` allowed.
- **Python Version**: Strictly 3.10+ using native generics (e.g., `list[str]`).
