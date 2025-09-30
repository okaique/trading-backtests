import math
import backtrader as bt


class RiskManagedStrategy(bt.Strategy):
    """Base strategy that handles ATR-based stops and position sizing."""

    params = dict(
        atr_period=14,
        atr_mult=2.0,
        risk_per_trade=0.01,
        commission=0.001,
    )

    def __init__(self):
        data0 = self.datas[0]
        self.atr = bt.ind.ATR(data0, period=int(self.p.atr_period))
        if self.p.commission is not None:
            self.broker.setcommission(commission=float(self.p.commission))

        self.captured_trades = []
        self.captured_positions = []
        self.captured_equity_curve = []

    def prenext(self):
        self.next()

    @property
    def min_history(self) -> int:
        """Minimum number of bars before trading is allowed."""
        return 1

    def should_enter(self) -> bool:
        raise NotImplementedError

    def should_exit(self) -> bool:
        return False

    def stop_price(self, entry_price: float) -> float:
        return entry_price - self.p.atr_mult * float(self.atr[0])

    def next(self):
        if len(self) < self.min_history:
            return

        price = float(self.data.close[0])
        atr_value = float(self.atr[0])
        if not math.isfinite(atr_value) or atr_value <= 0:
            return

        if not self.position and self.should_enter():
            stop_price = self.stop_price(price)
            risk_per_share = price - stop_price
            if risk_per_share <= 0:
                return

            cash = self.broker.getcash()
            risk_capital = cash * self.p.risk_per_trade
            size = int(risk_capital / risk_per_share)
            if size <= 0:
                return

            self.buy(size=size)
            self.sell(exectype=bt.Order.Stop, price=stop_price, size=size)

        elif self.position and self.should_exit():
            self.close()

        dt = self.datas[0].datetime.date(0)
        pos_size = float(self.position.size) if self.position else 0.0
        pos_value = float(pos_size * price) if pos_size else 0.0
        equity = float(self.broker.getvalue())
        snapshot = {"date": dt, "position": pos_size, "value": pos_value, "equity": equity}
        self.captured_positions.append(snapshot)
        self.captured_equity_curve.append({"date": dt, "equity": equity})

    def notify_order(self, order):
        if order.status not in [order.Completed]:
            return

        dt = self.datas[0].datetime.date(0)
        op = "buy" if order.isbuy() else "sell"
        trade = {
            "date": dt,
            "operation": op,
            "price": float(order.executed.price),
            "size": float(order.executed.size),
            "pnl": None,
        }
        self.captured_trades.append(trade)

    def notify_trade(self, trade):
        if trade.isclosed:
            dt = self.datas[0].datetime.date(0)
            for t in reversed(self.captured_trades):
                if t["date"] == dt and t["operation"] == "sell" and t["pnl"] is None:
                    t["pnl"] = float(trade.pnl)
                    break