# Test Strategy for Taiwan Stock Multi-Factor Analysis System

To ensure stability and prevent crashes when adding new features or fixing bugs, the following testing plan is implemented.

## 1. Automated Testing Suite (Future Implementation)
We recommend using `pytest` for automated testing.

### A. Unit Tests (`tests/unit/`)
- **Scoring Logic:** Test each factor scoring function in `src/features/` with mock data to ensure they return values between 0.0 and 1.0.
- **Data Clients:** Use `unittest.mock` to simulate API responses from FinMind and TWSE to test `src/data/` without network dependencies.
- **Config:** Verify that `src/config.py` values are loaded correctly.

### B. Integration Tests (`tests/integration/`)
- **Model Test:** Verify that `MultiFactorModel` correctly combines all scores.
- **Backtest Engine:** Run a short backtest with dummy data to ensure the engine doesn't crash.
- **CLI Flow:** Use `click.testing.CliRunner` to simulate user commands.

## 2. Manual Verification Checklist (Before Release)
- [ ] Run `python3 src/main.py check-api` to verify connectivity.
- [ ] Run `python3 src/main.py analyze 2330` to check the accuracy analysis and report generation.
- [ ] Run `python3 src/main.py score --max-stocks 5` to verify batch processing.
- [ ] Launch `python3 src/main.py dashboard` and verify the web interface loads.

## 3. Continuous Integration (CI)
- Set up **GitHub Actions** to:
    - Run `ruff` or `flake8` for linting.
    - Run `pytest` on every push to `main` or `feat_*` branches.
    - Verify Docker build success.

## 4. Error Handling Standards
- Always use `loguru` to capture stack traces.
- Wrap data fetching in `try-except` blocks (as seen in `MultiFactorModel.safe_fetch`).
- Provide meaningful error messages to users via the CLI instead of raw Python tracebacks.
