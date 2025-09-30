import math
from typing import Optional

import numpy as np

from app.ml.logistic_signal import fit_logistic, predict_proba
from app.strategies.base import RiskManagedStrategy


class LogisticMomentumRisk(RiskManagedStrategy):
    params = dict(
        lookback=5,
        train_window=120,
        entry_threshold=0.6,
        exit_threshold=0.4,
        atr_period=14,
        atr_mult=2.0,
        risk_per_trade=0.01,
        commission=0.001,
    )

    def __init__(self):
        super().__init__()
        self._coeffs: Optional[np.ndarray] = None
        self._bias: float = 0.0
        self._prob: float = 0.0

    @property
    def min_history(self) -> int:
        return int(self.p.train_window + self.p.lookback + 1)

    def _collect_closes(self, count: int) -> Optional[np.ndarray]:
        values = list(self.data.close.get(size=count))
        if len(values) < count:
            return None
        return np.array(values, dtype=float)

    def _train_if_ready(self):
        count = int(self.p.train_window + self.p.lookback + 1)
        closes = self._collect_closes(count)
        if closes is None:
            return

        log_returns = np.diff(np.log(closes))
        lookback = int(self.p.lookback)
        train_window = int(self.p.train_window)

        features = []
        labels = []
        for idx in range(train_window):
            window = log_returns[idx : idx + lookback]
            target = 1.0 if log_returns[idx + lookback] > 0 else 0.0
            features.append(window)
            labels.append(target)

        feat_arr = np.array(features)
        label_arr = np.array(labels)
        if not np.isfinite(feat_arr).all():
            return

        self._coeffs, self._bias = fit_logistic(feat_arr, label_arr)

        recent = log_returns[-lookback:]
        self._prob = float(predict_proba(recent, self._coeffs, self._bias)[0])

    def next(self):
        self._train_if_ready()
        super().next()

    def should_enter(self) -> bool:
        if self._coeffs is None:
            return False
        return self._prob >= float(self.p.entry_threshold)

    def should_exit(self) -> bool:
        if self._coeffs is None:
            return False
        return self._prob <= float(self.p.exit_threshold)