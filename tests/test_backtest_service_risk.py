import pandas as pd
from app.db.models.price import Price
from app.services.backtest_service import run_backtest_sma_cross_risk


def test_run_backtest_sma_cross_risk(db_session, seed_symbol):
    # Dados fictícios
    prices = [
        Price(symbol_id=seed_symbol.id, date=pd.to_datetime("2023-01-02"), open=10, high=11, low=9, close=10, volume=1000),
        Price(symbol_id=seed_symbol.id, date=pd.to_datetime("2023-01-03"), open=11, high=12, low=10, close=11, volume=1200),
        Price(symbol_id=seed_symbol.id, date=pd.to_datetime("2023-01-04"), open=12, high=13, low=11, close=12, volume=1300),
        Price(symbol_id=seed_symbol.id, date=pd.to_datetime("2023-01-05"), open=13, high=14, low=12, close=13, volume=1500),
        Price(symbol_id=seed_symbol.id, date=pd.to_datetime("2023-01-06"), open=14, high=15, low=13, close=14, volume=1600),
    ]
    db_session.add_all(prices)
    db_session.commit()

    result = run_backtest_sma_cross_risk(
        ticker="PETR4.SA",
        fast=2,
        slow=3,
        atr_period=5,
        atr_mult=2.0,
        risk_per_trade=0.01,
        start="2023-01-02",
        end="2023-01-06",
        initial_cash=50000.0,
    )

    assert result["ticker"] == "PETR4.SA"
    assert result["initial_cash"] == 50000.0
    assert "final_value" in result
    assert "metrics" in result
    assert "atr_period" in result