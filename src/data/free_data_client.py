from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import pandas as pd
import requests
from loguru import logger

from src.config import CACHE_EXPIRE_DAYS
from src.data.cache_manager import get_cached, set_cache
from src.data.finmind_client import FinMindClient


HEADERS = {"User-Agent": "Mozilla/5.0"}
TWSE_BASE = "https://www.twse.com.tw"
TWSE_OPENAPI = "https://openapi.twse.com.tw/v1"


class FreeDataClient:
    def __init__(self):
        self._session = requests.Session()
        self._session.headers.update(HEADERS)
        self._fm = FinMindClient()

    def _twse_date(self, dt: datetime) -> str:
        return dt.strftime("%Y%m%d")

    def _parse_twse_date(self, date_str: str) -> str:
        d = date_str.replace("/", "").split()[0]
        y = int(d[:3]) + 1911
        return f"{y:04d}-{d[3:5]}-{d[5:7]}"

    def stock_price(self, stock_id: str, start_date: str, end_date: str) -> pd.DataFrame:
        key = "free_TaiwanStockPrice"
        cache = get_cached(key, stock_id, start_date, end_date, CACHE_EXPIRE_DAYS)
        if cache is not None and not cache.empty:
            return cache

        df = self._fm.stock_price(stock_id, start_date, end_date)
        if not df.empty:
            set_cache(key, df, stock_id, start_date, end_date)
            return df

        df = self._twse_stock_day(stock_id, start_date, end_date)
        if not df.empty:
            set_cache(key, df, stock_id, start_date, end_date)
        return df

    def _twse_stock_day(self, stock_id: str, start_date: str, end_date: str) -> pd.DataFrame:
        start_dt = datetime.strptime(start_date[:10], "%Y-%m-%d")
        end_dt = datetime.strptime(end_date[:10], "%Y-%m-%d")
        months = []
        current = start_dt.replace(day=1)
        while current <= end_dt:
            months.append(self._twse_date(current))
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)

        def fetch_month(date_str):
            try:
                resp = self._session.get(
                    f"{TWSE_BASE}/exchangeReport/STOCK_DAY?response=json&date={date_str}&stockNo={stock_id}",
                    timeout=15,
                )
                data = resp.json()
                if data.get("stat") == "OK" and data.get("data"):
                    return [
                        {
                            "date": self._parse_twse_date(r[0]),
                            "stock_id": stock_id,
                            "Open": float(r[2].replace(",", "")),
                            "High": float(r[3].replace(",", "")),
                            "Low": float(r[4].replace(",", "")),
                            "Close": float(r[5].replace(",", "")),
                            "Volume": int(r[1].replace(",", "")),
                            "Amount": float(r[6].replace(",", "")),
                            "Change": float(r[7].replace(",", "")),
                        }
                        for r in data["data"]
                    ]
            except Exception as e:
                logger.debug(f"STOCK_DAY fail {stock_id} {date_str}: {e}")
            return []

        records = []
        with ThreadPoolExecutor(max_workers=8) as ex:
            for fut in as_completed({ex.submit(fetch_month, m): m for m in months}):
                records.extend(fut.result())

        df = pd.DataFrame(records)
        if df.empty:
            return df
        df["date"] = pd.to_datetime(df["date"])
        mask = (df["date"] >= start_dt) & (df["date"] <= end_dt)
        return df[mask].sort_values("date").drop_duplicates(subset=["date"]).reset_index(drop=True)

    def per_pbr_list(self) -> pd.DataFrame:
        key = "free_PER_PBR_list"
        cache = get_cached(key, "", "", "", CACHE_EXPIRE_DAYS)
        if cache is not None and not cache.empty:
            return cache

        try:
            resp = self._session.get(f"{TWSE_OPENAPI}/exchangeReport/BWIBBU_d", timeout=15)
            data = resp.json()
            rows = [
                {
                    "stock_id": item["Code"],
                    "stock_name": item.get("Name", ""),
                    "close_price": float(item.get("ClosePrice", 0) or 0),
                    "dividend_yield": float(item.get("DividendYield", 0) or 0),
                    "PER": float(item.get("PEratio", 0) or 0) if item.get("PEratio", "") else None,
                    "PBR": float(item.get("PBratio", 0) or 0),
                }
                for item in data
            ]
            df = pd.DataFrame(rows)
            set_cache(key, df, "", "", "")
            return df
        except Exception as e:
            logger.warning(f"PER/PBR API failed: {e}")
            return pd.DataFrame()

    def per_pbr(self, stock_id: str, start_date: str = "", end_date: str = "") -> pd.DataFrame:
        all_data = self.per_pbr_list()
        if all_data.empty:
            return pd.DataFrame()
        result = all_data[all_data["stock_id"] == stock_id].copy()
        if not result.empty:
            result["date"] = datetime.now().strftime("%Y-%m-%d")
        return result

    def month_revenue(self, stock_id: str, start_date: str, end_date: str) -> pd.DataFrame:
        return self._fm.month_revenue(stock_id, start_date, end_date)

    def institutional_investors(self, stock_id: str, start_date: str, end_date: str) -> pd.DataFrame:
        return self._fm.institutional_investors(stock_id, start_date, end_date)

    def margin_short_sale(self, stock_id: str, start_date: str, end_date: str) -> pd.DataFrame:
        return self._fm.margin_short_sale(stock_id, start_date, end_date)

    def dividend(self, stock_id: str, start_date: str, end_date: str) -> pd.DataFrame:
        return self._fm.dividend(stock_id, start_date, end_date)

    def all_stock_info(self) -> pd.DataFrame:
        key = "free_stock_info"
        cache = get_cached(key, "", "", "", CACHE_EXPIRE_DAYS * 7)
        if cache is not None and not cache.empty:
            return cache
        df = self._fm.all_stock_info()
        if not df.empty:
            set_cache(key, df, "", "", "")
            return df
        return _fallback_stocks()

    def holding_shares(self, stock_id: str, start_date: str, end_date: str) -> pd.DataFrame:
        return self._fm.holding_shares(stock_id, start_date, end_date)

    def warrant_daily(self, stock_id: str, start_date: str, end_date: str) -> pd.DataFrame:
        return self._fm.warrant_daily(stock_id, start_date, end_date)

    def stock_daily_adj(self, stock_id: str, start_date: str, end_date: str) -> pd.DataFrame:
        return self._fm.stock_daily_adj(stock_id, start_date, end_date)


def _fallback_stocks() -> pd.DataFrame:
    stocks = [
        ("2330", "台積電", "半導體"),
        ("2317", "鴻海", "其他電子"),
        ("2454", "聯發科", "半導體"),
        ("2412", "中華電", "通信網路"),
        ("2881", "富邦金", "金融"),
        ("2882", "國泰金", "金融"),
        ("2308", "台達電", "電機"),
        ("2382", "廣達", "電腦週邊"),
        ("1301", "台塑", "塑膠"),
        ("1303", "南亞", "塑膠"),
    ]
    return pd.DataFrame(stocks, columns=["stock_id", "stock_name", "industry_category"])
