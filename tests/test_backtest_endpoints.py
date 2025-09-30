import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def api_client():
    return TestClient(app)


def _base_payload():
    return {
        "ticker": "PETR4.SA",
        "strategy_type": "sma_cross",
        "strategy_params": {"fast_period": 5, "slow_period": 10},
        "start": "2023-01-02",
        "end": "2023-01-10",
        "initial_cash": 50000.0,
    }


def test_run_backtest_sync(api_client, monkeypatch):
    captured = {}

    def fake_run_backtest_and_save(**kwargs):
        captured.update(kwargs)
        return {"id": 1, "ticker": kwargs["ticker"], "strategy_type": kwargs["strategy_type"], "status": "completed"}

    monkeypatch.setattr("app.api.routers.backtests.run_backtest_and_save", fake_run_backtest_and_save)

    response = api_client.post("/backtests/run", json=_base_payload())

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert captured["strategy_type"] == "sma_cross"
    assert captured["strategy_params"] == {"fast_period": 5, "slow_period": 10}


def test_run_backtest_async(api_client, monkeypatch):
    calls = []

    def fake_run(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr("app.api.routers.backtests.run_backtest_and_save", fake_run)

    response = api_client.post("/backtests/run?async_run=true", json=_base_payload())

    assert response.status_code == 200
    assert response.json() == {"status": "scheduled", "ticker": "PETR4.SA", "strategy_type": "sma_cross"}
    assert len(calls) == 1
    async_kwargs = calls[0]
    assert async_kwargs["strategy_type"] == "sma_cross"
    assert async_kwargs["strategy_params"]["fast_period"] == 5
    assert async_kwargs["strategy_params"]["slow_period"] == 10


def test_list_backtests(api_client, monkeypatch):
    payload = {
        "page": 1,
        "page_size": 20,
        "total": 1,
        "items": [
            {
                "id": 1,
                "ticker": "PETR4.SA",
                "strategy_type": "sma_cross",
                "start": "2023-01-02",
                "end": "2023-01-10",
                "initial_cash": 50000.0,
                "final_value": 51000.0,
                "status": "completed",
                "created_at": "2023-01-11T10:00:00",
            }
        ],
    }

    monkeypatch.setattr("app.api.routers.backtests.list_backtests", lambda **_: payload)

    response = api_client.get("/backtests")
    assert response.status_code == 200
    assert response.json() == payload


def test_get_results_not_found(api_client, monkeypatch):
    monkeypatch.setattr("app.api.routers.backtests.get_backtest_results", lambda backtest_id: None)
    response = api_client.get("/backtests/999/results")
    assert response.status_code == 404
    detail = response.json()["detail"]
    assert detail.startswith("Backtest")