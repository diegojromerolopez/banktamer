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

### Global Installation (Recommended)

To install `banktamer` as a global command on your system, it is recommended to use `pipx`:

```bash
# From the local repository
pipx install .

# Or from Git directly
pipx install git+https://github.com/diegojromerolopez/banktamer.git
```

Once installed, you can run `banktamer` from anywhere.

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

### Configuration

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
├── assets/              # Project assets (logo, etc.)
├── banktamer/           # Core source code
│   ├── analytics.py     # Aggregation logic
│   ├── categorizer.py   # Regex engine
│   ├── cli.py           # Entry point & CLI logic
│   ├── config/          # Bundled JSON schemas & YAML rules (DEFAULTS)
│   ├── io.py            # Excel ingestion
│   ├── models.py        # Data structures
│   └── report/          # Reporting engine
│       ├── terminal.py  # Terminal visualization (always on)
│       └── pdf.py       # Professional PDF generation
├── tests/
│   └── unit/            # Unit tests (100% coverage mandatory)
├── GEMINI.md            # Critical AI/Developer coding rules
├── Makefile             # Development automation
└── pyproject.toml       # Dependencies & Config
```

### Development Workflow

Use the provided `Makefile` for standard tasks:

- **Format code**: `make format` (Uses `black` and `ruff`)
- **Lint code**: `make lint` (Uses `flake8`, `ruff`, and `mypy`)
- **Run tests**: `make test` (Executes tests in `tests/unit`)
- **Sync dependencies**: `make install`

### Adding a New Bank

1.  Add the column mapping to `config/schemas.json`.
2.  Assign an existing category file or create a new one in `config/categories/<category>.yaml`.
3.  Test it with `make run args="..."`.

### Coding Standards

- **Rules**: See [GEMINI.md](GEMINI.md) for strict requirements (100% coverage, no relative imports, etc.).
- **Line Length**: 120 characters.
- **Type Hints**: Mandatory for all functions (verified via `mypy`). No `Any` allowed.
- **Python Version**: Strictly 3.10+ using native generics (e.g., `list[str]`).
