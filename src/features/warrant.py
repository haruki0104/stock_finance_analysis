import pandas as pd
import numpy as np
from loguru import logger


def calc_warrant_score(stock_id: str, warrant_df: pd.DataFrame) -> float:
    if warrant_df.empty or len(warrant_df) < 5:
        return 0.5

    score = 0.0
    n_signals = 0

    vol_score = _warrant_volume_trend(warrant_df)
    if vol_score is not None:
        score += vol_score * 0.50
        n_signals += 1

    cp_ratio_score = _call_put_ratio(warrant_df)
    if cp_ratio_score is not None:
        score += cp_ratio_score * 0.50
        n_signals += 1

    if n_signals == 0:
        return 0.5
    return score


def _warrant_volume_trend(df: pd.DataFrame) -> float | None:
    if "volume" not in df.columns and "Volume" not in df.columns:
        return None
    vol_col = "Volume" if "Volume" in df.columns else "volume"
    d = df.sort_values("date")
    recent = d[vol_col].tail(10).mean()
    prior = d[vol_col].tail(30).head(20).mean() if len(d) >= 30 else d[vol_col].mean()
    if prior <= 0:
        return 0.5
    ratio = recent / prior

    if ratio > 2.0:
        return 1.0
    if ratio > 1.5:
        return 0.8
    if ratio > 1.0:
        return 0.6
    if ratio > 0.7:
        return 0.4
    return 0.2


def _call_put_ratio(df: pd.DataFrame) -> float | None:
    if "call_volume" not in df.columns and "put_volume" not in df.columns:
        return _infer_call_put(df)
    d = df.sort_values("date").tail(10)
    calls = d["call_volume"].sum()
    puts = d["put_volume"].sum()
    if puts == 0:
        return 0.6
    ratio = calls / puts
    if ratio > 1.5:
        return 0.8
    if ratio > 1.0:
        return 0.6
    if ratio > 0.7:
        return 0.4
    return 0.2


def _infer_call_put(df: pd.DataFrame) -> float | None:
    price_cols = [c for c in df.columns if "price" in c.lower() and "strike" in c.lower()]
    if not price_cols:
        return None
    return 0.5
