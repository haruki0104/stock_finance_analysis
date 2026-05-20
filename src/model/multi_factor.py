import pandas as pd
import numpy as np
from loguru import logger
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from src.config import SCORE_WEIGHTS
from src.features.fundamental import calc_fundamental_score
from src.features.institutional import calc_institutional_score
from src.features.technical import calc_technical_score
from src.features.warrant import calc_warrant_score
from src.features.sentiment import calc_sentiment_score


def safe_fetch(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        logger.debug(f"Data fetch failed ({fn.__name__}): {e}")
        return pd.DataFrame()


class MultiFactorModel:
    def __init__(self, client):
        self.client = client

    def score_stock(self, stock_id: str, start_date: str, end_date: str) -> dict | None:
        try:
            price = safe_fetch(self.client.stock_price, stock_id, start_date, end_date)
            revenue = safe_fetch(self.client.month_revenue, stock_id, start_date, end_date)
            per = safe_fetch(self.client.per_pbr, stock_id, start_date, end_date)
            dividend = safe_fetch(self.client.dividend, stock_id, start_date, end_date)
            inst = safe_fetch(self.client.institutional_investors, stock_id, start_date, end_date)
            margin = safe_fetch(self.client.margin_short_sale, stock_id, start_date, end_date)
            holdings = pd.DataFrame()
            try:
                holdings = self.client.holding_shares(stock_id, start_date, end_date)
            except Exception:
                pass
            warrant = pd.DataFrame()
            try:
                warrant = self.client.warrant_daily(stock_id, start_date, end_date)
            except Exception:
                pass

            if price.empty or len(price) < 20:
                return None

            fundamental = calc_fundamental_score(stock_id, price, revenue, per, dividend)
            institutional = calc_institutional_score(stock_id, inst)
            technical = calc_technical_score(stock_id, price)
            warrant_s = calc_warrant_score(stock_id, warrant)
            sentiment = calc_sentiment_score(stock_id, margin, holdings)

            total = (
                fundamental * SCORE_WEIGHTS["fundamental"]
                + institutional * SCORE_WEIGHTS["institutional"]
                + technical * SCORE_WEIGHTS["technical"]
                + warrant_s * SCORE_WEIGHTS["warrant"]
                + sentiment * SCORE_WEIGHTS["sentiment"]
            )

            return {
                "stock_id": stock_id,
                "total_score": round(total, 4),
                "fundamental": round(fundamental, 4),
                "institutional": round(institutional, 4),
                "technical": round(technical, 4),
                "warrant": round(warrant_s, 4),
                "sentiment": round(sentiment, 4),
                "close_price": round(price["Close"].iloc[-1], 2) if "Close" in price.columns else 0,
            }
        except Exception as e:
            logger.debug(f"Failed to score {stock_id}: {e}")
            return None

    def score_universe(self, stock_ids: list, start_date: str,
                       end_date: str, max_workers: int = 5) -> pd.DataFrame:
        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            fut_map = {
                executor.submit(self.score_stock, sid, start_date, end_date): sid
                for sid in stock_ids
            }
            for fut in tqdm(as_completed(fut_map), total=len(fut_map), desc="Scoring stocks"):
                result = fut.result()
                if result:
                    results.append(result)

        df = pd.DataFrame(results)
        if not df.empty:
            df = df.sort_values("total_score", ascending=False).reset_index(drop=True)
            df["rank"] = range(1, len(df) + 1)
        return df
