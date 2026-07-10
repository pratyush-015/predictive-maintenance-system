"""Trains the two deep learning models and appends their metrics to the
shared model comparison report.

Models:
  - LSTM              : sequence classifier over a sliding window of recent
                         readings, predicts P(anomaly) — captures temporal
                         dependencies the tabular models can't see directly.
  - Autoencoder        : trained ONLY on normal data to learn a compressed
                         representation of "healthy" behavior; reconstruction
                         error on unseen data becomes the anomaly signal.
                         Also used at serving time as a secondary, unsupervised
                         cross-check on the Random Forest's classification
                         (see backend/app/ml_runtime/predictor.py).

Run: python train_deep.py   (writes into ml/models/, requires train_baseline.py
to have already produced scaler.joblib)
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split

sys.path.insert(0, str(Path(__file__).resolve().parent))
from feature_lib import ALL_FEATURES  # noqa: E402

import tensorflow as tf
from tensorflow import keras
from keras import layers

DATA_PATH = Path(__file__).resolve().parent / "data" / "dataset.csv"
MODEL_DIR = Path(__file__).resolve().parent / "models"
RANDOM_STATE = 42
SEQ_LEN = 6  # matches ROLL_WINDOW used elsewhere — ~30s of history at 5s cadence

tf.random.set_seed(RANDOM_STATE)
np.random.seed(RANDOM_STATE)


def build_sequences(df: pd.DataFrame, feature_cols: list[str], seq_len: int):
    """Builds sliding-window sequences per device so no window crosses a
    device boundary. Label of a sequence = label of its LAST timestep."""
    X_seqs, y_bin, y_mc, device_ids = [], [], [], []
    for device_id, g in df.groupby("device_id"):
        g = g.sort_values("t")
        feats = g[feature_cols].values
        labels = g["label"].values
        is_anom = g["is_anomaly"].values
        for i in range(seq_len - 1, len(g)):
            X_seqs.append(feats[i - seq_len + 1 : i + 1])
            y_bin.append(is_anom[i])
            y_mc.append(labels[i])
            device_ids.append(device_id)
    return np.array(X_seqs), np.array(y_bin), np.array(y_mc), np.array(device_ids)


def measure_inference_ms(model, X_sample: np.ndarray, n_repeats: int = 100) -> float:
    idx = np.random.default_rng(0).integers(0, len(X_sample), size=min(n_repeats, len(X_sample)))
    start = time.perf_counter()
    for i in idx:
        model.predict(X_sample[i : i + 1], verbose=0)
    elapsed = time.perf_counter() - start
    return (elapsed / len(idx)) * 1000.0


def evaluate_binary(name, y_true, y_pred, y_score, inference_ms) -> dict:
    try:
        auc = roc_auc_score(y_true, y_score)
    except ValueError:
        auc = 0.0
    metrics = {
        "model_name": name,
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
        "f1_score": round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
        "roc_auc": round(float(auc), 4),
        "inference_time_ms": round(inference_ms, 4),
    }
    print(f"\n=== {name} ===")
    for k, v in metrics.items():
        if k != "model_name":
            print(f"  {k:20s}: {v}")
    return metrics


def main() -> None:
    print(f"Loading dataset from {DATA_PATH} ...")
    df = pd.read_csv(DATA_PATH).sort_values(["device_id", "t"]).reset_index(drop=True)

    scaler = joblib.load(MODEL_DIR / "scaler.joblib")
    df_scaled = df.copy()
    df_scaled[ALL_FEATURES] = scaler.transform(df[ALL_FEATURES].values)

    # Split by DEVICE (not row) so sequences never leak across train/test —
    # devices held out entirely for test simulate "unseen machines".
    device_ids = df["device_id"].unique()
    train_devices, test_devices = train_test_split(device_ids, test_size=0.3, random_state=RANDOM_STATE)

    train_df = df_scaled[df_scaled["device_id"].isin(train_devices)]
    test_df = df_scaled[df_scaled["device_id"].isin(test_devices)]

    # =================================================================
    # 1) LSTM sequence classifier
    # =================================================================
    print("\nBuilding LSTM sequences...")
    X_train_seq, y_train_bin, _, _ = build_sequences(train_df, ALL_FEATURES, SEQ_LEN)
    X_test_seq, y_test_bin, _, _ = build_sequences(test_df, ALL_FEATURES, SEQ_LEN)
    print(f"Train sequences: {X_train_seq.shape}, Test sequences: {X_test_seq.shape}")

    n_features = len(ALL_FEATURES)
    lstm = keras.Sequential(
        [
            layers.Input(shape=(SEQ_LEN, n_features)),
            layers.LSTM(32, return_sequences=True),
            layers.Dropout(0.2),
            layers.LSTM(16),
            layers.Dropout(0.2),
            layers.Dense(16, activation="relu"),
            layers.Dense(1, activation="sigmoid"),
        ],
        name="lstm_anomaly_classifier",
    )
    lstm.compile(optimizer=keras.optimizers.Adam(1e-3), loss="binary_crossentropy", metrics=["accuracy"])

    class_weight = {
        0: 1.0,
        1: float(len(y_train_bin) - y_train_bin.sum()) / max(y_train_bin.sum(), 1),
    }
    lstm.fit(
        X_train_seq,
        y_train_bin,
        validation_split=0.15,
        epochs=12,
        batch_size=128,
        class_weight=class_weight,
        verbose=2,
        callbacks=[keras.callbacks.EarlyStopping(patience=3, restore_best_weights=True, monitor="val_loss")],
    )

    lstm_score = lstm.predict(X_test_seq, verbose=0).ravel()
    lstm_pred = (lstm_score >= 0.5).astype(int)
    lstm_ms = measure_inference_ms(lstm, X_test_seq)
    comparison_entries = [evaluate_binary("lstm", y_test_bin, lstm_pred, lstm_score, lstm_ms)]

    lstm.save(MODEL_DIR / "lstm.keras")

    # =================================================================
    # 2) Autoencoder — trained on NORMAL rows only (single-timestep vector,
    #    so it can run cheaply inline at serving time without needing a
    #    sequence buffer).
    # =================================================================
    print("\nTraining Autoencoder on normal-only data...")
    normal_train = train_df[train_df["label"] == "normal"][ALL_FEATURES].values
    X_test_flat = test_df[ALL_FEATURES].values
    y_test_flat = test_df["is_anomaly"].values

    ae = keras.Sequential(
        [
            layers.Input(shape=(n_features,)),
            layers.Dense(16, activation="relu"),
            layers.Dense(8, activation="relu"),
            layers.Dense(4, activation="relu"),
            layers.Dense(8, activation="relu"),
            layers.Dense(16, activation="relu"),
            layers.Dense(n_features, activation="linear"),
        ],
        name="autoencoder",
    )
    ae.compile(optimizer=keras.optimizers.Adam(1e-3), loss="mse")
    ae.fit(
        normal_train,
        normal_train,
        validation_split=0.15,
        epochs=25,
        batch_size=128,
        verbose=2,
        callbacks=[keras.callbacks.EarlyStopping(patience=4, restore_best_weights=True, monitor="val_loss")],
    )

    # Reconstruction error on held-out NORMAL validation rows sets the anomaly threshold
    recon_normal = ae.predict(normal_train, verbose=0)
    normal_errors = np.mean(np.square(normal_train - recon_normal), axis=1)
    threshold = float(np.percentile(normal_errors, 95))

    recon_test = ae.predict(X_test_flat, verbose=0)
    test_errors = np.mean(np.square(X_test_flat - recon_test), axis=1)
    ae_pred = (test_errors >= threshold).astype(int)
    ae_ms = measure_inference_ms(ae, X_test_flat)
    comparison_entries.append(evaluate_binary("autoencoder", y_test_flat, ae_pred, test_errors, ae_ms))

    ae.save(MODEL_DIR / "autoencoder.keras")

    # =================================================================
    # Merge into comparison.json (keep baseline entries already written)
    # =================================================================
    comparison_path = MODEL_DIR / "comparison.json"
    existing = json.loads(comparison_path.read_text()) if comparison_path.exists() else {"models": []}
    existing_models = {m["model_name"]: m for m in existing.get("models", [])}
    for entry in comparison_entries:
        existing_models[entry["model_name"]] = entry
    all_models = list(existing_models.values())
    best = max(all_models, key=lambda m: m["f1_score"])["model_name"]
    comparison_path.write_text(
        json.dumps(
            {"generated_at": datetime.now(timezone.utc).isoformat(), "models": all_models, "best_model": best},
            indent=2,
        )
    )

    # Update metadata with autoencoder threshold + sequence length for serving code
    metadata_path = MODEL_DIR / "metadata.json"
    metadata = json.loads(metadata_path.read_text())
    metadata["autoencoder_threshold"] = threshold
    metadata["lstm_sequence_length"] = SEQ_LEN
    metadata_path.write_text(json.dumps(metadata, indent=2))

    print(f"\nAutoencoder anomaly threshold (95th pct normal reconstruction error): {threshold:.5f}")
    print(f"Saved deep models to {MODEL_DIR}. Overall best model (by F1): {best}")


if __name__ == "__main__":
    main()
