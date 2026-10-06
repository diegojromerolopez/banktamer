<p align="center">
  <img src="assets/logo.png" width="300" alt="BankTamer Logo">
</p>

[![CI Status](https://github.com/diegojromerolopez/banktamer/actions/workflows/ci.yml/badge.svg)](https://github.com/diegojromerolopez/banktamer/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen.svg)](https://github.com/diegojromerolopez/banktamer/actions/workflows/ci.yml)
[![Python Version](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/release/python-3130/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://img.shields.io/badge/types-mypy-blue.svg)](https://mypy-lang.org/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)

# BankTamer

`banktamer` is a Python 3.13+ CLI utility designed to process bank transaction files (XLS/XLSX), categorize operations using regex-based pattern matching, and generate detailed financial reports.

## Features

- **Standardized Ingestion**: Support for multiple bank formats via JSON schemas.
- **Regex Categorization**: Fully customizable category rules using YAML.
- **Monthly Analytics**: Automatic grouping by month with totals for income, expenses, and net balance.
- **Visual Insights**: Automatic generation of colorful terminal bar charts, financial distribution pie charts, and category evolution line charts (tracking Incomes/Expenses over time).
- **Modern Reporting**: Export options to professional PDF documents for easy sharing and record keeping.
- **AI-Powered Insights**: (Optional) Integrated financial advisor that analyzes your spending patterns and provides actionable saving suggestions using providers like OpenAI, Anthropic, Gemini, or local models via Ollama.
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

### Installation Options

#### 1. Global Installation (via `pipx`)
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

# Automated Bank Download: Connect to Santander, download transactions, and analyze
banktamer --profile santander

# Example: Santander with common rules
banktamer --bank santander --category common --files downloads/extract_2024.xlsx

# Example: Multiple files from the same bank
banktamer --bank santander --category common --files extract_jan.xlsx extract_feb.xlsx extract_mar.xlsx

# Example: Using custom config directory
banktamer --bank santander --config-dir /path/to/my/config --files data.xlsx

# Example: Generating a professional PDF report
banktamer --bank santander --category common --files data.xlsx --report pdf --output report_2024.pdf

# Example: AI Analysis with local Ollama
banktamer --bank santander --category common --files data.xlsx --ai ollama
```

### Automated Bank Downloads (`--profile`)

BankTamer supports automated bank scraping via Playwright to log in, navigate, handle dynamic pagination, and download your transaction files directly.

#### Prerequisites
Ensure the Playwright Chromium browser binary is installed:
```bash
uv run playwright install chromium
```

#### Running with a Profile
1. Provide your bank credentials via environment variables or a `.env` file (see `.env.example`):
   ```bash
   export SANTANDER_USERNAME="your-nif"
   export SANTANDER_PASSWORD="your-password"
   ```
   > **Note**: If `SANTANDER_PASSWORD` is empty or not set, BankTamer will automatically prompt you securely in the terminal using masked input.

2. Run BankTamer with the desired profile:
   ```bash
   banktamer --profile santander
   ```

3. CLI options for profiles:
   - `--profile <name>`: Name of the bank profile (matches `config/profiles/<name>.yaml`).
   - `--download-dir <path>`: Directory where downloaded statement files will be stored (defaults to `./downloads`).
   - `--headless` / `--no-headless`: Run browser in headless mode (default) or headful mode to watch the automation in real time.
   - `--env-file <path>`: Path to a custom `.env` file for credentials (defaults to `./.env` if present).

#### Bank Profile Structure (`config/profiles/<profile_name>.yaml`)

A profile defines the bank association, browser settings, credentials, and step-by-step automation pipeline:

```yaml
bank: "santander-es"                             # Target bank schema in schemas.json
url: "https://particulares.bancosantander.es/oneweb/"
headless: true                                  # Default headless setting (can be overridden via CLI)
timeout_ms: 30000                               # Default step timeout in milliseconds

credentials:
  username:
    env: "SANTANDER_USERNAME"
  password:
    env: "SANTANDER_PASSWORD"

steps:
  - action: "navigate"
    url: "https://particulares.bancosantander.es/oneweb/"

  - action: "fill"
    selector: "#san-text-input-1"
    value: "${username}"

  - action: "fill"
    selector: "#san-text-input-0"
    value: "${password}"

  - action: "click"
    selector: "button.san-ending-button"

  - action: "wait_for_url"
    url: "https://particulares.bancosantander.es/oneweb/global-position"

  - action: "click"
    selector: "button.san-product-cards__interactive-layer"
    first: true

  - action: "wait_for_url"
    url: "https://particulares.bancosantander.es/oneweb/accounts"

  - action: "load_until_date"
    selector: "san-action-link"
    has_text: "Ver más movimientos"
    item_selector: "san-transaction-list-item"
    date_selector: "san-transaction-list-header > h4"
    days_past: 100
    seconds: 1.0
    max_clicks: 50

  - action: "click"
    selector: "button[aria-label='Acción 3 de 3: Descargar movimientos']"

  - action: "wait_for_selector"
    selector: "button[aria-label='Descargar en formato Excel']"

  - action: "click"
    selector: "button[aria-label='Descargar en formato Excel']"

  - action: "wait"
    seconds: 2

  - action: "download"
    selector: "san-ending-button"
    has_text: "Descargar"
```

#### Supported Step Actions

| Action | Description | Parameters |
| :--- | :--- | :--- |
| `navigate` | Navigates the browser to the specified URL. | `url`, `timeout_ms` |
| `fill` | Fills an input element. Resolves `${username}`, `${password}`, or any `${ENV_VAR}`. Automatically masked in console logs. | `selector`, `value`, `timeout_ms` |
| `click` | Clicks a button or element. | `selector`, `has_text` (optional), `first` (bool, optional), `timeout_ms` |
| `wait_for_url` | Waits until browser URL matches the target URL. | `url`, `timeout_ms` |
| `wait_for_selector` | Waits until element matches a state (`visible`, `attached`, `hidden`, `detached`). | `selector`, `state`, `timeout_ms` |
| `wait` | Suspends execution for a specified duration. | `seconds` |
| `load_until_date` | Automated dynamic pagination. Clicks the load-more button (`selector`) and waits for `item_selector` count to increase until date headers (`date_selector`) contain a date `days_past` days in the past or older. Supports Spanish date formats (e.g. `"Lunes, 27 Julio"`). Stops gracefully if button is not visible or `max_clicks` is reached. | `selector`, `has_text`, `item_selector`, `date_selector`, `days_past`, `max_clicks`, `seconds`, `timeout_ms` |
| `download` | Clicks the download trigger element and intercepts the browser file download event, saving the file to the download directory. | `selector`, `has_text` (optional), `first` (bool, optional), `timeout_ms` |

#### Error Handling and Debugging
- Each step is logged to the terminal with sanitized parameters (passwords are masked with `********`).
- If any step fails or times out, BankTamer automatically captures a debug screenshot to `<download-dir>/automation_error.png` to help inspect the browser state.

### AI Financial Analysis

BankTamer includes an optional AI-powered financial advisor that can analyze your categorized data and provide:
- Detailed spending pattern summaries.
- Actionable money-saving suggestions.
- Identification of unusual category spikes or trends.

#### Supported Providers

| Provider | Requirement | Flag |
| :--- | :--- | :--- |
| **Ollama** | Running local instance | `--ai ollama` |
| **OpenAI** | API Key (`OPENAI_API_KEY`) | `--ai openai` |
| **Anthropic** | API Key (`ANTHROPIC_API_KEY`) | `--ai anthropic` |
| **Gemini** | API Key (`GOOGLE_API_KEY`) | `--ai gemini` |
| **Hugging Face**| API Key (`HUGGINGFACE_API_KEY`)| `--ai huggingface` |

#### Local AI (Ollama) Smart Selection

If you use `--ai ollama` without specifying a model, BankTamer performs **intelligent auto-discovery**:
1.  **Llama 3 First**: It prioritizes `llama3` if it's installed on your system.
2.  **Resource Efficient**: If `llama3` is missing, it automatically picks the **smallest** available general-purpose model to save memory.
3.  **Privacy & Quality**: It automatically skips remote "cloud" links and "coder" specialized models (like `deepseek-coder`) to ensure you get high-quality financial advice strictly on your local machine.

To override the selection, use `--ai-model <model_name>`.

#### Customizing AI Prompts (`ai_settings.yaml`)

You can customize the AI's persona and instructions by creating an `ai_settings.yaml` file in your configuration directory (e.g., `~/.banktamer/config/ai_settings.yaml`).

```yaml
prompt_templates:
  financial_analysis: |
    You are a strictly frugal financial advisor. 
    Analyze the following data and be very critical of any non-essential spending.
    {summary}
```

The `{summary}` placeholder is optional; if present, it will be replaced by the monthly financial data. If absent, the data will be appended to your custom prompt.

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
│   └── integration/     # Integration tests (verifying banks & happy paths)
├── GEMINI.md            # Critical AI/Developer coding rules
├── Makefile             # Development automation
└── pyproject.toml       # Dependencies & Config
```

### Development Workflow

Use the provided `Makefile` for standard tasks:

- **Format code**: `make format`
- **Lint code**: `make lint` (Ruff & Mypy)
- **Run all tests**: `make test-all`
- **Tag and push release**: `make tag` (triggers GitHub Release and PyPI publication)

### Testing Strategy

`banktamer` follows a strict testing hierarchy to ensure reliability:

1.  **Unit Tests (`tests/unit`)**: Fast tests focusing on individual functions and classes. **100% code coverage is mandatory.**
2.  **Integration Tests (`tests/integration`)**:
    - **Schema Verification**: Every bank defined in `config/schemas.json` is automatically verified against generated Excel files to ensure parsing logic is correct.
    - **Happy Paths**: End-to-end functional flows for different bank formats (unified vs. split amounts).

Run specific test suites:

```bash
make test             # Unit tests only
make test-integration # Integration tests only
make test-all         # All of the above
```



### Adding a New Bank

1.  Add the column mapping to `config/schemas.json`.
2.  Assign an existing category file or create a new one in `config/categories/<category>.yaml`.
3.  **Run integration tests**: `make test-integration`. The schema verification test will automatically pick up your new bank and verify it parses correctly.

### Coding Standards

- **Rules**: See [GEMINI.md](GEMINI.md) for strict requirements (100% coverage, no relative imports, etc.).
- **Line Length**: 120 characters.
- **Type Hints**: Mandatory for all functions (verified via `mypy`). No `Any` allowed.
- **Python Version**: Strictly 3.10+ using native generics (e.g., `list[str]`).
