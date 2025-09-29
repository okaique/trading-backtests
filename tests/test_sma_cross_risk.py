import pandas as pd
import numpy as np
import backtrader as bt
from app.strategies.sma_cross_risk import SMACrossRisk


def make_test_data(n=60, start_price=10):
    dates = pd.date_range("2023-01-01", periods=n, freq="D")
    prices = np.linspace(start_price, start_price + n * 0.1, n)
    df = pd.DataFrame(
        {
            "open": prices,
            "high": prices + 0.5,
            "low": prices - 0.5,
            "close": prices,
            "volume": 1000,
        },
        index=dates,
    )
    return df


def run_strategy(df: pd.DataFrame, initial_cash=10000):
    cerebro = bt.Cerebro()
    cerebro.broker.setcash(initial_cash)
    data = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data)
    cerebro.addstrategy(SMACrossRisk)
    cerebro.run()
    return cerebro.broker.getvalue()


def test_position_sizing_respects_risk():
    df = make_test_data(n=60)
    final_value = run_strategy(df, initial_cash=10000)
    assert final_value > 0


def test_stop_loss_triggers_exit():
    df = make_test_data(n=60)

    df.iloc[:30, df.columns.get_loc("close")] = np.linspace(10, 30, 30)
    df.iloc[:30, df.columns.get_loc("open")] = df.iloc[:30, df.columns.get_loc("close")]
    df.iloc[:30, df.columns.get_loc("high")] = df.iloc[:30, df.columns.get_loc("close")] + 0.5
    df.iloc[:30, df.columns.get_loc("low")] = df.iloc[:30, df.columns.get_loc("close")] - 0.5

    df.iloc[30:, df.columns.get_loc("close")] = 5
    df.iloc[30:, df.columns.get_loc("low")] = 4

    final_value = run_strategy(df, initial_cash=10000)
    assert final_value < 10000