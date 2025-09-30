from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel, Field

import structlog

from app.services.backtest_service import (
    run_backtest_and_save,
    get_backtest_results,
    list_backtests,
)

router = APIRouter(prefix="/backtests", tags=["backtests"])
logger = structlog.get_logger(__name__)



class BacktestRunRequest(BaseModel):
    ticker: str
    strategy_type: str = Field(..., description="Identificador da estrategia (ex.: sma_cross, donchian_breakout, momentum)")
    strategy_params: Dict[str, Any] = Field(default_factory=dict)
    start: Optional[str] = None
    end: Optional[str] = None
    initial_cash: float = 100000.0
    commission: Optional[float] = None
    timeframe: Optional[str] = "1d"


def _schedule_job(background_tasks: BackgroundTasks, *, payload: Dict[str, Any]):
    def _job():
        try:
            run_backtest_and_save(**payload)
        except Exception as exc:  # pragma: no cover - background path
            print(f"Backtest background job failed: {exc}")

    background_tasks.add_task(_job)


@router.post("/run")
def run_backtest(
    req: BacktestRunRequest,
    background_tasks: BackgroundTasks,
    async_run: bool = Query(False, description="Executa em background quando true"),
):
    payload = req.model_dump()
    if async_run:
        logger.info("backtest.enqueue", ticker=req.ticker, strategy_type=req.strategy_type)
        _schedule_job(background_tasks, payload=payload)
        return {
            "status": "scheduled",
            "ticker": req.ticker,
            "strategy_type": req.strategy_type,
        }

    try:
        result = run_backtest_and_save(**payload)
    except Exception as exc:
        logger.exception("backtest.run.error", ticker=req.ticker, strategy_type=req.strategy_type)
        raise HTTPException(status_code=500, detail=str(exc))

    logger.info("backtest.run.sync_completed", ticker=req.ticker, strategy_type=req.strategy_type, summary=result)
    return result


@router.get("/")
def list_backtests_endpoint(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    ticker: Optional[str] = None,
    strategy_type: Optional[str] = None,
    created_from: Optional[str] = Query(None, description="Filtro de data inicial (ISO 8601)"),
    created_to: Optional[str] = Query(None, description="Filtro de data final (ISO 8601)"),
):
    def _parse_date(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Data invalida: {value}") from exc

    created_from_dt = _parse_date(created_from)
    created_to_dt = _parse_date(created_to)

    result = list_backtests(
        page=page,
        page_size=page_size,
        ticker=ticker,
        strategy_type=strategy_type,
        created_from=created_from_dt,
        created_to=created_to_dt,
    )
    logger.info("backtest.list", page=page, page_size=page_size, ticker=ticker, strategy_type=strategy_type)
    return result


@router.get("/{backtest_id}/results")
def get_results(backtest_id: int):
    result = get_backtest_results(backtest_id)
    if not result:
        raise HTTPException(status_code=404, detail="Backtest nao encontrado")
    return result