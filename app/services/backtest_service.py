from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Dict, Optional, Tuple, Any

import backtrader as bt
import pandas as pd
import structlog
from sqlalchemy import select, func

from app.db.session import SessionLocal
from app.db.models.price import Price
from app.db.models.symbol import Symbol
from app.db.models.backtest import Backtest
from app.db.models.backtest_trade import BacktestTrade
from app.db.models.backtest_position import BacktestPosition

logger = structlog.get_logger(__name__)

from app.strategies import SMACrossRisk, DonchianBreakoutRisk, MomentumRisk, LogisticMomentumRisk
from app.strategies.base import RiskManagedStrategy


RISK_DEFAULTS: Dict[str, Any] = {
    "atr_period": 14,
    "atr_mult": 2.0,
    "risk_per_trade": 0.01,
    "commission": 0.001,
}


@dataclass(frozen=True)
class StrategyConfig:
    cls: type[RiskManagedStrategy]
    defaults: Dict[str, Any]
    required: set[str]
    min_history: Callable[[Dict[str, Any]], int]


def _sma_history(params: Dict[str, Any]) -> int:
    return max(int(params.get("fast_period", 1)), int(params.get("slow_period", 1)), int(params.get("atr_period", 1)))


def _donchian_history(params: Dict[str, Any]) -> int:
    return max(int(params.get("channel_period", 1)), int(params.get("atr_period", 1)))


def _momentum_history(params: Dict[str, Any]) -> int:
    return max(int(params.get("lookback", 1)) + 1, int(params.get("atr_period", 1)))


def _ml_history(params: Dict[str, Any]) -> int:
    lookback = int(params.get("lookback", 1))
    train_window = int(params.get("train_window", 1))
    atr_period = int(params.get("atr_period", 1))
    return max(train_window + lookback + 1, atr_period)


STRATEGY_REGISTRY: Dict[str, StrategyConfig] = {
    "sma_cross": StrategyConfig(
        cls=SMACrossRisk,
        defaults={"fast_period": 10, "slow_period": 30},
        required={"fast_period", "slow_period"},
        min_history=_sma_history,
    ),
    "donchian_breakout": StrategyConfig(
        cls=DonchianBreakoutRisk,
        defaults={"channel_period": 20},
        required={"channel_period"},
        min_history=_donchian_history,
    ),
    "momentum": StrategyConfig(
        cls=MomentumRisk,
        defaults={"lookback": 20, "entry_threshold": 0.0, "exit_threshold": 0.0},
        required={"lookback"},
        min_history=_momentum_history,
    ),
    "ml_momentum": StrategyConfig(
        cls=LogisticMomentumRisk,
        defaults={"lookback": 10, "train_window": 120, "entry_threshold": 0.6, "exit_threshold": 0.4},
        required={"lookback", "train_window"},
        min_history=_ml_history,
    ),
}


def load_price_data_from_db(
    ticker: str, start: Optional[str] = None, end: Optional[str] = None
) -> pd.DataFrame:
    db = SessionLocal()
    try:
        symbol = db.execute(
            select(Symbol).where(Symbol.ticker == ticker)
        ).scalar_one_or_none()
        if symbol is None:
            raise ValueError(f"Ticker '{ticker}' nao encontrado no banco.")

        query = (
            select(Price)
            .where(Price.symbol_id == symbol.id)
            .order_by(Price.date.asc())
        )
        if start:
            query = query.where(Price.date >= start)
        if end:
            query = query.where(Price.date <= end)

        prices = db.execute(query).scalars().all()
        if not prices:
            raise ValueError(f"Nenhum dado encontrado para {ticker} no periodo.")

        df = pd.DataFrame(
            [
                {
                    "datetime": p.date,
                    "open": p.open,
                    "high": p.high,
                    "low": p.low,
                    "close": p.close,
                    "volume": p.volume,
                }
                for p in prices
            ]
        )
        df["datetime"] = pd.to_datetime(df["datetime"])
        df.set_index("datetime", inplace=True)
        return df
    finally:
        db.close()


def _resolve_strategy(strategy_type: str, user_params: Optional[Dict[str, Any]]) -> Tuple[type[RiskManagedStrategy], Dict[str, Any], StrategyConfig]:
    if strategy_type not in STRATEGY_REGISTRY:
        available = ", ".join(sorted(STRATEGY_REGISTRY.keys()))
        raise ValueError(f"Estrategia '{strategy_type}' nao suportada. Opcoes: {available}.")

    config = STRATEGY_REGISTRY[strategy_type]
    params: Dict[str, Any] = {**RISK_DEFAULTS, **config.defaults}
    if user_params:
        params.update(user_params)

    missing = [field for field in config.required if params.get(field) is None]
    if missing:
        raise ValueError(f"Parametros ausentes para '{strategy_type}': {', '.join(missing)}")

    return config.cls, params, config


def _extract_metrics_from_strategy(
    strat: RiskManagedStrategy, initial_cash: float, final_value: float
) -> Dict[str, Optional[float]]:
    ret_pct = (final_value / initial_cash - 1.0) if initial_cash else 0.0
    sharpe = None
    max_dd = None
    try:
        sharpe = strat.analyzers.sharpe.get_analysis().get("sharperatio")
    except Exception:
        pass
    try:
        dd_info = strat.analyzers.drawdown.get_analysis()
        if "max" in dd_info and "drawdown" in dd_info["max"]:
            max_dd = -float(dd_info["max"]["drawdown"]) / 100.0
    except Exception:
        pass

    return {
        "return_pct": float(ret_pct),
        "sharpe": float(sharpe) if sharpe is not None else None,
        "max_drawdown": float(max_dd) if max_dd is not None else None,
    }


def _serialize_trades(trades):
    return [
        {
            "date": trade["date"],
            "operation": trade["operation"],
            "price": trade["price"],
            "size": trade["size"],
            "pnl": trade["pnl"],
        }
        for trade in trades
    ]


def _serialize_positions(positions):
    return [
        {
            "date": pos["date"],
            "position": pos["position"],
            "value": pos["value"],
            "equity": pos["equity"],
        }
        for pos in positions
    ]


def _run_backtrader(
    df: pd.DataFrame,
    strategy_cls: type[RiskManagedStrategy],
    strategy_kwargs: Dict[str, Any],
    initial_cash: float,
    commission: Optional[float],
    min_history: int,
):
    cerebro = bt.Cerebro()
    feed = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(feed)

    cerebro.addstrategy(strategy_cls, **strategy_kwargs)
    cerebro.addanalyzer(
        bt.analyzers.SharpeRatio,
        _name="sharpe",
        timeframe=bt.TimeFrame.Days,
        riskfreerate=0.0,
    )
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")

    cerebro.broker.setcash(initial_cash)
    final_commission = (
        float(strategy_kwargs.get("commission"))
        if "commission" in strategy_kwargs
        else (float(commission) if commission is not None else RISK_DEFAULTS["commission"])
    )
    cerebro.broker.setcommission(commission=final_commission)

    runonce = len(df) > min_history if min_history else False
    run = cerebro.run(runonce=runonce)
    strat: RiskManagedStrategy = run[0]
    final_value = float(cerebro.broker.getvalue())

    metrics = _extract_metrics_from_strategy(strat, initial_cash, final_value)
    trades = _serialize_trades(strat.captured_trades)
    positions = _serialize_positions(strat.captured_positions)
    equity_curve = [
        {"date": point["date"], "equity": point["equity"]}
        for point in strat.captured_equity_curve
    ]

    return final_value, metrics, trades, positions, equity_curve


def run_backtest(
    *,
    ticker: str,
    strategy_type: str,
    strategy_params: Optional[Dict[str, Any]] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    initial_cash: float = 100000.0,
    commission: Optional[float] = None,
    timeframe: Optional[str] = "1d",
) -> Dict[str, Any]:
    df = load_price_data_from_db(ticker, start, end)
    strategy_cls, params, config = _resolve_strategy(strategy_type, strategy_params)

    if commission is not None:
        params["commission"] = commission

    min_history = config.min_history(params)
    final_value, metrics, trades, positions, equity_curve = _run_backtrader(
        df=df,
        strategy_cls=strategy_cls,
        strategy_kwargs=params,
        initial_cash=initial_cash,
        commission=commission,
        min_history=min_history,
    )

    return {
        "ticker": ticker,
        "strategy_type": strategy_type,
        "strategy_params": params,
        "start": start,
        "end": end,
        "timeframe": timeframe,
        "initial_cash": initial_cash,
        "final_value": final_value,
        "metrics": metrics,
        "trades": trades,
        "positions": positions,
        "equity_curve": equity_curve,
    }


def run_backtest_and_save(
    *,
    ticker: str,
    strategy_type: str,
    strategy_params: Optional[Dict[str, Any]] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    initial_cash: float = 100000.0,
    commission: Optional[float] = None,
    timeframe: Optional[str] = "1d",
) -> Dict[str, Any]:
    logger.info("backtest.run.start", ticker=ticker, strategy_type=strategy_type)
    result = run_backtest(
        ticker=ticker,
        strategy_type=strategy_type,
        strategy_params=strategy_params,
        start=start,
        end=end,
        initial_cash=initial_cash,
        commission=commission,
        timeframe=timeframe,
    )

    db = SessionLocal()
    try:
        backtest = Backtest(
            ticker=ticker,
            strategy_type=strategy_type,
            strategy_params=result["strategy_params"],
            fast_period=result["strategy_params"].get("fast_period"),
            slow_period=result["strategy_params"].get("slow_period"),
            start=start,
            end=end,
            initial_cash=initial_cash,
            final_value=result["final_value"],
            status="completed",
            metrics=result["metrics"],
        )
        db.add(backtest)
        db.commit()
        db.refresh(backtest)

        trades_rows = [
            BacktestTrade(
                backtest_id=backtest.id,
                date=trade["date"],
                operation=trade["operation"],
                price=trade["price"],
                size=trade["size"],
                pnl=trade["pnl"],
            )
            for trade in result["trades"]
        ]
        if trades_rows:
            db.add_all(trades_rows)

        positions_rows = [
            BacktestPosition(
                backtest_id=backtest.id,
                date=pos["date"],
                position=pos["position"],
                value=pos["value"],
                equity=pos["equity"],
            )
            for pos in result["positions"]
        ]
        if positions_rows:
            db.add_all(positions_rows)

        db.commit()

        summary = {
            "id": backtest.id,
            "ticker": ticker,
            "strategy_type": strategy_type,
            "strategy_params": result["strategy_params"],
            "start": start,
            "end": end,
            "timeframe": timeframe,
            "initial_cash": initial_cash,
            "final_value": result["final_value"],
            "status": "completed",
        }
        logger.info("backtest.run.completed", backtest_id=backtest.id, ticker=ticker, strategy_type=strategy_type, final_value=result["final_value"])
        return summary
    except Exception:
        db.rollback()
        logger.exception("backtest.run.error", ticker=ticker, strategy_type=strategy_type)
        raise
    finally:
        db.close()


def list_backtests(
    *,
    page: int = 1,
    page_size: int = 20,
    ticker: Optional[str] = None,
    strategy_type: Optional[str] = None,
    created_from: Optional[datetime] = None,
    created_to: Optional[datetime] = None,
) -> Dict[str, Any]:
    db = SessionLocal()
    try:
        base_query = select(Backtest)
        if ticker:
            base_query = base_query.where(Backtest.ticker == ticker)
        if strategy_type:
            base_query = base_query.where(Backtest.strategy_type == strategy_type)
        if created_from:
            base_query = base_query.where(Backtest.created_at >= created_from)
        if created_to:
            base_query = base_query.where(Backtest.created_at <= created_to)

        total = db.execute(select(func.count()).select_from(base_query.subquery())).scalar() or 0

        ordered_query = base_query.order_by(Backtest.created_at.desc())
        offset = max(page - 1, 0) * page_size
        items = db.execute(ordered_query.offset(offset).limit(page_size)).scalars().all()

        payload = [
            {
                "id": item.id,
                "ticker": item.ticker,
                "strategy_type": item.strategy_type,
                "start": item.start,
                "end": item.end,
                "initial_cash": item.initial_cash,
                "final_value": item.final_value,
                "status": item.status,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
            for item in items
        ]

        return {
            "page": page,
            "page_size": page_size,
            "total": total,
            "items": payload,
        }
    finally:
        db.close()


def get_backtest_results(backtest_id: int) -> Optional[Dict[str, Any]]:
    db = SessionLocal()
    try:
        backtest = db.execute(
            select(Backtest).where(Backtest.id == backtest_id)
        ).scalar_one_or_none()
        if not backtest:
            return None

        trades = db.execute(
            select(BacktestTrade)
            .where(BacktestTrade.backtest_id == backtest_id)
            .order_by(BacktestTrade.date.asc())
        ).scalars().all()

        positions = db.execute(
            select(BacktestPosition)
            .where(BacktestPosition.backtest_id == backtest_id)
            .order_by(BacktestPosition.date.asc())
        ).scalars().all()

        trades_payload = [
            {
                "date": t.date.isoformat(),
                "operation": t.operation,
                "price": t.price,
                "size": t.size,
                "pnl": t.pnl,
            }
            for t in trades
        ]

        positions_payload = [
            {
                "date": p.date.isoformat(),
                "position": p.position,
                "value": p.value,
                "equity": p.equity,
            }
            for p in positions
        ]

        equity_curve = [
            {"date": item["date"], "equity": item["equity"]}
            for item in positions_payload
        ]

        return {
            "id": backtest.id,
            "ticker": backtest.ticker,
            "strategy_type": backtest.strategy_type,
            "strategy_params": backtest.strategy_params,
            "start": backtest.start,
            "end": backtest.end,
            "initial_cash": backtest.initial_cash,
            "final_value": backtest.final_value,
            "status": backtest.status,
            "metrics": backtest.metrics or {},
            "trades": trades_payload,
            "positions": positions_payload,
            "equity_curve": equity_curve,
            "created_at": backtest.created_at.isoformat() if backtest.created_at else None,
        }
    finally:
        db.close()