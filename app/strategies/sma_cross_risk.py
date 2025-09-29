import math
import backtrader as bt


class SMACrossRisk(bt.Strategy):
    """
    SMA crossover strategy with risk management:
    - Stop loss derived from ATR (defaults to 2x ATR)
    - Position sizing limits each trade to 1% of available cash
    """
    params = dict(
        fast_period=10,
        slow_period=30,
        atr_period=14,
        atr_mult=2.0,
        risk_per_trade=0.01,  # 1% of the account
    )

    def __init__(self):
        data0 = self.datas[0]
        self.sma_fast = bt.ind.SMA(data0, period=int(self.p.fast_period))
        self.sma_slow = bt.ind.SMA(data0, period=int(self.p.slow_period))
        self.crossover = bt.ind.CrossOver(self.sma_fast, self.sma_slow)

        self.atr = bt.ind.ATR(data0, period=int(self.p.atr_period))
        self._first_signal_seen = False
        self.broker.setcommission(commission=0.001)

    def prenext(self):
        self.next()

    def _should_enter(self):
        has_initial_signal = False
        if not self._first_signal_seen and len(self) >= self.p.slow_period:
            self._first_signal_seen = True
            has_initial_signal = self.sma_fast[0] > self.sma_slow[0]
        return self.crossover[0] > 0 or has_initial_signal

    def next(self):
        if len(self) < self.p.slow_period:
            return

        if not self.position:
            if self._should_enter():
                atr_value = float(self.atr[0])
                if not math.isfinite(atr_value) or atr_value <= 0:
                    return

                stop_price = self.data.close[0] - self.p.atr_mult * atr_value
                risk_per_share = self.data.close[0] - stop_price
                if risk_per_share <= 0:
                    return

                cash = self.broker.getcash()
                risk_capital = cash * self.p.risk_per_trade
                size = int(risk_capital / risk_per_share)

                if size > 0:
                    self.buy(size=size)
                    self.sell(
                        exectype=bt.Order.Stop,
                        price=stop_price,
                        size=size,
                    )

        else:
            if self.crossover[0] < 0:
                self.close()
