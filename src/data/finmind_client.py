import os

import pandas as pd
from loguru import logger

from src.config import CACHE_EXPIRE_DAYS
from src.data.cache_manager import get_cached, set_cache

try:
    from FinMind.data import DataLoader
except ImportError:
    DataLoader = None


FINMIND_TOKEN = os.environ.get("FINMIND_TOKEN", "")

COLUMN_NORMALIZE = {
    "Trading_Volume": "Volume",
    "Trading_money": "Amount",
    "open": "Open",
    "max": "High",
    "min": "Low",
    "close": "Close",
    "spread": "Change",
    "Trading_turnover": "Turnover",
}


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
    df = df.rename(columns=COLUMN_NORMALIZE)
    return df.loc[:, ~df.columns.duplicated()]


class FinMindClient:
    def __init__(self):
        self.loader = DataLoader() if DataLoader else None
        if self.loader is None:
            logger.warning("FinMind package is not installed")
        elif FINMIND_TOKEN:
            self.loader.login_by_token(FINMIND_TOKEN)
            logger.info("FinMind logged in with token")
        else:
            logger.info("FinMind in anonymous mode (300 req/hr)")

    def _load(self, dataset: str, stock_id: str, start_date: str, end_date: str, fn_name: str) -> pd.DataFrame:
        key = f"finmind_{dataset}"
        cached = get_cached(key, stock_id, start_date, end_date, CACHE_EXPIRE_DAYS)
        if cached is not None and not cached.empty:
            return cached
        if self.loader is None:
            return pd.DataFrame()
        try:
            fn = getattr(self.loader, fn_name)
            df = fn(stock_id=stock_id, start_date=start_date, end_date=end_date)
        except Exception as e:
            logger.debug(f"FinMind {dataset} failed for {stock_id}: {e}")
            return pd.DataFrame()
        if df is None or df.empty:
            return pd.DataFrame()
        if dataset in {"TaiwanStockPrice", "TaiwanStockDailyAdj"}:
            df = _normalize(df)
        set_cache(key, df, stock_id, start_date, end_date)
        return df

    def stock_price(self, stock_id: str, start_date: str, end_date: str) -> pd.DataFrame:
        return self._load("TaiwanStockPrice", stock_id, start_date, end_date, "taiwan_stock_daily")

    def month_revenue(self, stock_id: str, start_date: str, end_date: str) -> pd.DataFrame:
        return self._load("TaiwanStockMonthRevenue", stock_id, start_date, end_date, "taiwan_stock_month_revenue")

    def institutional_investors(self, stock_id: str, start_date: str, end_date: str) -> pd.DataFrame:
        return self._load(
            "TaiwanStockInstitutionalInvestors",
            stock_id,
            start_date,
            end_date,
            "taiwan_stock_institutional_investors",
        )

    def margin_short_sale(self, stock_id: str, start_date: str, end_date: str) -> pd.DataFrame:
        return self._load(
            "TaiwanStockMarginShort",
            stock_id,
            start_date,
            end_date,
            "taiwan_stock_margin_purchase_short_sale",
        )

    def per_pbr(self, stock_id: str, start_date: str, end_date: str) -> pd.DataFrame:
        return self._load("TaiwanStockPerPbr", stock_id, start_date, end_date, "taiwan_stock_per_pbr")

    def holding_shares(self, stock_id: str, start_date: str, end_date: str) -> pd.DataFrame:
        return self._load(
            "TaiwanStockHoldingShares",
            stock_id,
            start_date,
            end_date,
            "taiwan_stock_holding_shares_per",
        )

    def warrant_daily(self, stock_id: str, start_date: str, end_date: str) -> pd.DataFrame:
        return self._load(
            "TaiwanStockWarrant",
            stock_id,
            start_date,
            end_date,
            "taiwan_stock_warrant_trading_daily_report",
        )

    def dividend(self, stock_id: str, start_date: str, end_date: str) -> pd.DataFrame:
        return self._load("TaiwanStockDividend", stock_id, start_date, end_date, "taiwan_stock_dividend")

    def financial_statement(self, stock_id: str, start_date: str, end_date: str) -> pd.DataFrame:
        return self._load(
            "TaiwanStockFinancialStatement",
            stock_id,
            start_date,
            end_date,
            "taiwan_stock_financial_statement",
        )

    def all_stock_info(self) -> pd.DataFrame:
        key = "finmind_TaiwanStockInfo"
        cached = get_cached(key, "", "", "", CACHE_EXPIRE_DAYS * 7)
        if cached is not None and not cached.empty:
            return cached
        if self.loader is None:
            return pd.DataFrame()
        try:
            df = self.loader.taiwan_stock_info()
        except Exception as e:
            logger.debug(f"FinMind stock info failed: {e}")
            return pd.DataFrame()
        if df is None or df.empty:
            return pd.DataFrame()
        set_cache(key, df, "", "", "")
        return df

    def stock_daily_adj(self, stock_id: str, start_date: str, end_date: str) -> pd.DataFrame:
        return self._load("TaiwanStockDailyAdj", stock_id, start_date, end_date, "taiwan_stock_daily_adj")
