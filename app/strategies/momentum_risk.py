import math
import backtrader as bt

from app.strategies.base import RiskManagedStrategy


class MomentumRisk(RiskManagedStrategy):
    """Momentum-based trend following with ATR risk controls."""

    params = dict(
        lookback=20,
        entry_threshold=0.0,
        exit_threshold=0.0,
        atr_period=14,
        atr_mult=2.0,
        risk_per_trade=0.01,
        commission=0.001,
    )

    def __init__(self):
        super().__init__()
        self.momentum = bt.ind.RateOfChangePercent(self.data.close, period=int(self.p.lookback))

    @property
    def min_history(self) -> int:
        return int(self.p.lookback) + 1

    def _momentum_value(self) -> float:
        value = float(self.momentum[0])
        return value if math.isfinite(value) else float("nan")

    def should_enter(self) -> bool:
        value = self._momentum_value()
        if not math.isfinite(value):
            return False
        return value >= float(self.p.entry_threshold)

    def should_exit(self) -> bool:
        value = self._momentum_value()
        if not math.isfinite(value):
            return False
        return value <= float(self.p.exit_threshold)