import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from loguru import logger
import json

from src.config import REPORT_DIR


def generate_report(results, strategy_name: str = "MultiFactorRotation",
                    benchmark_return: float = 0.0) -> dict:
    strat = results[0]

    start_value = strat.broker.startingcash
    final_value = strat.broker.getvalue()
    total_return_pct = (final_value - start_value) / start_value * 100

    ret_analysis = strat.analyzers.time_return.get_analysis() if hasattr(strat.analyzers, 'time_return') else {}
    sharpe_analysis = strat.analyzers.sharpe.get_analysis() if hasattr(strat.analyzers, 'sharpe') else {}
    dd_analysis = strat.analyzers.drawdown.get_analysis() if hasattr(strat.analyzers, 'drawdown') else {}

    dates = sorted(ret_analysis.keys())
    daily_returns = np.array([ret_analysis[d] for d in dates], dtype=float)

    sharpe = sharpe_analysis.get('sharperatio', 0) or 0
    max_dd = dd_analysis.get('max', {}).get('drawdown', 0) or 0

    if len(daily_returns) > 1:
        cum = np.cumprod(1 + daily_returns) * start_value
        cum = np.insert(cum, 0, start_value)
        dd_series = (cum[1:] - np.maximum.accumulate(cum[1:])) / np.maximum.accumulate(cum[1:]) * 100
        max_dd = max(abs(np.min(dd_series)), max_dd)
    else:
        cum = np.array([start_value, final_value])
        dd_series = np.array([0, 0])

    wins = int(np.sum(daily_returns > 0))
    total = len(daily_returns)
    win_rate = wins / max(total, 1) * 100

    report = {
        "strategy": strategy_name,
        "period": f"{dates[0].strftime('%Y-%m-%d') if dates else 'N/A'} ~ {dates[-1].strftime('%Y-%m-%d') if dates else 'N/A'}",
        "start_value": round(start_value, 2),
        "final_value": round(final_value, 2),
        "total_return_pct": round(total_return_pct, 2),
        "benchmark_return_pct": round(benchmark_return * 100, 2),
        "excess_return_pct": round(total_return_pct - benchmark_return * 100, 2),
        "sharpe_ratio": round(sharpe, 4),
        "max_drawdown_pct": round(max_dd, 2),
        "win_rate_pct": round(win_rate, 2),
        "total_trading_days": total,
    }

    logger.info(f"\n{'='*55}")
    logger.info(f"  Strategy: {strategy_name}")
    logger.info(f"  Period: {report['period']}")
    logger.info(f"  Start: {start_value:>12,.2f} → Final: {final_value:>12,.2f}")
    logger.info(f"  Return: {total_return_pct:>7.2f}%  |  Benchmark: {benchmark_return*100:.2f}%")
    logger.info(f"  Excess: {(total_return_pct - benchmark_return*100):>7.2f}%")
    logger.info(f"  Sharpe: {sharpe:.4f}  |  MaxDD: {max_dd:.2f}%  |  WinRate: {win_rate:.1f}%")
    logger.info(f"{'='*55}")

    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)

    eq = cum / start_value * 100
    axes[0].plot(eq, color="blue", linewidth=1.5, label=f"{strategy_name} ({total_return_pct:.1f}%)")
    axes[0].axhline(y=100 + benchmark_return * 100, color="gray", linestyle="--",
                    label=f"Benchmark ({benchmark_return*100:.1f}%)")
    axes[0].set_ylabel("Equity (%)")
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    axes[1].fill_between(range(len(dd_series)), 0, dd_series, color="red", alpha=0.3)
    axes[1].set_ylabel("Drawdown (%)")
    axes[1].grid(True, alpha=0.3)

    axes[2].bar(range(len(daily_returns)), daily_returns * 100, width=1,
                color=np.where(daily_returns >= 0, "green", "red"), alpha=0.5)
    axes[2].set_ylabel("Daily Return (%)")
    axes[2].set_xlabel("Trading Day")
    axes[2].grid(True, alpha=0.3)

    plt.tight_layout()
    safe_name = strategy_name.lower().replace(" ", "_")
    report_path = REPORT_DIR / f"{safe_name}_report.png"
    fig.savefig(report_path, dpi=150)
    logger.info(f"Chart saved: {report_path}")
    plt.close(fig)

    json_path = REPORT_DIR / f"{safe_name}_report.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    logger.info(f"JSON saved: {json_path}")

    return report
