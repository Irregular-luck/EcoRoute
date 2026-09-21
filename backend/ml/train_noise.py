"""Train the EcoRoute LSTM and serialize its feature scaler.

Input CSV must contain the five feature columns below plus `noise_db`. Rows must
be chronologically ordered within a road segment; a real pipeline should split by
segment/time to avoid temporal leakage.
"""
from pathlib import Path
import argparse
import pickle

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from tensorflow import keras

FEATURES = ["traffic_score", "motorcycle_share", "bus_share", "speed_kph", "rain_probability"]


def sequences(values, target, window: int):
    x, y = [], []
    for index in range(window - 1, len(values)):
        x.append(values[index - window + 1:index + 1])
        y.append(target[index])
    return x, y


def train(csv_path: Path, output_dir: Path, window: int = 12) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    frame = pd.read_csv(csv_path).dropna(subset=[*FEATURES, "noise_db"])
    if len(frame) < window + 20:
        raise ValueError(f"At least {window + 20} labelled rows are required.")
    scaler = StandardScaler().fit(frame[FEATURES])
    x, y = sequences(scaler.transform(frame[FEATURES]), frame["noise_db"].to_numpy(), window)
    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=.2, shuffle=False)
    model = keras.Sequential([
        keras.layers.Input(shape=(window, len(FEATURES))),
        keras.layers.LSTM(64, dropout=.15, recurrent_dropout=0.0),
        keras.layers.Dense(24, activation="relu"),
        keras.layers.Dense(1),
    ])
    model.compile(optimizer=keras.optimizers.Adam(learning_rate=1e-3), loss="mse", metrics=["mae"])
    model.fit(x_train, y_train, validation_data=(x_test, y_test), epochs=80, batch_size=32, callbacks=[keras.callbacks.EarlyStopping(monitor="val_loss", patience=8, restore_best_weights=True)])
    model.save(output_dir / "noise_lstm.keras")
    with (output_dir / "noise_scaler.pkl").open("wb") as file:
        pickle.dump(scaler, file)
    # A bounded representative sample keeps serving-side local SHAP explanations practical.
    import numpy as np
    np.save(output_dir / "shap_background.npy", x_train[:min(100, len(x_train))])
    print(dict(zip(model.metrics_names, model.evaluate(x_test, y_test, verbose=0))))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("ml_models"))
    parser.add_argument("--window", type=int, default=12)
    args = parser.parse_args()
    train(args.csv, args.output_dir, args.window)
