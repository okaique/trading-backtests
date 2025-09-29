import backtrader as bt
import pandas as pd
from sqlalchemy import select

from app.db.session import SessionLocal
from app.db.models.price import Price
from app.db.models.symbol import Symbol
from app.strategies.sma_cross import SMACross
from app.db.models.backtest import Backtest


def load_price_data_from_db(ticker: str, start: str = None, end: str = None) -> pd.DataFrame:
    db = SessionLocal()
    try:
        symbol = db.execute(
            select(Symbol).where(Symbol.ticker == ticker)
        ).scalar_one_or_none()

        if symbol is None:
            raise ValueError(f"Ticker '{ticker}' não encontrado no banco.")

        q = select(Price).where(Price.symbol_id == symbol.id).order_by(Price.date.asc())
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

        # Converte para datetime64[ns]
        df["datetime"] = pd.to_datetime(df["datetime"])
        df.set_index("datetime", inplace=True)
        return df
    finally:
        db.close()


def run_backtest_sma_cross(
    ticker: str,
    fast: int = 10,
    slow: int = 30,
    start: str = None,
    end: str = None,
    initial_cash: float = 100000.0,
):
    """
    Executa backtest com a estratégia SMA Cross para um ticker.
    Retorna métricas básicas de resultado.
    """
    df = load_price_data_from_db(ticker, start, end)

    cerebro = bt.Cerebro()

    data = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data)

    cerebro.addstrategy(SMACross, fast_period=fast, slow_period=slow)

    cerebro.broker.setcash(initial_cash)
    cerebro.broker.setcommission(commission=0.001)

    cerebro.run()

    final_value = cerebro.broker.getvalue()

    return {
        "ticker": ticker,
        "fast_period": fast,
        "slow_period": slow,
        "start": start,
        "end": end,
        "initial_cash": initial_cash,
        "final_value": final_value,
    }


def run_backtest_and_save(
    ticker: str,
    fast: int = 10,
    slow: int = 30,
    start: str = None,
    end: str = None,
    initial_cash: float = 100000.0,
):
    db = SessionLocal()
    try:
        result = run_backtest_sma_cross(
            ticker=ticker,
            fast=fast,
            slow=slow,
            start=start,
            end=end,
            initial_cash=initial_cash,
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
            },
        )

        db.add(backtest)
        db.commit()
        db.refresh(backtest)

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


if __name__ == "__main__":
    result = run_backtest_sma_cross(
        "PETR4.SA",
        fast=10,
        slow=30,
        start="2023-01-01",
        end="2023-12-31",
        initial_cash=50000.0,
    )
    print(result)