from __future__ import annotations

import backtrader as bt
import pandas as pd
from sqlalchemy import select
from typing import Optional, Dict

from app.db.session import SessionLocal
from app.db.models.price import Price
from app.db.models.symbol import Symbol
from app.db.models.backtest import Backtest
from app.db.models.backtest_trade import BacktestTrade
from app.db.models.backtest_position import BacktestPosition


def load_price_data_from_db(
    ticker: str, start: Optional[str] = None, end: Optional[str] = None
) -> pd.DataFrame:
    """Carrega dados OHLCV do banco para um ticker específico."""
    db = SessionLocal()
    try:
        symbol = db.execute(
            select(Symbol).where(Symbol.ticker == ticker)
        ).scalar_one_or_none()
        if symbol is None:
            raise ValueError(f"Ticker '{ticker}' não encontrado no banco.")

        q = (
            select(Price)
            .where(Price.symbol_id == symbol.id)
            .order_by(Price.date.asc())
        )
        if start:
            q = q.where(Price.date >= start)
        if end:
            q = q.where(Price.date <= end)

        prices = db.execute(q).scalars().all()
        if not prices:
            raise ValueError(f"Nenhum dado encontrado para {ticker} no período.")

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


class CaptureSMACross(bt.Strategy):
    """
    Estratégia SMA Cross simples com captura de trades/posições/equity.
    NÃO herda da sua SMACross para evitar conflitos internos do Backtrader.
    """

    params = dict(fast_period=10, slow_period=30)

    def __init__(self):
        data0 = self.datas[0]
        self.sma_fast = bt.ind.SMA(data0, period=int(self.p.fast_period))
        self.sma_slow = bt.ind.SMA(data0, period=int(self.p.slow_period))
        self.crossover = bt.ind.CrossOver(self.sma_fast, self.sma_slow)

        self.captured_trades = []
        self.captured_positions = []
        self.captured_equity_curve = []

    def notify_order(self, order):
        if order.status in [order.Completed]:
            dt = self.datas[0].datetime.date(0)
            op = "buy" if order.isbuy() else "sell"
            self.captured_trades.append(
                {
                    "date": dt,
                    "operation": op,
                    "price": float(order.executed.price),
                    "size": float(order.executed.size),
                    "pnl": None,
                }
            )

    def notify_trade(self, trade):
        if trade.isclosed:
            dt = self.datas[0].datetime.date(0)
            for t in reversed(self.captured_trades):
                if t["date"] == dt and t["operation"] == "sell" and t["pnl"] is None:
                    t["pnl"] = float(trade.pnl)
                    break

    def next(self):
        dt = self.datas[0].datetime.date(0)

        # Lógica de compra/venda
        if not self.position:
            if self.crossover[0] > 0:
                self.buy()
        else:
            if self.crossover[0] < 0:
                self.sell()

        # Snapshot de posição/equity
        pos_size = float(self.position.size)
        pos_value = float(pos_size * self.datas[0].close[0]) if pos_size else 0.0
        equity = float(self.broker.getvalue())

        self.captured_positions.append(
            {"date": dt, "position": pos_size, "value": pos_value, "equity": equity}
        )
        self.captured_equity_curve.append({"date": dt, "equity": equity})


def _extract_metrics_from_strategy(
    strat: CaptureSMACross, initial_cash: float, final_value: float
) -> Dict[str, float]:
    """Extrai métricas de retorno, sharpe e drawdown do strategy."""
    ret_pct = (final_value / initial_cash - 1.0) if initial_cash else 0.0
    sharpe = None
    dd = None
    try:
        sharpe = strat.analyzers.sharpe.get_analysis().get("sharperatio")
    except Exception:
        pass
    try:
        dd_info = strat.analyzers.drawdown.get_analysis()
        if "max" in dd_info and "drawdown" in dd_info["max"]:
            dd = -float(dd_info["max"]["drawdown"]) / 100.0
    except Exception:
        pass

    return {
        "return_pct": float(ret_pct),
        "sharpe": float(sharpe) if sharpe is not None else None,
        "max_drawdown": float(dd) if dd is not None else None,
    }


def run_backtest_sma_cross(
    ticker: str,
    fast: int = 10,
    slow: int = 30,
    start: Optional[str] = None,
    end: Optional[str] = None,
    initial_cash: float = 100000.0,
):
    """Executa um backtest SMA Cross e retorna resultados + métricas."""
    df = load_price_data_from_db(ticker, start, end)

    cerebro = bt.Cerebro()
    feed = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(feed)

    cerebro.addstrategy(CaptureSMACross, fast_period=fast, slow_period=slow)

    # Analyzers
    cerebro.addanalyzer(
        bt.analyzers.SharpeRatio, _name="sharpe", timeframe=bt.TimeFrame.Days, riskfreerate=0.0
    )
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")

    cerebro.broker.setcash(initial_cash)
    cerebro.broker.setcommission(commission=0.001)

    run = cerebro.run()
    strat: CaptureSMACross = run[0]
    final_value = float(cerebro.broker.getvalue())

    metrics = _extract_metrics_from_strategy(strat, initial_cash, final_value)

    return {
        "ticker": ticker,
        "fast_period": fast,
        "slow_period": slow,
        "start": start,
        "end": end,
        "initial_cash": initial_cash,
        "final_value": final_value,
        "metrics": metrics,
        "trades": strat.captured_trades,
        "positions": strat.captured_positions,
        "equity_curve": strat.captured_equity_curve,
    }


def run_backtest_and_save(
    ticker: str,
    fast: int = 10,
    slow: int = 30,
    start: Optional[str] = None,
    end: Optional[str] = None,
    initial_cash: float = 100000.0,
):
    """Roda o backtest, salva no banco e retorna resumo."""
    db = SessionLocal()
    try:
        result = run_backtest_sma_cross(
            ticker=ticker, fast=fast, slow=slow, start=start, end=end, initial_cash=initial_cash
        )

        backtest = Backtest(
            ticker=ticker,
            fast_period=fast,
            slow_period=slow,
            start=start,
            end=end,
            initial_cash=initial_cash,
            final_value=result["final_value"],
            status="completed",
            metrics={
                "initial_cash": initial_cash,
                "final_value": result["final_value"],
                "fast_period": fast,
                "slow_period": slow,
                "return_pct": result["metrics"].get("return_pct"),
                "sharpe": result["metrics"].get("sharpe"),
                "max_drawdown": result["metrics"].get("max_drawdown"),
            },
        )
        db.add(backtest)
        db.commit()
        db.refresh(backtest)

        trades_rows = [
            BacktestTrade(
                backtest_id=backtest.id,
                date=rec["date"],
                operation=rec["operation"],
                price=rec["price"],
                size=rec["size"],
                pnl=rec["pnl"],
            )
            for rec in result["trades"]
        ]
        if trades_rows:
            db.add_all(trades_rows)

        pos_rows = [
            BacktestPosition(
                backtest_id=backtest.id,
                date=rec["date"],
                position=rec["position"],
                value=rec["value"],
                equity=rec["equity"],
            )
            for rec in result["positions"]
        ]
        if pos_rows:
            db.add_all(pos_rows)

        db.commit()

        return {
            "id": backtest.id,
            "ticker": ticker,
            "fast_period": fast,
            "slow_period": slow,
            "start": start,
            "end": end,
            "initial_cash": initial_cash,
            "final_value": result["final_value"],
            "status": "completed",
        }
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def get_backtest_results(backtest_id: int):
    """Recupera resultados completos de um backtest salvo no banco."""
    db = SessionLocal()
    try:
        backtest = db.execute(
            select(Backtest).where(Backtest.id == backtest_id)
        ).scalar_one_or_none()
        if not backtest:
            return None

        trades = (
            db.execute(
                select(BacktestTrade)
                .where(BacktestTrade.backtest_id == backtest_id)
                .order_by(BacktestTrade.date.asc())
            )
            .scalars()
            .all()
        )

        positions = (
            db.execute(
                select(BacktestPosition)
                .where(BacktestPosition.backtest_id == backtest_id)
                .order_by(BacktestPosition.date.asc())
            )
            .scalars()
            .all()
        )

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
            {"date": p["date"], "equity": p["equity"]}
            for p in positions_payload
        ]

        return {
            "id": backtest.id,
            "ticker": backtest.ticker,
            "fast_period": backtest.fast_period,
            "slow_period": backtest.slow_period,
            "start": backtest.start,
            "end": backtest.end,
            "initial_cash": backtest.initial_cash,
            "final_value": backtest.final_value,
            "status": backtest.status,
            "metrics": backtest.metrics or {},
            "trades": trades_payload,
            "positions": positions_payload,
            "equity_curve": equity_curve,
            "created_at": backtest.created_at.isoformat()
            if backtest.created_at
            else None,
        }
    finally:
        db.close()