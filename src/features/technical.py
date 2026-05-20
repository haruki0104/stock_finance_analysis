import pandas as pd
import numpy as np
from loguru import logger


def calc_technical_score(stock_id: str, price_df: pd.DataFrame) -> float:
    if price_df.empty or len(price_df) < 60:
        return 0.5

    df = price_df.sort_values("date").copy()
    score = 0.0
    n_signals = 0

    ma_score = _ma_trend_score(df)
    if ma_score is not None:
        score += ma_score * 0.35
        n_signals += 1

    rsi_score = _rsi_score(df)
    if rsi_score is not None:
        score += rsi_score * 0.20
        n_signals += 1

    macd_score = _macd_score(df)
    if macd_score is not None:
        score += macd_score * 0.25
        n_signals += 1

    vol_score = _volume_score(df)
    if vol_score is not None:
        score += vol_score * 0.20
        n_signals += 1

    if n_signals == 0:
        return 0.5
    return score


def _ma_trend_score(df: pd.DataFrame) -> float | None:
    close = df["Close"].values
    if len(close) < 60:
        return None
    ma5 = pd.Series(close).rolling(5).mean().values
    ma20 = pd.Series(close).rolling(20).mean().values
    ma60 = pd.Series(close).rolling(60).mean().values

    current = close[-1]
    if current > ma20[-1] > ma60[-1]:
        return 1.0
    if current > ma5[-1] > ma20[-1]:
        return 0.9
    if current > ma20[-1]:
        return 0.7
    if current > ma60[-1]:
        return 0.5
    if current > ma5[-1]:
        return 0.4
    return 0.2


def _rsi_score(df: pd.DataFrame) -> float | None:
    close = df["Close"].values
    if len(close) < 15:
        return None
    rsi = _compute_rsi(close, 14)
    current_rsi = rsi[-1]
    if 40 <= current_rsi <= 60:
        return 0.5
    if 30 <= current_rsi < 40:
        return 0.7
    if current_rsi < 30:
        return 0.9
    if 60 < current_rsi <= 70:
        return 0.3
    if current_rsi > 70:
        return 0.1
    return 0.5


def _compute_rsi(prices: np.ndarray, period: int = 14) -> np.ndarray:
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = pd.Series(gains).rolling(period, min_periods=period).mean().values
    avg_loss = pd.Series(losses).rolling(period, min_periods=period).mean().values
    rs = np.divide(avg_gain, avg_loss, out=np.zeros_like(avg_gain), where=avg_loss != 0)
    rsi = 100 - (100 / (1 + rs))
    return np.concatenate([np.full(period, np.nan), rsi])[:len(prices)]


def _macd_score(df: pd.DataFrame) -> float | None:
    close = df["Close"].values
    if len(close) < 26:
        return None
    ema12 = pd.Series(close).ewm(span=12).mean().values
    ema26 = pd.Series(close).ewm(span=26).mean().values
    macd_line = ema12 - ema26
    signal = pd.Series(macd_line).ewm(span=9).mean().values

    prev_macd = macd_line[-2] if len(macd_line) >= 2 else macd_line[-1]
    prev_signal = signal[-2] if len(signal) >= 2 else signal[-1]
    curr_macd = macd_line[-1]
    curr_signal = signal[-1]

    if prev_macd <= prev_signal and curr_macd > curr_signal:
        return 1.0
    if curr_macd > curr_signal:
        return 0.7
    if prev_macd >= prev_signal and curr_macd < curr_signal:
        return 0.3
    return 0.4


def _volume_score(df: pd.DataFrame) -> float | None:
    if "Volume" not in df.columns or len(df) < 20:
        return None
    volumes = df["Volume"].values
    avg_vol_20 = pd.Series(volumes).rolling(20).mean().values
    recent_vol = volumes[-5:].mean()
    avg_vol = avg_vol_20[-1]
    if avg_vol <= 0:
        return 0.5
    ratio = recent_vol / avg_vol
    close = df["Close"].values
    price_up = close[-1] > close[-6] if len(close) >= 6 else False
    if ratio > 1.5 and price_up:
        return 1.0
    if ratio > 1.2 and price_up:
        return 0.8
    if ratio > 1.0:
        return 0.6
    if ratio > 0.7:
        return 0.4
    return 0.2
