try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger
except ImportError:
    BackgroundScheduler = None
    IntervalTrigger = None

from sqlalchemy import select

from app.db.session import SessionLocal
from app.db.models.symbol import Symbol
from app.services.data_collector import update_prices_for_ticker
from app.services.indicator_service import update_sma_for_ticker

import structlog

logger = structlog.get_logger(__name__)

_scheduler = BackgroundScheduler(timezone="UTC") if BackgroundScheduler else None


def refresh_indicators_job():
    session = SessionLocal()
    try:
        symbols = session.execute(select(Symbol)).scalars().all()
        if not symbols:
            logger.warning("scheduler.no_symbols")
            return

        for symbol in symbols:
            ticker = symbol.ticker
            try:
                update_prices_for_ticker(ticker, db=session)
                update_sma_for_ticker(ticker, db=session)
                logger.info("scheduler.indicator_update", ticker=ticker)
            except Exception:
                logger.exception("scheduler.indicator_update_failed", ticker=ticker)
                session.rollback()
            else:
                session.commit()
    finally:
        session.close()


def start_scheduler(interval_minutes: int = 60) -> None:
    if _scheduler is None:
        logger.warning("scheduler.disabled_no_dependency")
        return
    if _scheduler.running:
        logger.info("scheduler.already_running")
        return

    _scheduler.add_job(
        refresh_indicators_job,
        trigger=IntervalTrigger(minutes=interval_minutes),
        id="refresh-indicators",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("scheduler.started", interval_minutes=interval_minutes)


def shutdown_scheduler() -> None:
    if _scheduler is None:
        return
    if not _scheduler.running:
        return
    _scheduler.shutdown(wait=False)
    logger.info("scheduler.stopped")