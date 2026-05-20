import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from loguru import logger

from src.data.free_data_client import FreeDataClient
from src.features.fundamental import calc_fundamental_score
from src.features.institutional import calc_institutional_score
from src.features.technical import calc_technical_score
from src.features.warrant import calc_warrant_score
from src.features.sentiment import calc_sentiment_score
from src.config import SCORE_WEIGHTS


def analyze_stock(stock_id: str, years: int = 2) -> dict:
    client = FreeDataClient()
    end = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - timedelta(days=int(years * 365))).strftime("%Y-%m-%d")

    logger.info(f"Analyzing {stock_id} from {start} to {end}")

    price = client.stock_price(stock_id, start, end)
    if price.empty or len(price) < 20:
        return {"stock_id": stock_id, "error": "Insufficient price data"}

    revenue = client.month_revenue(stock_id, start, end)
    per_df = client.per_pbr(stock_id)
    dividend = client.dividend(stock_id, start, end)
    inst = client.institutional_investors(stock_id, start, end)
    margin = client.margin_short_sale(stock_id, start, end)
    holdings = client.holding_shares(stock_id, start, end)
    warrant = client.warrant_daily(stock_id, start, end)
    info = client.all_stock_info()
    stock_name = ""
    industry = ""
    if not info.empty:
        match = info[info["stock_id"] == stock_id]
        if not match.empty:
            stock_name = match.iloc[0].get("stock_name", "")
            industry = match.iloc[0].get("industry_category", "")

    fundamental = calc_fundamental_score(stock_id, price, revenue, per_df, dividend)
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

    close_prices = price["Close"].values
    current_price = float(close_prices[-1]) if len(close_prices) > 0 else 0
    price_1y_ago = float(close_prices[0]) if len(close_prices) > 0 else 0
    price_change_1y = ((current_price - price_1y_ago) / price_1y_ago * 100) if price_1y_ago > 0 else 0

    ma20 = pd.Series(close_prices).rolling(20).mean().iloc[-1] if len(close_prices) >= 20 else current_price
    ma60 = pd.Series(close_prices).rolling(60).mean().iloc[-1] if len(close_prices) >= 60 else current_price

    signal = "BUY" if total >= 0.45 else ("SELL" if total < 0.30 else "HOLD")

    details = {
        "stock_id": stock_id,
        "stock_name": stock_name,
        "industry": industry,
        "analysis_period": f"{start} ~ {end}",
        "current_price": current_price,
        "price_change_1y_pct": round(price_change_1y, 2),
        "ma20": round(float(ma20), 2),
        "ma60": round(float(ma60), 2),
        "total_score": round(total, 4),
        "signal": signal,
        "scores": {
            "fundamental": {"score": round(fundamental, 4), "weight": SCORE_WEIGHTS["fundamental"],
                            "description": "營收成長、本益比、股利"},
            "institutional": {"score": round(institutional, 4), "weight": SCORE_WEIGHTS["institutional"],
                              "description": "三大法人買賣超、外資動向"},
            "technical": {"score": round(technical, 4), "weight": SCORE_WEIGHTS["technical"],
                          "description": "均線排列、RSI、MACD、成交量"},
            "warrant": {"score": round(warrant_s, 4), "weight": SCORE_WEIGHTS["warrant"],
                        "description": "權證成交量變化"},
            "sentiment": {"score": round(sentiment, 4), "weight": SCORE_WEIGHTS["sentiment"],
                          "description": "融資融券、股權集中度"},
        },
        "price_trend": {
            "last_5": [float(x) for x in close_prices[-5:]] if len(close_prices) >= 5 else [],
            "high_1y": float(np.max(close_prices)) if len(close_prices) > 0 else 0,
            "low_1y": float(np.min(close_prices)) if len(close_prices) > 0 else 0,
        },
    }

    recommendations = []
    if total >= 0.45:
        recommendations.append("綜合評分良好，可考慮建立部位")
    elif total >= 0.35:
        recommendations.append("評分中等，建議觀察")
    else:
        recommendations.append("評分偏低，謹慎操作")

    if fundamental >= 0.6:
        recommendations.append("基本面穩健")
    elif fundamental < 0.3:
        recommendations.append("基本面需留意")

    if institutional >= 0.5:
        recommendations.append("法人近期偏多")
    elif institutional < 0.3:
        recommendations.append("法人近期偏空")

    if technical >= 0.6:
        recommendations.append("技術面偏多")
    elif technical < 0.3:
        recommendations.append("技術面偏弱")

    details["recommendations"] = recommendations
    return details


def print_analysis_report(details: dict):
    if "error" in details:
        print(f"\n  ❌ {details['stock_id']}: {details['error']}")
        return

    sid = details["stock_id"]
    name = details.get("stock_name", "")
    industry = details.get("industry", "")
    price = details.get("current_price", 0)
    signal = details.get("signal", "HOLD")
    total = details.get("total_score", 0)

    signal_color = {"BUY": "🟢", "SELL": "🔴", "HOLD": "🟡"}
    sig = signal_color.get(signal, "⚪")

    print(f"\n{'='*55}")
    print(f"  {sig}  {sid} {name} ({industry})")
    print(f"  分析期間: {details.get('analysis_period', 'N/A')}")
    print(f"  現價: {price:.2f}  |  1年漲跌: {details.get('price_change_1y_pct', 0):+.2f}%")
    print(f"  MA20: {details.get('ma20', 0):.2f}  |  MA60: {details.get('ma60', 0):.2f}")
    print(f"  最高(1年): {details['price_trend']['high_1y']:.2f}  |  最低(1年): {details['price_trend']['low_1y']:.2f}")
    print(f"{'='*55}")
    print(f"  總評分: {total:.4f}  →  訊號: {signal}")
    print(f"{'='*55}")
    print(f"  各維度評分:")
    for name, sc in details.get("scores", {}).items():
        bar = "█" * int(sc["score"] * 20) + "░" * (20 - int(sc["score"] * 20))
        print(f"    {name:15s} {bar} {sc['score']:.3f} (權重{sc['weight']*100:.0f}%) - {sc['description']}")
    print(f"{'='*55}")
    print(f"  建議:")
    for rec in details.get("recommendations", []):
        print(f"    • {rec}")
    print(f"{'='*55}\n")
