from fastapi import FastAPI
from app.api.routers.health import router as health_router

def create_app() -> FastAPI:
    app = FastAPI(title="Trading Backtests API")
    app.include_router(health_router)
    return app

app = create_app()