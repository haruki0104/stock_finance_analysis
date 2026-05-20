import backtrader as bt
from loguru import logger
from src.config import TOP_N_STOCKS


class MultiFactorRotationStrategy(bt.Strategy):
    params = (
        ("top_n", TOP_N_STOCKS),
        ("rebalance_day", 4),
    )

    def __init__(self):
        self.smas5 = {}
        self.smas20 = {}
        self.smas60 = {}
        self.rsis = {}
        for data in self.datas:
            self.smas5[data._name] = bt.ind.SMA(data.close, period=5)
            self.smas20[data._name] = bt.ind.SMA(data.close, period=20)
            self.rsis[data._name] = bt.ind.RSI(data.close, period=14)
            if len(data) > 60:
                self.smas60[data._name] = bt.ind.SMA(data.close, period=60)

    def next(self):
        current_date = self.datas[0].datetime.date(0)
        if current_date.weekday() != self.params.rebalance_day:
            return
        if len(self) < 60:
            return
        self.rebalance()

    def rebalance(self):
        scores = {}
        for data in self.datas:
            sid = data._name
            score = 0.5
            close = data.close[0]

            ma5 = self.smas5[sid][0] if sid in self.smas5 else close
            ma20 = self.smas20[sid][0] if sid in self.smas20 else close
            ma60 = self.smas60[sid][0] if sid in self.smas60 else close
            rsi = self.rsis[sid][0] if sid in self.rsis else 50

            if close > ma20:
                score += 0.15
            if close > ma60:
                score += 0.15
            if ma20 > ma60:
                score += 0.10
            if 30 <= rsi <= 70:
                score += 0.10
            if rsi < 30:
                score += 0.20

            scores[sid] = score

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_stocks = [s[0] for s in ranked[:self.params.top_n]]

        target_per = self.broker.getvalue() / max(len(top_stocks), 1)

        for data in self.datas:
            sid = data._name
            pos = self.getposition(data).size
            close = data.close[0]

            if sid in top_stocks:
                if close > 0:
                    target_size = int(target_per / close / 1000) * 1000
                    if target_size > 0:
                        diff = target_size - pos
                        if diff > 500:
                            self.buy(data=data, size=diff)
                        elif diff < -500:
                            self.sell(data=data, size=abs(diff))
            elif pos > 0:
                self.sell(data=data, size=pos)


class BuyAndHoldStrategy(bt.Strategy):
    def __init__(self):
        self.ordered = False

    def next(self):
        if not self.ordered and len(self) >= 20:
            per_stock = self.broker.getvalue() / max(len(self.datas), 1)
            for data in self.datas:
                close = data.close[0]
                if close > 0:
                    size = int(per_stock / close / 1000) * 1000
                    if size > 0:
                        self.buy(data=data, size=size)
            self.ordered = True
