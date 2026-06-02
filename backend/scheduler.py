import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from backend.config import SCHEDULE_HOUR, SCHEDULE_MINUTE
from backend import database, data_fetcher, content_generator

log = logging.getLogger(__name__)

_scheduler = BackgroundScheduler(timezone="Asia/Jerusalem")


def run_daily_generation():
    today = datetime.now().strftime("%Y-%m-%d")
    log.info(f"Starting daily content generation for {today}")
    try:
        market_data = data_fetcher.fetch_market_data()
        news = data_fetcher.fetch_globes_news()
        market_summary, investment_tip, news_analysis = content_generator.generate_all(
            market_data, news
        )
        database.save_draft(
            date=today,
            market_summary=market_summary,
            investment_tip=investment_tip,
            news_analysis=news_analysis,
            raw_market_data=market_data,
            raw_news=news,
        )
        log.info(f"Content generation complete for {today}")
        return True
    except Exception as e:
        log.error(f"Content generation failed: {e}", exc_info=True)
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
