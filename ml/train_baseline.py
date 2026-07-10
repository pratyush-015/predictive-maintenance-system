"""Trains the three classical baseline models and writes comparison metrics.

Models:
  - Isolation Forest  (unsupervised anomaly detection)
  - One-Class SVM     (unsupervised anomaly detection)
  - Random Forest     (supervised multi-class issue classifier; also used
                        for per-prediction explainability via feature
                        importances at serving time)

All three are evaluated on the SAME held-out test set using a unified binary
anomaly framing (is_anomaly True/False) so Accuracy/Precision/Recall/F1/
ROC-AUC are directly comparable across models, in addition to the Random
Forest's native multi-class report (saved separately for reference).

Run: python train_baseline.py   (writes into ml/models/)
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
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.svm import OneClassSVM

sys.path.insert(0, str(Path(__file__).resolve().parent))
from feature_lib import ALL_FEATURES  # noqa: E402

DATA_PATH = Path(__file__).resolve().parent / "data" / "dataset.csv"
MODEL_DIR = Path(__file__).resolve().parent / "models"
RANDOM_STATE = 42


def measure_inference_ms(predict_fn, X_sample: np.ndarray, n_repeats: int = 200) -> float:
    """Average single-sample inference latency in milliseconds."""
    idx = np.random.default_rng(0).integers(0, len(X_sample), size=min(n_repeats, len(X_sample)))
    start = time.perf_counter()
    for i in idx:
        predict_fn(X_sample[i : i + 1])
    elapsed = time.perf_counter() - start
    return (elapsed / len(idx)) * 1000.0


def evaluate_binary(name: str, y_true: np.ndarray, y_pred: np.ndarray, y_score: np.ndarray, inference_ms: float) -> dict:
    try:
        auc = roc_auc_score(y_true, y_score)
    except ValueError:
        auc = float("nan")
    metrics = {
        "model_name": name,
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
        "f1_score": round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
        "roc_auc": round(float(auc), 4) if auc == auc else 0.0,  # NaN check
        "inference_time_ms": round(inference_ms, 4),
    }
    print(f"\n=== {name} ===")
    for k, v in metrics.items():
        if k != "model_name":
            print(f"  {k:20s}: {v}")
    return metrics


def main() -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Loading dataset from {DATA_PATH} ...")
    df = pd.read_csv(DATA_PATH)

    X = df[ALL_FEATURES].values
    y_multiclass = df["label"].values
    y_binary = df["is_anomaly"].values

    X_train, X_test, y_train_bin, y_test_bin, y_train_mc, y_test_mc = train_test_split(
        X, y_binary, y_multiclass, test_size=0.25, random_state=RANDOM_STATE, stratify=y_binary
    )

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s = scaler.transform(X_test)

    comparison_entries = []

    # ---------------------------------------------------------------
    # 1) Isolation Forest — unsupervised, trained on the (mostly normal)
    #    training split; contamination set from empirical anomaly rate.
    # ---------------------------------------------------------------
    contamination = float(np.clip(y_train_bin.mean(), 0.01, 0.5))
    iso = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    iso.fit(X_train_s)
    iso_pred = (iso.predict(X_test_s) == -1).astype(int)
    iso_score = -iso.decision_function(X_test_s)  # higher = more anomalous
    iso_ms = measure_inference_ms(lambda x: iso.predict(x), X_test_s)
    comparison_entries.append(evaluate_binary("isolation_forest", y_test_bin, iso_pred, iso_score, iso_ms))
    joblib.dump(iso, MODEL_DIR / "isolation_forest.joblib")

    # ---------------------------------------------------------------
    # 2) One-Class SVM — unsupervised, trained on a subsample of normal
    #    data only (OC-SVM training cost grows quickly with N).
    # ---------------------------------------------------------------
    normal_mask_train = y_train_bin == 0
    X_normal = X_train_s[normal_mask_train]
    subsample_n = min(4000, len(X_normal))
    rng = np.random.default_rng(RANDOM_STATE)
    sub_idx = rng.choice(len(X_normal), size=subsample_n, replace=False)
    ocsvm = OneClassSVM(kernel="rbf", gamma="scale", nu=float(np.clip(contamination, 0.01, 0.3)))
    ocsvm.fit(X_normal[sub_idx])
    ocsvm_pred = (ocsvm.predict(X_test_s) == -1).astype(int)
    ocsvm_score = -ocsvm.decision_function(X_test_s)
    ocsvm_ms = measure_inference_ms(lambda x: ocsvm.predict(x), X_test_s)
    comparison_entries.append(evaluate_binary("one_class_svm", y_test_bin, ocsvm_pred, ocsvm_score, ocsvm_ms))
    joblib.dump(ocsvm, MODEL_DIR / "one_class_svm.joblib")

    # ---------------------------------------------------------------
    # 3) Random Forest — supervised multi-class issue classifier.
    #    Doubles as the live explainability + recommendation source.
    # ---------------------------------------------------------------
    rf = RandomForestClassifier(
        n_estimators=300,
        max_depth=14,
        min_samples_leaf=3,
        random_state=RANDOM_STATE,
        n_jobs=-1,
        class_weight="balanced",
    )
    rf.fit(X_train_s, y_train_mc)

    rf_pred_mc = rf.predict(X_test_s)
    rf_proba = rf.predict_proba(X_test_s)
    normal_idx = list(rf.classes_).index("normal")
    rf_anomaly_score = 1.0 - rf_proba[:, normal_idx]
    rf_pred_bin = (rf_pred_mc != "normal").astype(int)
    rf_ms = measure_inference_ms(lambda x: rf.predict(x), X_test_s)
    comparison_entries.append(evaluate_binary("random_forest", y_test_bin, rf_pred_bin, rf_anomaly_score, rf_ms))
    joblib.dump(rf, MODEL_DIR / "random_forest.joblib")

    print("\n=== Random Forest multi-class report (issue classification) ===")
    mc_report = classification_report(y_test_mc, rf_pred_mc, output_dict=True, zero_division=0)
    print(classification_report(y_test_mc, rf_pred_mc, zero_division=0))

    # ---------------------------------------------------------------
    # Persist shared artifacts
    # ---------------------------------------------------------------
    joblib.dump(scaler, MODEL_DIR / "scaler.joblib")

    issue_labels = sorted(df["label"].unique().tolist())
    metadata = {
        "feature_names": ALL_FEATURES,
        "issue_labels": issue_labels,
        "label_decoder": {lbl: lbl for lbl in issue_labels},
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "dataset_rows": int(len(df)),
        "anomaly_rate": round(float(y_binary.mean()), 4),
        "random_forest_multiclass_report": mc_report,
    }
    (MODEL_DIR / "metadata.json").write_text(json.dumps(metadata, indent=2))

    comparison_path = MODEL_DIR / "comparison.json"
    existing = {"models": []}
    if comparison_path.exists():
        try:
            existing = json.loads(comparison_path.read_text())
        except json.JSONDecodeError:
            pass
    # Replace any previous entries with the same model_name, keep others (e.g. deep models)
    existing_models = {m["model_name"]: m for m in existing.get("models", [])}
    for entry in comparison_entries:
        existing_models[entry["model_name"]] = entry
    all_models = list(existing_models.values())
    best = max(all_models, key=lambda m: m["f1_score"])["model_name"]
    comparison_path.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "models": all_models,
                "best_model": best,
            },
            indent=2,
        )
    )

    print(f"\nSaved models, scaler, metadata, and comparison to {MODEL_DIR}")
    print(f"Best model so far (by F1): {best}")


if __name__ == "__main__":
    main()
