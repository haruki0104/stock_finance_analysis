import datetime
import backtrader as bt
import pandas as pd
from loguru import logger

from src.config import TRADING_FEE_RATE, TAX_RATE, SLIPPAGE, BACKTEST_START, BACKTEST_END


class TaiwanStockData(bt.feeds.PandasData):
    params = (
        ("datetime", None),
        ("open", "Open"),
        ("high", "High"),
        ("low", "Low"),
        ("close", "Close"),
        ("volume", "Volume"),
        ("openinterest", None),
    )


class TaiwanCommission(bt.CommInfoBase):
    params = (
        ("commission", TRADING_FEE_RATE),
        ("stocklike", True),
        ("commtype", bt.CommInfoBase.COMM_PERC),
    )

    def _getcommission(self, size, price, pseudoexec):
        comm = abs(size) * price * self.p.commission
        return comm


class BacktestEngine:
    def __init__(self, cash: float = 1_000_000):
        self.cerebro = bt.Cerebro()
        self.cerebro.broker.setcash(cash)
        self.cerebro.broker.addcommissioninfo(TaiwanCommission())
        self.cerebro.broker.set_slippage_perc(SLIPPAGE)
        self.cerebro.addanalyzer(bt.analyzers.TimeReturn, _name="time_return")
        self.cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe", timeframe=bt.TimeFrame.Days)
        self.cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
        self.start_date = None
        self.end_date = None

    def add_data(self, df: pd.DataFrame, stock_id: str):
        df = df.copy()
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date")

        required = ["Open", "High", "Low", "Close", "Volume"]
        rename_map = {}
        for col in df.columns:
            cl = col.lower()
            if cl == "open":
                rename_map[col] = "Open"
            elif cl == "high":
                rename_map[col] = "High"
            elif cl == "low":
                rename_map[col] = "Low"
            elif cl == "close":
                rename_map[col] = "Close"
            elif cl == "volume":
                rename_map[col] = "Volume"

        df = df.rename(columns=rename_map)
        missing = [c for c in required if c not in df.columns]
        if missing:
            logger.warning(f"{stock_id} missing columns {missing}, skipping")
            return

        df = df.dropna(subset=required)
        df.sort_index(inplace=True)

        data = TaiwanStockData(dataname=df)
        self.cerebro.adddata(data, name=stock_id)

        if self.start_date is None or df.index.min() < self.start_date:
            self.start_date = df.index.min()
        if self.end_date is None or df.index.max() > self.end_date:
            self.end_date = df.index.max()

    def add_strategy(self, strategy_class, **params):
        self.cerebro.addstrategy(strategy_class, **params)

    def add_analyzer(self, analyzer_class, **params):
        self.cerebro.addanalyzer(analyzer_class, **params)

    def add_sizer(self, sizer_class, **params):
        self.cerebro.addsizer(sizer_class, **params)

    def run(self) -> bt.Cerebro:
        logger.info(f"Running backtest: cash={self.cerebro.broker.getvalue():,.0f}, "
                     f"start={self.start_date}, end={self.end_date}")
        results = self.cerebro.run()
        logger.info(f"Final portfolio value: {self.cerebro.broker.getvalue():,.0f}")
        return results
