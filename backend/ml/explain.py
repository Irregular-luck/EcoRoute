"""SHAP adapter for post-training local noise explanations."""
from __future__ import annotations
import numpy as np

FEATURE_LABELS = ["Traffic density", "Motorcycle share", "Bus share", "Average speed", "Rain probability"]


def explain_lstm(model, background: np.ndarray, observation: np.ndarray) -> list[dict]:
    """Return one SHAP attribution per last-timestep feature.

    `background` and `observation` are scaled 3D LSTM arrays: [rows, timestep, feature].
    SHAP remains optional at API serving time to keep mobile route lookup latency bounded.
    """
    import shap
    explainer = shap.GradientExplainer(model, background)
    values = explainer.shap_values(observation)
    raw = np.asarray(values[0] if isinstance(values, list) else values)[0, -1]
    return [{"feature": label, "impact_db": round(float(impact), 2)} for label, impact in zip(FEATURE_LABELS, raw)]
