import pandas as pd
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db.session import SessionLocal
from app.db.models.symbol import Symbol
from app.db.models.price import Price
from app.db.models.indicator import Indicator


def calculate_sma(prices: pd.DataFrame, window: int) -> pd.Series:
    return prices["close"].rolling(window=window).mean()


def update_sma_for_ticker(ticker: str, window: int = 20) -> dict:
    db = SessionLocal()
    try:
        symbol = db.execute(
            select(Symbol).where(Symbol.ticker == ticker)
        ).scalar_one_or_none()

        if symbol is None:
            raise ValueError(f"Ticker '{ticker}' não encontrado no banco.")

        q = select(Price).where(Price.symbol_id == symbol.id).order_by(Price.date.asc())
        prices = db.execute(q).scalars().all()
        if not prices:
            return {
                "ticker": ticker,
                "inserted": 0,
                "message": "Nenhum preço encontrado."
            }

        df = pd.DataFrame(
            [{"date": p.date, "close": p.close} for p in prices]
        ).set_index("date")

        sma_series = calculate_sma(df, window)

        rows = []
        for date, value in sma_series.dropna().items():
            rows.append({
                "symbol_id": symbol.id,
                "date": date,
                "name": "SMA",
                "value": float(value),
                "params": f"window={window}"
            })

        if not rows:
            return {
                "ticker": ticker,
                "inserted": 0,
                "message": "Nenhum valor de SMA calculado."
            }

        stmt = pg_insert(Indicator).values(rows)
        stmt = stmt.on_conflict_do_nothing(
            index_elements=["symbol_id", "date", "name", "params"]
        )
        result = db.execute(stmt)
        db.commit()

        return {
            "ticker": ticker,
            "inserted": result.rowcount if result.rowcount is not None else len(rows),
            "message": "SMA atualizado com sucesso."
        }
    finally:
        db.close()
