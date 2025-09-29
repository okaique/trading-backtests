from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.backtest_service import run_backtest_and_save, get_backtest_results

router = APIRouter(prefix="/backtests", tags=["backtests"])

class BacktestRequest(BaseModel):
    ticker: str
    fast_period: int = 10
    slow_period: int = 30
    start: str | None = None
    end: str | None = None
    initial_cash: float = 100000.0


@router.post("/run")
def run_backtest(req: BacktestRequest):
    try:
        result = run_backtest_and_save(
            ticker=req.ticker,
            fast=req.fast_period,
            slow=req.slow_period,
            start=req.start,
            end=req.end,
            initial_cash=req.initial_cash,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{backtest_id}/results")
def get_results(backtest_id: int):
    result = get_backtest_results(backtest_id)
    if not result:
        raise HTTPException(status_code=404, detail="Backtest não encontrado")
    return result