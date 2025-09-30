import numpy as np


def fit_logistic(features: np.ndarray, labels: np.ndarray, *, lr: float = 0.1, epochs: int = 300, l2: float = 1e-4):
    """Simple logistic regression trained via gradient descent."""
    if features.ndim != 2:
        raise ValueError("features must be 2-D array")
    if labels.ndim != 1:
        raise ValueError("labels must be 1-D array")
    if features.shape[0] != labels.shape[0]:
        raise ValueError("features and labels size mismatch")

    X = np.hstack([np.ones((features.shape[0], 1)), features])
    y = labels
    weights = np.zeros(X.shape[1])

    for _ in range(epochs):
        z = X @ weights
        preds = 1.0 / (1.0 + np.exp(-z))
        gradient = X.T @ (preds - y) / y.size + l2 * weights
        weights -= lr * gradient

    bias = weights[0]
    coeffs = weights[1:]
    return coeffs, bias


def predict_proba(features: np.ndarray, coeffs: np.ndarray, bias: float) -> np.ndarray:
    if features.ndim == 1:
        features = features.reshape(1, -1)
    z = features @ coeffs + bias
    return 1.0 / (1.0 + np.exp(-z))