import pandas as pd
from loguru import logger


def get_all_stocks(client) -> pd.DataFrame:
    df = client.all_stock_info()
    if df.empty:
        logger.warning("No stock info from data client, fallback to hardcoded list")
        return _fallback_stocks()

    df = df.copy()
    if "stock_id" not in df.columns and "code" in df.columns:
        df = df.rename(columns={"code": "stock_id"})
    if "stock_name" not in df.columns and "name" in df.columns:
        df = df.rename(columns={"name": "stock_name"})

    if "industry_category" in df.columns:
        df = df[df["industry_category"].fillna("") != ""]
    if "type" in df.columns:
        df = df[df["type"].isin(["twse", "tpex"])].copy()
    elif "market" in df.columns:
        df = df[df["market"].isin(["TWSE", "TPEx"])].copy()

    if "stock_id" not in df.columns:
        return _fallback_stocks()

    df["stock_id"] = df["stock_id"].astype(str).str.strip()
    df = df[df["stock_id"].str.match(r"^\d{4}$") != False]
    if df.empty:
        return _fallback_stocks()

    for col in ["stock_name", "industry_category"]:
        if col not in df.columns:
            df[col] = ""

    logger.info(f"Loaded {len(df)} common stocks")
    return df[["stock_id", "stock_name", "industry_category"]].drop_duplicates()


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


def filter_tradable(df: pd.DataFrame, price_df: pd.DataFrame) -> pd.DataFrame:
    recent = price_df.groupby("stock_id").last().reset_index()
    avg_price = price_df.groupby("stock_id")["Close"].mean().reset_index()
    merged = df.merge(recent[["stock_id", "Volume"]], on="stock_id", how="inner")
    merged = merged.merge(avg_price[["stock_id", "Close"]], on="stock_id", how="inner")
    mask = (merged["Volume"] > 500000) & (merged["Close"] > 5) & (merged["Close"] < 1000)
    result = merged[mask]
    logger.info(f"Filtered to {len(result)} tradable stocks")
    return result
