import pandas as pd
from app.services.indicator_service import calculate_sma, update_sma_for_ticker
from app.db.models.price import Price


def test_calculate_sma_basic():
    df = pd.DataFrame(
        {"close": [10, 11, 12, 13, 14]},
        index=pd.to_datetime([
            "2023-01-02",
            "2023-01-03",
            "2023-01-04",
            "2023-01-05",
            "2023-01-06",
        ])
    )
    sma = calculate_sma(df, window=3)
    assert round(sma.iloc[-1], 2) == 13.0


def test_update_sma_for_ticker(db_session, seed_symbol):
    prices = [
        Price(symbol_id=seed_symbol.id, date=pd.to_datetime("2023-01-02"), open=10, high=11, low=9, close=10, volume=1000),
        Price(symbol_id=seed_symbol.id, date=pd.to_datetime("2023-01-03"), open=11, high=12, low=10, close=11, volume=1500),
        Price(symbol_id=seed_symbol.id, date=pd.to_datetime("2023-01-04"), open=12, high=13, low=11, close=12, volume=1200),
        Price(symbol_id=seed_symbol.id, date=pd.to_datetime("2023-01-05"), open=13, high=14, low=12, close=13, volume=1300),
    ]
    db_session.add_all(prices)
    db_session.commit()

    result = update_sma_for_ticker("PETR4.SA", window=3, db=db_session)
    assert result["inserted"] > 0
    assert "SMA atualizado com sucesso." in result["message"]