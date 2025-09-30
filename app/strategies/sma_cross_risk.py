import backtrader as bt

from app.strategies.base import RiskManagedStrategy


class SMACrossRisk(RiskManagedStrategy):
    """SMA crossover strategy with risk management and ATR-based stop."""

    params = dict(
        fast_period=10,
        slow_period=30,
        atr_period=14,
        atr_mult=2.0,
        risk_per_trade=0.01,
        commission=0.001,
    )

    def __init__(self):
        super().__init__()
        data0 = self.datas[0]
        self.sma_fast = bt.ind.SMA(data0, period=int(self.p.fast_period))
        self.sma_slow = bt.ind.SMA(data0, period=int(self.p.slow_period))
        self.crossover = bt.ind.CrossOver(self.sma_fast, self.sma_slow)
        self._initial_check_done = False

    @property
    def min_history(self) -> int:
        return int(self.p.slow_period)

    def should_enter(self) -> bool:
        if len(self) < self.min_history:
            return False
        if not self._initial_check_done:
            self._initial_check_done = True
            if self.sma_fast[0] > self.sma_slow[0]:
                return True
        return self.crossover[0] > 0

    def should_exit(self) -> bool:
        return self.crossover[0] < 0