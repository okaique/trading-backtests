import math
import backtrader as bt

from app.strategies.base import RiskManagedStrategy


class DonchianBreakoutRisk(RiskManagedStrategy):
    """Donchian breakout strategy with ATR-based risk management."""

    params = dict(
        channel_period=20,
        atr_period=14,
        atr_mult=2.0,
        risk_per_trade=0.01,
        commission=0.001,
    )

    def __init__(self):
        super().__init__()
        period = int(self.p.channel_period)
        data0 = self.datas[0]
        self.highest = bt.ind.Highest(data0.high, period=period)
        self.lowest = bt.ind.Lowest(data0.low, period=period)

    @property
    def min_history(self) -> int:
        return int(self.p.channel_period)

    def should_enter(self) -> bool:
        if len(self) <= self.min_history:
            return False
        upper = float(self.highest[-1])
        price = float(self.data.close[0])
        return math.isfinite(upper) and price > upper

    def should_exit(self) -> bool:
        if len(self) <= self.min_history:
            return False
        lower = float(self.lowest[-1])
        price = float(self.data.close[0])
        return math.isfinite(lower) and price < lower