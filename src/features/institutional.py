import pandas as pd
import numpy as np
from loguru import logger


def calc_institutional_score(stock_id: str, inst_df: pd.DataFrame) -> float:
    score = 0.0
    n_signals = 0

    net_score = _net_buy_sell_trend(inst_df)
    if net_score is not None:
        score += net_score * 0.50
        n_signals += 1

    foreign_score = _foreign_investor_trend(inst_df)
    if foreign_score is not None:
        score += foreign_score * 0.30
        n_signals += 1

    consensus_score = _institution_consensus(inst_df)
    if consensus_score is not None:
        score += consensus_score * 0.20
        n_signals += 1

    if n_signals == 0:
        return 0.5
    return score


def _net_buy_sell_trend(inst_df: pd.DataFrame) -> float | None:
    if inst_df.empty:
        return None
    df = inst_df.sort_values("date").tail(20)
    if df.empty:
        return None

    if "buy" in df.columns and "sell" in df.columns:
        net = df.groupby("date")[["buy", "sell"]].sum()
        net["net"] = net["buy"] - net["sell"]
    else:
        buy_cols = [c for c in df.columns if "Buy" in c and c not in ["date", "stock_id"]]
        sell_cols = [c for c in df.columns if "Sell" in c and c not in ["date", "stock_id"]]
        if not buy_cols or not sell_cols:
            return 0.5
        net = df.groupby("date")[buy_cols + sell_cols].sum()
        net["net"] = net[buy_cols].sum(axis=1) - net[sell_cols].sum(axis=1)

    recent_net = net["net"].tail(5).mean()
    prior_net = net["net"].tail(15).head(10).mean() if len(net) >= 15 else net["net"].mean()

    if prior_net == 0:
        return 0.6 if recent_net > 0 else 0.4
    ratio = recent_net / abs(prior_net)
    if ratio > 2:
        return 0.9
    if ratio > 1:
        return 0.7
    if ratio > 0.5:
        return 0.6
    if ratio > 0:
        return 0.55
    if ratio > -0.5:
        return 0.4
    if ratio > -1:
        return 0.3
    return 0.15


def _foreign_investor_trend(inst_df: pd.DataFrame) -> float | None:
    if inst_df.empty or "name" not in inst_df.columns:
        return None
    df = inst_df.sort_values("date")
    foreign = df[df["name"].str.contains("外資", na=False)].tail(20)
    if foreign.empty:
        return None
    foreign_net = (foreign["buy"].sum() - foreign["sell"].sum())
    if foreign_net > 0:
        return 0.7
    if foreign_net > -10_000_000:
        return 0.5
    return 0.3


def _institution_consensus(inst_df: pd.DataFrame) -> float | None:
    if inst_df.empty or "name" not in inst_df.columns:
        return None
    df = inst_df.sort_values("date")
    has_foreign = "外資" in df["name"].unique()
    has_trust = "投信" in df["name"].unique()
    has_dealer = "自營商" in df["name"].unique()
    active = sum([has_foreign, has_trust, has_dealer])
    if active >= 3:
        return 0.8
    if active >= 2:
        return 0.6
    return 0.4
