import backtrader as bt


class SMACross(bt.Strategy):
    """
    Estratégia simples de cruzamento de médias móveis:
    - Compra quando SMA rápida cruza acima da SMA lenta
    - Vende quando SMA rápida cruza abaixo da SMA lenta
    """

    params = (
        ("fast_period", 10),
        ("slow_period", 30),
    )

    def __init__(self):
        sma_fast = bt.indicators.SMA(self.data.close, period=self.params.fast_period)
        sma_slow = bt.indicators.SMA(self.data.close, period=self.params.slow_period)

        # Detecta cruzamentos
        self.crossover = bt.indicators.CrossOver(sma_fast, sma_slow)

    def next(self):
        if not self.position:  # Não temos posição
            if self.crossover > 0:  # SMA rápida cruzou acima
                self.buy()
        elif self.crossover < 0:  # Já temos posição e cruzou abaixo
            self.sell()