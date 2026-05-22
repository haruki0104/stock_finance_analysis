import time
import datetime
import schedule
import pandas as pd
from loguru import logger
from pathlib import Path

from src.config import DATA_DIR, SCHEDULE_TIME, SCHEDULE_DAYS, BACKTEST_START
from src.data.free_data_client import FreeDataClient
from src.data.cache_manager import init_db


client = FreeDataClient()


def update_stock_prices(stock_ids: list[str] = None):
    today = datetime.date.today()
    start = (today - datetime.timedelta(days=365)).strftime("%Y-%m-%d")
    end = today.strftime("%Y-%m-%d")

    if stock_ids is None:
        info = client.all_stock_info()
        stock_ids = info["stock_id"].astype(str).tolist()[:50]

    logger.info(f"Scheduled update: fetching {len(stock_ids)} stocks from {start} to {end}")
    success = 0
    for sid in stock_ids:
        try:
            df = client.stock_price(sid, start, end)
            if not df.empty:
                success += 1
        except Exception as e:
            logger.debug(f"Update failed for {sid}: {e}")
        time.sleep(0.5)

    per_df = client.per_pbr_list()
    logger.info(f"Update complete: {success}/{len(stock_ids)} stocks, PER/PBR: {len(per_df)} records")


def update_per_pbr():
    df = client.per_pbr_list()
    logger.info(f"PER/PBR updated: {len(df)} records")


def daily_update():
    logger.info("Starting daily data update...")
    update_per_pbr()
    info = client.all_stock_info()
    ids = [s for s in info["stock_id"].astype(str).tolist()
           if s.isdigit() and len(s) == 4][:30]
    update_stock_prices(ids)
    logger.info("Daily update finished")


def run_scheduler():
    init_db()
    logger.info(f"Scheduler started. Will run daily at {SCHEDULE_TIME}")

    for day in SCHEDULE_DAYS:
        day_names = ["monday", "tuesday", "wednesday", "thursday", "friday",
                     "saturday", "sunday"]
        schedule.every().__getattribute__(day_names[day]).at(SCHEDULE_TIME).do(daily_update)

    schedule.every().hour.do(lambda: logger.debug("Scheduler heartbeat..."))

    today_run = False
    if datetime.datetime.now().hour < 15:
        logger.info("Market still open, will update after close")
    else:
        daily_update()
        today_run = True

    logger.info("Scheduler entering loop (Ctrl+C to stop)")
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user")
