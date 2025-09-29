from __future__ import annotations

import argparse
from datetime import datetime
from typing import Iterable, List, Optional

import pandas as pd
import yfinance as yf
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.db.session import SessionLocal
from app.db.models.symbol import Symbol
from app.db.models.price import Price


def _normalize_datestr(date_str: Optional[str]) -> Optional[str]:
    if date_str is None or str(date_str).strip() == "":
        return None
    try:
        dt = datetime.fromisoformat(str(date_str).strip())
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                dt = datetime.strptime(str(date_str).strip(), fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
        raise ValueError(f"Formato de data inválido: '{date_str}'. Use YYYY-MM-DD.")


def fetch_prices_yf(
    ticker: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
    interval: str = "1d",
) -> pd.DataFrame:
    start_norm = _normalize_datestr(start)
    end_norm = _normalize_datestr(end)

    df = yf.download(
        tickers=ticker,
        start=start_norm,
        end=end_norm,
        interval=interval,
        progress=False,
        auto_adjust=False,
        actions=False,
        threads=True,
    )

    if df is None or df.empty:
        return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[1] if isinstance(col, tuple) else col for col in df.columns]

    rename_map = {c: c.capitalize() for c in df.columns}
    df = df.rename(columns=rename_map)

    expected = ["Open", "High", "Low", "Close", "Volume"]
    for col in expected:
        if col not in df.columns:
            df[col] = None

    if df.index.tz is not None:
        df.index = df.index.tz_convert(None)

    return df[expected]



def _prepare_rows_for_insert(df: pd.DataFrame, symbol_id: int) -> List[dict]:
    if df.empty:
        return []

    rows: List[dict] = []
    for ts, row in df.iterrows():
        d = ts.date()

        def safe_float(value):
            try:
                if hasattr(value, "iloc"):
                    return float(value.iloc[0])
                return float(value)
            except Exception:
                return None

        rows.append(
            {
                "symbol_id": symbol_id,
                "date": d,
                "open": safe_float(row.get("Open")),
                "high": safe_float(row.get("High")),
                "low": safe_float(row.get("Low")),
                "close": safe_float(row.get("Close")),
                "volume": safe_float(row.get("Volume")),
            }
        )
    return rows


def _filter_already_existing_dates(
    db, symbol_id: int, candidate_dates: Iterable
) -> List:
    if not candidate_dates:
        return []

    candidate_dates = list(candidate_dates)
    q = select(Price.date).where(
        Price.symbol_id == symbol_id,
        Price.date.in_(candidate_dates),
    )
    existing = set(db.scalars(q).all())
    return [d for d in candidate_dates if d not in existing]


def save_prices_bulk_ignore_duplicates(db, rows: List[dict]) -> int:
    if not rows:
        return 0
    stmt = pg_insert(Price).values(rows)
    stmt = stmt.on_conflict_do_nothing(index_elements=["symbol_id", "date"])
    db.execute(stmt)
    return len(rows)


def update_prices_for_ticker(
    ticker: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
    interval: str = "1d",
    db=None
) -> dict:
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        symbol = db.execute(
            select(Symbol).where(Symbol.ticker == ticker)
        ).scalar_one_or_none()

        if symbol is None:
            raise ValueError(f"Ticker '{ticker}' não encontrado na base.")

        df = fetch_prices_yf(ticker=ticker, start=start, end=end, interval=interval)

        if df.empty:
            return {
                "ticker": ticker,
                "downloaded": 0,
                "inserted": 0,
                "skipped": 0,
                "message": "Nenhum dado retornado do Yahoo Finance.",
            }

        candidate_rows = _prepare_rows_for_insert(df, symbol_id=symbol.id)
        candidate_dates = [r["date"] for r in candidate_rows]
        new_dates = _filter_already_existing_dates(db, symbol_id=symbol.id, candidate_dates=candidate_dates)
        rows_new_only = [r for r in candidate_rows if r["date"] in new_dates]

        inserted_attempts = save_prices_bulk_ignore_duplicates(db, rows_new_only)
        db.commit()

        return {
            "ticker": ticker,
            "downloaded": len(candidate_rows),
            "inserted": inserted_attempts,
            "skipped": len(candidate_rows) - inserted_attempts,
            "message": "Preços atualizados com sucesso.",
        }
    finally:
        if close_db:
            db.close()


def main():
    parser = argparse.ArgumentParser(description="Atualiza preços OHLCV de um ticker usando Yahoo Finance.")
    parser.add_argument("--ticker", required=True, help="Ticker (ex.: PETR4.SA)")
    parser.add_argument("--start", required=False, default=None, help="Data inicial (YYYY-MM-DD)")
    parser.add_argument("--end", required=False, default=None, help="Data final (YYYY-MM-DD)")
    parser.add_argument("--interval", required=False, default="1d", help="Intervalo (ex.: 1d, 1wk, 1mo)")

    args = parser.parse_args()

    summary = update_prices_for_ticker(
        ticker=args.ticker,
        start=args.start,
        end=args.end,
        interval=args.interval,
    )
    print(summary)


if __name__ == "__main__":
    main()
