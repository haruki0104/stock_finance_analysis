from pathlib import Path
from loguru import logger
import os

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CACHE_DB_PATH = DATA_DIR / "cache.db"
REPORT_DIR = PROJECT_ROOT / "reports"

DATA_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

BACKTEST_START = "2023-06-01"
BACKTEST_END = "2026-05-01"

TRADING_FEE_RATE = 0.001425
TAX_RATE = 0.003
SLIPPAGE = 0.001

SCORE_WEIGHTS = {
    "fundamental": 0.30,
    "institutional": 0.25,
    "technical": 0.20,
    "warrant": 0.10,
    "sentiment": 0.15,
}

REBALANCE_FREQ = "W"
TOP_N_STOCKS = 10
CACHE_EXPIRE_DAYS = 1

SCHEDULE_TIME = "18:30"
SCHEDULE_DAYS = [0, 1, 2, 3, 4]
