import pandas as pd
import numpy as np

from app.services.backtest_service import load_price_data_from_db, run_backtest
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
    prices = [
        Price(symbol_id=seed_symbol.id, date=pd.to_datetime("2023-01-02"), open=10, high=11, low=9, close=10, volume=1000),
        Price(symbol_id=seed_symbol.id, date=pd.to_datetime("2023-01-03"), open=11, high=12, low=10, close=11, volume=1200),
        Price(symbol_id=seed_symbol.id, date=pd.to_datetime("2023-01-04"), open=12, high=13, low=11, close=12, volume=1300),
        Price(symbol_id=seed_symbol.id, date=pd.to_datetime("2023-01-05"), open=13, high=14, low=12, close=13, volume=1500),
        Price(symbol_id=seed_symbol.id, date=pd.to_datetime("2023-01-06"), open=14, high=15, low=13, close=14, volume=1600),
    ]
    db_session.add_all(prices)
    db_session.commit()

    result = run_backtest(
        ticker="PETR4.SA",
        strategy_type="sma_cross",
        strategy_params={"fast_period": 2, "slow_period": 3},
        start="2023-01-02",
        end="2023-01-06",
        initial_cash=50000.0,
    )

    assert result["ticker"] == "PETR4.SA"
    assert result["strategy_type"] == "sma_cross"
    assert result["initial_cash"] == 50000.0
    assert "final_value" in result
    assert result["final_value"] > 0
    assert result["metrics"]["return_pct"] is not None


def test_run_backtest_ml_momentum(db_session, seed_symbol):
    prices = []
    base_date = pd.to_datetime("2023-01-02")
    for idx in range(180):
        date = base_date + pd.Timedelta(days=idx)
        price = 10 + idx * 0.1 + (idx % 5) * 0.05
        prices.append(
            Price(
                symbol_id=seed_symbol.id,
                date=date,
                open=price * 0.99,
                high=price * 1.01,
                low=price * 0.98,
                close=price,
                volume=1000 + idx,
            )
        )
    db_session.add_all(prices)
    db_session.commit()

    result = run_backtest(
        ticker="PETR4.SA",
        strategy_type="ml_momentum",
        strategy_params={
            "lookback": 5,
            "train_window": 60,
            "entry_threshold": 0.5,
            "exit_threshold": 0.4
        },
        start="2023-01-02",
        end="2023-07-01",
        initial_cash=50000.0
    )

    assert result["strategy_type"] == "ml_momentum"
    assert result["final_value"] > 0
    assert result["metrics"]["return_pct"] is not None