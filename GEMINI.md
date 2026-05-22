# GEMINI.md - Taiwan Stock Multi-Factor Analysis System

## Project Overview
This project is a comprehensive **Taiwan Stock Multi-Factor Analysis System**. It provides tools for scoring stocks based on various dimensions, generating analysis reports, backtesting trading strategies, and visualizing results through a web dashboard.

### Core Technologies
- **Language:** Python 3
- **Data Analysis:** `pandas`, `numpy`, `scikit-learn`, `scipy`
- **Financial Data:** `FinMind`, `twstock`, TWSE OpenAPI
- **Backtesting:** `backtrader`
- **CLI:** `click`
- **Visualization:** `streamlit`, `plotly`, `matplotlib`
- **Logging:** `loguru`

### Architecture
- `src/main.py`: The central CLI entry point for all operations.
- `src/config.py`: Global configuration, including factor weights, backtest parameters, and directory paths.
- `src/data/`: Modules for data acquisition (`free_data_client.py`), caching (`cache_manager.py`), and scheduling (`scheduler.py`).
- `src/features/`: Individual scoring modules for:
    - Fundamental Analysis (`fundamental.py`) - 30% weight
    - Institutional/Chip Analysis (`institutional.py`) - 25% weight
    - Technical Analysis (`technical.py`) - 20% weight
    - Warrant Analysis (`warrant.py`) - 10% weight
    - Market Sentiment (`sentiment.py`) - 15% weight
- `src/model/`: Multi-factor model integration and signal generation.
- `src/backtest/`: Engine and strategies for performance evaluation.
- `src/analysis/`: Generation of detailed individual stock reports.
- `src/dashboard/`: Streamlit-based interactive web interface.

---

## Building and Running

### Prerequisites
- Python 3.9+
- Virtual environment (recommended)

### Installation
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Key Commands (via `src/main.py`)

- **Interactive Menu (Recommended):**
  ```bash
  python3 src/main.py
  # OR
  python3 src/main.py menu
  ```

- **Check API connectivity:**
  ```bash
  python3 src/main.py check-api
  ```

- **Analyze a specific stock:**
  ```bash
  python3 src/main.py analyze <stock_id> [--years 2] [--json]
  ```
  *Includes "Backtest Adaptability Analysis" to evaluate if the model is historically accurate for the given stock.*

- **Batch score stocks:**
  ```bash
  python3 src/main.py score [--max-stocks 50] [--top-n 10]
  ```

- **Run backtest:**
  ```bash
  python3 src/main.py backtest [--start YYYY-MM-DD] [--end YYYY-MM-DD] [--strategy rotation]
  ```

- **Start Dashboard:**
  ```bash
  python3 src/main.py dashboard
  ```

- **Daily Data Update:**
  ```bash
  python3 src/main.py schedule
  ```

- **Clear Cache:**
  ```bash
  python3 src/main.py clear [--dataset <name>]
  ```

---

## Development Conventions

### Coding Style
- Follow PEP 8 standards.
- Use `loguru` for all logging; avoid raw `print` statements in library code.
- Functional scoring modules: Each factor in `src/features/` should follow a consistent scoring pattern (returning a normalized value between 0.0 and 1.0).

### Data Management
- Local caching is handled via SQLite (`data/cache.db`).
- Use `FreeDataClient` for anonymous access to TWSE and FinMind when possible.
- Environment variables can be used for `FINMIND_TOKEN` to increase API rate limits.

### Testing and Validation
- Verify changes by running the CLI `check-api` and `analyze` commands.
- For new features, ensure they are integrated into `MultiFactorModel` if they contribute to the final score.
- Reports are generated in the `reports/` directory.
