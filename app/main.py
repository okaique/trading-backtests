from fastapi import FastAPI
from app.api.routers import data, health, backtests

app = FastAPI(title="Trading Backtests API")

app.include_router(health.router)
app.include_router(data.router)
app.include_router(backtests.router)
