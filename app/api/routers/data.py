from fastapi import APIRouter
from pydantic import BaseModel
from app.services.data_collector import update_prices_for_ticker
from app.services.indicator_service import update_sma_for_ticker

router = APIRouter(prefix="/data", tags=["Data"])


class IndicatorRequest(BaseModel):
    ticker: str
    window: int = 20


@router.post("/indicators/update")
def update_indicators(req: IndicatorRequest):
    prices_summary = update_prices_for_ticker(req.ticker)
    indicators_summary = update_sma_for_ticker(req.ticker, req.window)
    return {"prices": prices_summary, "indicators": indicators_summary}