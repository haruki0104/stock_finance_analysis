#!/usr/bin/env python3
import sys
import click
import pandas as pd
from loguru import logger
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import (
    BACKTEST_START, BACKTEST_END,
    SCORE_WEIGHTS, TOP_N_STOCKS, REPORT_DIR,
)
from src.data.free_data_client import FreeDataClient
from src.data.finmind_client import FinMindClient
from src.data.cache_manager import init_db, clear_cache
from src.data.stock_universe import get_all_stocks
from src.model.multi_factor import MultiFactorModel
from src.model.signal import generate_signals


__version__ = "1.1.0"

@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """台股多因子分析系統 - CLI (v1.1.0)"""
    init_db()
    if ctx.invoked_subcommand is None:
        ctx.invoke(menu)


@cli.command()
def version():
    """顯示版本號"""
    click.echo(f"Taiwan Stock Multi-Factor Analysis System v{__version__}")


@cli.command()
@click.pass_context
def menu(ctx):
    """互動式選單介面"""
    click.echo("\n" + "="*50)
    click.echo("  台股多因子分析系統 - 互動式選單")
    click.echo("="*50)

    options = [
        ("1", "檢查 API 連線狀態", "check_api"),
        ("2", "分析單一個股 (Report)", "analyze"),
        ("3", "多因子評分 (批次篩選)", "score"),
        ("4", "執行策略回測", "backtest"),
        ("5", "啟動 Streamlit 視覺化儀表板", "dashboard"),
        ("6", "執行每日資料更新", "schedule"),
        ("7", "顯示評分權重配置", "weights"),
        ("8", "清除快取資料", "clear"),
        ("0", "離開系統", "exit")
    ]

    while True:
        click.echo("\n可用操作:")
        for key, desc, _ in options:
            click.echo(f"  [{key}] {desc}")

        choice = click.prompt("\n請輸入選項編號", type=str, default="1")

        if choice == "0":
            click.echo("正在離開系統...")
            break

        selected = next((opt for opt in options if opt[0] == choice), None)
        if not selected:
            click.echo("無效的選項，請重新輸入。")
            continue

        cmd_name = selected[2]

        try:
            if cmd_name == "analyze":
                stock_id = click.prompt("請輸入股票代碼 (例如: 2330)", type=str)
                ctx.invoke(analyze, stock_id=stock_id)
            elif cmd_name == "score":
                max_stocks = click.prompt("要分析的股票數量上限", type=int, default=50)
                ctx.invoke(score, max_stocks=max_stocks)
            elif cmd_name == "backtest":
                strategy = click.prompt("選擇回測策略 (rotation/buyhold)",
                                        type=click.Choice(["rotation", "buyhold"]),
                                        default="rotation")
                ctx.invoke(backtest, strategy=strategy)
            elif cmd_name == "check_api":
                ctx.invoke(check_api)
            elif cmd_name == "dashboard":
                ctx.invoke(dashboard)
                break  # Dashboard typically takes over the process
            elif cmd_name == "schedule":
                ctx.invoke(schedule)
            elif cmd_name == "weights":
                ctx.invoke(weights)
            elif cmd_name == "clear":
                if click.confirm("確定要清除所有快取資料嗎?"):
                    ctx.invoke(clear)
            
            click.echo("\n" + "-"*50)
            if choice not in ["5", "0"]:
                if not click.confirm("是否繼續使用選單?"):
                    break
        except Exception as e:
            logger.error(f"執行時發生錯誤: {e}")
            if not click.confirm("是否要重試?"):
                break


@cli.command()
def check_api():
    """檢查 API 連線狀態"""
    fm = FinMindClient()
    stocks = fm.all_stock_info()
    free = FreeDataClient()
    per_df = free.per_pbr_list()
    info_df = free.all_stock_info()
    click.echo(f"FinMind: {'OK' if not stocks.empty else 'FAIL'}")
    click.echo(f"TWSE OpenAPI: {'OK' if not per_df.empty else 'FAIL'}")
    click.echo(f"twstock: {'OK' if not info_df.empty else 'FAIL'}")
    click.echo(f"總計可取得 {len(info_df)} 檔股票")


@cli.command()
@click.option("--start", default=BACKTEST_START, help="開始日期")
@click.option("--end", default=BACKTEST_END, help="結束日期")
@click.option("--max-stocks", default=50, help="分析股票數量上限")
@click.option("--top-n", default=TOP_N_STOCKS, help="選取標的數")
@click.option("--output", default="", help="輸出 CSV 路徑")
@click.option("--source", default="free", type=click.Choice(["free", "finmind"]),
              help="資料來源")
def score(start, end, max_stocks, top_n, output, source):
    """對股票進行多因子評分"""
    client = FreeDataClient() if source == "free" else FinMindClient()
    model = MultiFactorModel(client)

    click.echo(f"取得股票清單...")
    stocks = get_all_stocks(client)
    stock_ids = stocks["stock_id"].astype(str).tolist()[:max_stocks]

    click.echo(f"正在評分 {len(stock_ids)} 檔個股 (從 {start} 到 {end})...")
    scores = model.score_universe(stock_ids, start, end, max_workers=10)

    if scores.empty:
        click.echo("無法取得評分結果")
        return

    signals = generate_signals(scores)
    signals["signal"] = signals.apply(
        lambda r: "BUY" if r["rank"] <= top_n else ("SELL" if r["rank"] > len(scores) - 5 else "HOLD"),
        axis=1
    )

    click.echo(f"\n{'='*60}")
    click.echo(f"  評分完成! 共 {len(signals)} 檔個股")
    click.echo(f"  平均分數: {signals['total_score'].mean():.4f}")
    click.echo(f"  最高分數: {signals['total_score'].max():.4f} ({signals.iloc[0]['stock_id']})")
    click.echo(f"  買進訊號: {len(signals[signals['signal']=='BUY'])} 檔")
    click.echo(f"{'='*60}")

    display_cols = ["rank", "stock_id", "total_score", "fundamental",
                    "institutional", "technical", "warrant", "sentiment",
                    "close_price", "signal"]
    click.echo(signals[display_cols].head(20).to_string(index=False))

    if output:
        signals.to_csv(output, index=False, encoding="utf-8-sig")
        click.echo(f"結果已儲存至 {output}")


@cli.command()
@click.option("--start", default=BACKTEST_START, help="回測開始日期")
@click.option("--end", default=BACKTEST_END, help="回測結束日期")
@click.option("--cash", default=1_000_000, help="初始資金")
@click.option("--top-n", default=TOP_N_STOCKS, help="持有標的數")
@click.option("--strategy", default="rotation",
              type=click.Choice(["rotation", "buyhold", "equalweight"]),
              help="策略類型")
def backtest(start, end, cash, top_n, strategy):
    """執行回測"""
    client = FreeDataClient()
    model = MultiFactorModel(client)

    from src.backtest.engine import BacktestEngine
    from src.backtest.strategies import (
        MultiFactorRotationStrategy,
        BuyAndHoldStrategy,
    )
    from src.backtest.report import generate_report

    strategy_map = {
        "rotation": MultiFactorRotationStrategy,
        "buyhold": BuyAndHoldStrategy,
    }

    stocks = get_all_stocks(client)
    stock_ids = [s for s in stocks["stock_id"].astype(str).tolist()[:30]
                 if s.isdigit() and len(s) == 4]

    click.echo(f"取得 {len(stock_ids)} 檔股票歷史資料...")
    engine = BacktestEngine(cash=cash)

    for sid in stock_ids:
        df = client.stock_price(sid, start, end)
        if not df.empty and len(df) > 100:
            engine.add_data(df, sid)

    engine.add_strategy(strategy_map[strategy], top_n=top_n)

    click.echo(f"執行回測 ({strategy})...")
    results = engine.run()

    benchmark_return = 0.35
    report = generate_report(results, strategy_name=strategy.title(),
                              benchmark_return=benchmark_return)

    click.echo(f"\n回測報告已儲存至 {REPORT_DIR}")


@cli.command()
@click.argument("stock_id", required=True)
@click.option("--years", default=2, help="分析年數")
@click.option("--json", "as_json", is_flag=True, help="輸出 JSON 格式")
def analyze(stock_id: str, years: int, as_json: bool):
    """分析單一個股"""
    from src.analysis.stock_report import analyze_stock, print_analysis_report
    result = analyze_stock(stock_id, years=years)
    if as_json:
        import json
        click.echo(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_analysis_report(result)


@cli.command()
@click.option("--daemon", is_flag=True, help="持續執行排程")
def schedule(daemon):
    """執行每日資料更新排程"""
    from src.data.scheduler import run_scheduler, daily_update
    if daemon:
        run_scheduler()
    else:
        daily_update()
        click.echo("每日更新完成")


@cli.command()
def dashboard():
    """啟動 Streamlit 儀表板"""
    import subprocess
    import sys
    dashboard_path = Path(__file__).resolve().parent / "dashboard" / "app.py"
    click.echo("啟動 Streamlit 儀表板...")
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(dashboard_path)])


@cli.command()
@click.option("--dataset", default=None, help="清除特定資料集快取")
def clear(dataset):
    """清除資料快取"""
    clear_cache(dataset)
    click.echo("快取已清除")


@cli.command()
def weights():
    """顯示目前評分權重"""
    click.echo(f"\n目前評分權重配置:")
    click.echo(f"{'='*40}")
    for k, v in SCORE_WEIGHTS.items():
        name_map = {
            "fundamental": "基本面", "institutional": "籌碼面",
            "technical": "技術面", "warrant": "權證",
            "sentiment": "市場情緒"
        }
        click.echo(f"  {name_map.get(k, k):10s}: {v*100:.0f}%")
    click.echo(f"{'='*40}")


if __name__ == "__main__":
    cli()
