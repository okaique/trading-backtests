import pandas as pd
from app.services.backtest_service import run_backtest_sma_cross, load_price_data_from_db
from app.db.models.price import Price


def test_load_price_data_from_db(db_session, seed_symbol):
    prices = [
        Price(symbol_id=seed_symbol.id, date=pd.to_datetime("2023-01-02"), open=10, high=11, low=9, close=10, volume=1000),
        Price(symbol_id=seed_symbol.id, date=pd.to_datetime("2023-01-03"), open=11, high=12, low=10, close=11, volume=1200),
        Price(symbol_id=seed_symbol.id, date=pd.to_datetime("2023-01-04"), open=12, high=13, low=11, close=12, volume=1300),
        Price(symbol_id=seed_symbol.id, date=pd.to_datetime("2023-01-05"), open=13, high=14, low=12, close=13, volume=1500),
    ]
    db_session.add_all(prices)
    db_session.commit()

    df = load_price_data_from_db("PETR4.SA")
    assert not df.empty
    assert "close" in [c.lower() for c in df.columns]


def test_run_backtest_sma_cross(db_session, seed_symbol):
    # Adiciona dados fictícios de preços
    prices = [
        Price(symbol_id=seed_symbol.id, date=pd.to_datetime("2023-01-02"), open=10, high=11, low=9, close=10, volume=1000),
        Price(symbol_id=seed_symbol.id, date=pd.to_datetime("2023-01-03"), open=11, high=12, low=10, close=11, volume=1200),
        Price(symbol_id=seed_symbol.id, date=pd.to_datetime("2023-01-04"), open=12, high=13, low=11, close=12, volume=1300),
        Price(symbol_id=seed_symbol.id, date=pd.to_datetime("2023-01-05"), open=13, high=14, low=12, close=13, volume=1500),
        Price(symbol_id=seed_symbol.id, date=pd.to_datetime("2023-01-06"), open=14, high=15, low=13, close=14, volume=1600),
    ]
    db_session.add_all(prices)
    db_session.commit()

    result = run_backtest_sma_cross(
        ticker="PETR4.SA",
        fast=2,
        slow=3,
        start="2023-01-02",
        end="2023-01-06",
        initial_cash=50000.0,
    )

    assert result["ticker"] == "PETR4.SA"
    assert result["initial_cash"] == 50000.0
    assert "final_value" in result
    assert result["final_value"] > 0