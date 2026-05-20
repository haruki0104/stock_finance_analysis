import pandas as pd
import numpy as np
from loguru import logger

from src.config import TOP_N_STOCKS


SignalType = str  # "BUY" | "SELL" | "HOLD"


def generate_signals(scores_df: pd.DataFrame, prev_holdings: list[str] = None) -> pd.DataFrame:
    if scores_df.empty:
        return pd.DataFrame()

    scores_df = scores_df.copy()

    scores_df["signal"] = "HOLD"

    top_n = scores_df.head(TOP_N_STOCKS)
    scores_df.loc[top_n.index, "signal"] = "BUY"

    if prev_holdings:
        dropped = [s for s in prev_holdings if s not in top_n["stock_id"].values]
        scores_df.loc[scores_df["stock_id"].isin(dropped), "signal"] = "SELL"

    logger.info(f"Generated {len(top_n)} BUY signals, {len(prev_holdings or []) - len(top_n)} SELL signals")
    return scores_df


def filter_high_conviction(scores_df: pd.DataFrame,
                           min_total_score: float = 0.6) -> pd.DataFrame:
    return scores_df[
        (scores_df["total_score"] >= min_total_score)
        & (scores_df["signal"] == "BUY")
    ].copy()
