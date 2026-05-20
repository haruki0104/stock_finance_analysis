import pandas as pd
import numpy as np
from loguru import logger


def calc_sentiment_score(stock_id: str, margin_df: pd.DataFrame,
                         holdings_df: pd.DataFrame) -> float:
    score = 0.0
    n_signals = 0

    margin_score = _margin_signal(margin_df)
    if margin_score is not None:
        score += margin_score * 0.60
        n_signals += 1

    holding_score = _holding_concentration(holdings_df)
    if holding_score is not None:
        score += holding_score * 0.40
        n_signals += 1

    return score / max(n_signals, 1)


def _margin_signal(margin_df: pd.DataFrame) -> float | None:
    if margin_df.empty:
        return None

    df = margin_df.sort_values("date").tail(20)
    if df.empty or len(df) < 5:
        return None

    margin_col = None
    short_col = None
    for c in df.columns:
        cl = c.lower()
        if "margin" in cl or "purchase" in cl or "buy" in cl or "finance" in cl:
            if margin_col is None:
                margin_col = c
        if "short" in cl or "sale" in cl:
            if short_col is None:
                short_col = c

    if margin_col and short_col:
        margin_balance = df[margin_col].iloc[-1] if margin_col in df.columns else 0
        short_balance = df[short_col].iloc[-1] if short_col in df.columns else 0
        if margin_balance > 0 and short_balance > 0:
            ratio = margin_balance / short_balance
        else:
            ratio = 1.0
        recent_margin_change = (df[margin_col].iloc[-1] - df[margin_col].iloc[0]) / max(df[margin_col].iloc[0], 1)
        if recent_margin_change > 0.1 and ratio > 3:
            return 0.8
        if recent_margin_change > 0:
            return 0.6
        if recent_margin_change < -0.1:
            return 0.3
        return 0.5

    num_cols = df.select_dtypes(include=[np.number]).columns
    if len(num_cols) >= 2:
        col1 = num_cols[0]
        col2 = num_cols[1]
        recent = df[col1].iloc[-1]
        old = df[col1].iloc[0]
        if old != 0 and (recent - old) / abs(old) > 0.05:
            return 0.7
    return 0.5


def _holding_concentration(holdings_df: pd.DataFrame) -> float | None:
    if holdings_df.empty:
        return None
    df = holdings_df.sort_values("date").tail(2)
    if len(df) < 2:
        return None
    level_cols = [c for c in df.columns if "level" in c.lower() or "%" in c or "percent" in c.lower()
                  or "ratio" in c.lower()]
    if not level_cols:
        return None
    try:
        recent_top = df[level_cols].iloc[-1].sum() if level_cols else 0
        prior_top = df[level_cols].iloc[-2].sum() if level_cols else 0
        if prior_top == 0:
            return 0.5
        change = (recent_top - prior_top) / prior_top
        if change > 0.02:
            return 0.8
        if change > 0:
            return 0.6
        return 0.4
    except Exception:
        return 0.5
