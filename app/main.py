from fastapi import FastAPI

from app.api.routers import data, health, backtests
from app.core.config import settings
from app.core.logging_config import setup_logging
from app.tasks.scheduler import start_scheduler, shutdown_scheduler

setup_logging()

app = FastAPI(title="Trading Backtests API")

app.include_router(health.router)
app.include_router(data.router)
app.include_router(backtests.router)


@app.on_event("startup")
def _startup_scheduler():
    if settings.ENABLE_SCHEDULER:
        start_scheduler(settings.SCHEDULER_INTERVAL_MINUTES)


@app.on_event("shutdown")
def _shutdown_scheduler():
    if settings.ENABLE_SCHEDULER:
        shutdown_scheduler()