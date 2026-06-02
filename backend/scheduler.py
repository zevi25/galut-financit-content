import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from backend.config import SCHEDULE_HOUR, SCHEDULE_MINUTE, today_israel
from backend import database, data_fetcher, content_generator

log = logging.getLogger(__name__)

_scheduler = BackgroundScheduler(timezone="Asia/Jerusalem")


def run_daily_generation():
    """Full generation — creates all 9 sections. Used on first run of the day."""
    today = today_israel()
    log.info(f"Starting FULL content generation for {today}")
    try:
        market_data = data_fetcher.fetch_market_data()
        news = data_fetcher.fetch_globes_news()
        all_content = content_generator.generate_all(market_data, news)
        database.save_draft(
            date=today,
            raw_market_data=__import__("json").dumps(market_data, ensure_ascii=False),
            raw_news=__import__("json").dumps(news, ensure_ascii=False),
            **all_content,
        )
        log.info(f"Content generation complete for {today} — {len(all_content)} sections")
        return True
    except Exception as e:
        log.error(f"Content generation failed: {e}", exc_info=True)
        return False


def run_market_refresh():
    """Light refresh — only updates market_summary (market already exists for today)."""
    today = today_israel()
    log.info(f"Starting MARKET REFRESH for {today}")
    try:
        market_data = data_fetcher.fetch_market_data()
        news = data_fetcher.fetch_globes_news()
        market_summary = content_generator.generate_market_summary(market_data)
        database.save_draft(
            date=today,
            market_summary=market_summary,
            raw_market_data=__import__("json").dumps(market_data, ensure_ascii=False),
            raw_news=__import__("json").dumps(news, ensure_ascii=False),
        )
        log.info(f"Market refresh complete for {today}")
        return True
    except Exception as e:
        log.error(f"Market refresh failed: {e}", exc_info=True)
        return False


def start(app=None):
    database.init_db()
    _scheduler.add_job(
        run_daily_generation,
        CronTrigger(
            hour=SCHEDULE_HOUR,
            minute=SCHEDULE_MINUTE,
            timezone="Asia/Jerusalem",
            day_of_week="mon-fri",
        ),
        id="daily_content",
        replace_existing=True,
    )
    _scheduler.start()
    log.info(f"Scheduler started – daily generation at {SCHEDULE_HOUR:02d}:{SCHEDULE_MINUTE:02d} (Sun-Thu)")


def stop():
    if _scheduler.running:
        _scheduler.shutdown()
