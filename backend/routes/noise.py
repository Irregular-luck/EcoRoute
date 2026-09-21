"""Noise inference boundary.

Deploy a saved Keras LSTM model at `ml_models/noise_lstm.keras`. The app continues to
return explainable, deterministic estimates before a model is trained; it never labels
the fallback as an LSTM prediction.
"""
from pathlib import Path
from dataclasses import dataclass
import pickle
import numpy as np


@dataclass(frozen=True)
class NoiseResult:
    decibels: float
    model_version: str
    contributors: list[dict]
    summary: str


class NoisePredictor:
    model_path = Path(__file__).resolve().parent.parent / "ml_models" / "noise_lstm.keras"
    scaler_path = Path(__file__).resolve().parent.parent / "ml_models" / "noise_scaler.pkl"
    background_path = Path(__file__).resolve().parent.parent / "ml_models" / "shap_background.npy"

    def predict(self, traffic: int, motorcycle_share: int, bus_share: int, speed_kph: int, rain_probability: int) -> NoiseResult:
        raw_features = np.array([[traffic, motorcycle_share, bus_share, speed_kph, rain_probability]])
        contributors = None
        if self.model_path.exists():
            from tensorflow import keras  # Optional production dependency.
            model = keras.models.load_model(self.model_path)
            if not self.scaler_path.exists():
                raise RuntimeError("Trained LSTM is missing its fitted noise_scaler.pkl artifact.")
            with self.scaler_path.open("rb") as file:
                scaled = pickle.load(file).transform(raw_features)
            window = int(model.input_shape[1] or 12)
            sequence = np.repeat(scaled[:, np.newaxis, :], window, axis=1)
            decibels = float(model.predict(sequence, verbose=0)[0][0])
            version = "lstm-v1"
            if self.background_path.exists():
                try:
                    from ml.explain import explain_lstm
                    contributors = explain_lstm(model, np.load(self.background_path), sequence)
                except (ImportError, ValueError):
                    # The LSTM output remains valid; serving can retry SHAP asynchronously.
                    contributors = None
        else:
            decibels = 48 + traffic * .22 + motorcycle_share * .13 + bus_share * .08 - speed_kph * .035 + rain_probability * .02
            version = "baseline-v1-demo"
        contributors = contributors or [
            {"feature": "Traffic density", "impact_db": round(traffic * .22, 1)},
            {"feature": "Motorcycle share", "impact_db": round(motorcycle_share * .13, 1)},
            {"feature": "Bus share", "impact_db": round(bus_share * .08, 1)},
            {"feature": "Average speed", "impact_db": round(-speed_kph * .035, 1)},
        ]
        positive = [c["feature"].lower() for c in contributors[:2] if c["impact_db"] > 1]
        summary = "This route is noisy because of " + " and ".join(positive) + "." if positive else "This route has relatively low predicted road noise."
        return NoiseResult(round(max(40, min(100, decibels)), 1), version, contributors, summary)
