import pandas as pd
import numpy as np
from loguru import logger


def calc_fundamental_score(stock_id: str, price_df: pd.DataFrame,
                           revenue_df: pd.DataFrame, per_df: pd.DataFrame,
                           dividend_df: pd.DataFrame) -> float:
    score = 0.0
    n_signals = 0

    rev_score = _revenue_growth_score(revenue_df)
    if rev_score is not None:
        score += rev_score * 0.30
        n_signals += 1

    per_score = _valuation_score(price_df, per_df)
    if per_score is not None:
        score += per_score * 0.25
        n_signals += 1

    div_score = _dividend_score(dividend_df)
    if div_score is not None:
        score += div_score * 0.20
        n_signals += 1

    mom_score = _earnings_momentum_score(revenue_df)
    if mom_score is not None:
        score += mom_score * 0.25
        n_signals += 1

    if n_signals == 0:
        return 0.5
    return score


def _revenue_growth_score(revenue_df: pd.DataFrame) -> float | None:
    if revenue_df.empty or "revenue" not in revenue_df.columns:
        return None
    df = revenue_df.sort_values("date").tail(12)
    if len(df) < 4:
        return None
    recent = df["revenue"].iloc[-1]
    prev = df["revenue"].iloc[-13] if len(df) >= 13 else df["revenue"].iloc[0]
    if prev <= 0:
        return 0.5
    yoy_growth = (recent - prev) / prev
    if yoy_growth > 0.3:
        return 1.0
    if yoy_growth > 0.1:
        return 0.8
    if yoy_growth > 0.0:
        return 0.6
    if yoy_growth > -0.1:
        return 0.4
    return 0.2


def _valuation_score(price_df: pd.DataFrame, per_df: pd.DataFrame) -> float | None:
    if per_df.empty or "PER" not in per_df.columns:
        return None
    recent = per_df.dropna(subset=["PER"]).tail(60)
    if len(recent) < 10:
        return None
    current_per = recent["PER"].iloc[-1]
    if current_per <= 0:
        return 0.5
    mean_per = recent["PER"].mean()
    std_per = recent["PER"].std()
    if std_per == 0:
        return 0.5
    z = (current_per - mean_per) / std_per
    if z < -1.5:
        return 0.9
    if z < -0.5:
        return 0.7
    if z < 0.5:
        return 0.5
    if z < 1.5:
        return 0.3
    return 0.1


def _dividend_score(dividend_df: pd.DataFrame) -> float | None:
    if dividend_df.empty:
        return None
    df = dividend_df.sort_values("date").tail(3)
    if df.empty or "cash_dividend" not in df.columns:
        return None
    avg_div = df["cash_dividend"].mean()
    if avg_div > 5:
        return 1.0
    if avg_div > 3:
        return 0.8
    if avg_div > 1:
        return 0.6
    if avg_div > 0.5:
        return 0.4
    if avg_div > 0:
        return 0.2
    return 0.0


def _earnings_momentum_score(revenue_df: pd.DataFrame) -> float | None:
    if revenue_df.empty or "revenue" not in revenue_df.columns:
        return None
    df = revenue_df.sort_values("date").tail(6)
    if len(df) < 4:
        return None
    growth_rates = []
    for i in range(1, len(df)):
        prev = df["revenue"].iloc[i - 1]
        if prev > 0:
            growth_rates.append((df["revenue"].iloc[i] - prev) / prev)
    if not growth_rates:
        return 0.5
    recent_3 = np.mean(growth_rates[-3:]) if len(growth_rates) >= 3 else np.mean(growth_rates)
    all_avg = np.mean(growth_rates)
    if recent_3 > all_avg * 1.5:
        return 1.0
    if recent_3 > all_avg:
        return 0.7
    if recent_3 > 0:
        return 0.5
    return 0.2
