import pandas as pd
from app.services.data_collector import _prepare_rows_for_insert, update_prices_for_ticker


def test_prepare_rows_for_insert(seed_symbol):
    df = pd.DataFrame(
        {
            "Open": [10.0, 11.0],
            "High": [12.0, 12.5],
            "Low": [9.5, 10.5],
            "Close": [11.0, 12.0],
            "Volume": [1000, 1500],
        },
        index=pd.to_datetime(["2023-01-02", "2023-01-03"])
    )

    rows = _prepare_rows_for_insert(df, symbol_id=seed_symbol.id)
    assert len(rows) == 2
    assert rows[0]["open"] == 10.0
    assert rows[1]["close"] == 12.0


def test_update_prices_for_ticker_with_mock(mocker, db_session, seed_symbol):
    mock_df = pd.DataFrame(
        {
            "Open": [10.0, 11.0],
            "High": [12.0, 12.5],
            "Low": [9.5, 10.5],
            "Close": [11.0, 12.0],
            "Volume": [1000, 1500],
        },
        index=pd.to_datetime(["2023-01-02", "2023-01-03"])
    )

    mocker.patch("app.services.data_collector.fetch_prices_yf", return_value=mock_df)

    result = update_prices_for_ticker("PETR4.SA", db=db_session)
    assert result["inserted"] == 2
    assert result["skipped"] == 0
    assert result["message"] == "Preços atualizados com sucesso."