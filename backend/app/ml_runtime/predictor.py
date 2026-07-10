"""Inference + lightweight explainability + recommendation generation.

Explainability note: we use importance x deviation-from-baseline as a fast,
dependency-light approximation of per-prediction feature attribution. It is
not as faithful as SHAP's TreeExplainer, but it's good enough to tell a user
*why* an alert fired without adding a heavy dependency. Swapping in
`shap.TreeExplainer` for the RandomForest model is a documented drop-in
upgrade (see docs/ARCHITECTURE.md).
"""
from __future__ import annotations

from typing import Any

import numpy as np

from app.core.config import settings
from app.ml_runtime.features import ALL_FEATURES
from app.ml_runtime.model_loader import registry

RECOMMENDATIONS = {
    "cpu_overload": "CPU sustained near capacity. Identify top CPU-consuming processes and consider throttling, "
    "killing runaway processes, or scaling compute resources.",
    "memory_leak": "Memory usage is trending upward without recovery, a classic leak signature. Restart the "
    "suspect process/service during a maintenance window and monitor for recurrence; profile for leaks.",
    "disk_degradation": "Disk usage/I-O pattern indicates degradation or imminent capacity exhaustion. Free up "
    "space, check SMART health status, and plan storage expansion or disk replacement.",
    "abnormal_behavior": "Metric pattern deviates from learned normal behavior across multiple signals. Investigate "
    "recent process/network activity for unauthorized or runaway workloads.",
    "normal": "All monitored parameters are within learned normal operating ranges.",
}


def _explain_with_rf(model, feature_vec: np.ndarray, feature_names: list[str], top_k: int = 5) -> dict[str, float]:
    if not hasattr(model, "feature_importances_"):
        return {}
    importances = model.feature_importances_
    scaler = registry.scaler
    if scaler is not None:
        z = (feature_vec[0] - scaler.mean_) / np.where(scaler.scale_ == 0, 1, scaler.scale_)
    else:
        z = feature_vec[0]
    contribution = importances * np.abs(z)
    order = np.argsort(contribution)[::-1][:top_k]
    return {feature_names[i]: round(float(contribution[i]), 4) for i in order if contribution[i] > 0}


def predict(features: dict[str, float]) -> dict[str, Any]:
    registry.ensure_loaded()

    if not registry.models or not registry.feature_names:
        return {
            "model_name": "none",
            "is_anomaly": False,
            "anomaly_score": 0.0,
            "predicted_issue": "normal",
            "confidence": 0.0,
            "recommendation": "ML models not trained/loaded yet. Run `ml/train_baseline.py` and "
            "`ml/train_deep.py`, then POST /api/v1/predictions/reload-models.",
            "explanation": {},
        }

    feature_names = registry.feature_names
    raw_vec = np.array([[features.get(name, 0.0) for name in feature_names]])
    vec = registry.scaler.transform(raw_vec) if registry.scaler is not None else raw_vec

    # `anomaly_score` is always the Isolation Forest's continuous 0-1 output —
    # useful for trend charts even on readings that aren't flagged as an
    # anomaly. It does NOT independently decide `is_anomaly`; that decision
    # has one single source of truth to avoid the two ever disagreeing (see
    # note below on why Random Forest is that source).
    iso = registry.models.get("isolation_forest") or registry.models.get(settings.DEFAULT_ANOMALY_MODEL)
    model_name = "isolation_forest" if "isolation_forest" in registry.models else next(iter(registry.models))
    anomaly_score = 0.0
    iso_flagged = False
    if iso is not None and hasattr(iso, "decision_function"):
        raw_score = float(iso.decision_function(vec)[0])
        anomaly_score = float(np.clip(0.5 - raw_score, 0.0, 1.0))
        iso_flagged = bool(iso.predict(vec)[0] == -1)

    # Primary classification comes from the supervised Random Forest — it's
    # both far more accurate on our held-out evaluation (~97% vs ~70-80% for
    # the unsupervised models, see ml/models/comparison.json) AND the only
    # model that names *which* issue is occurring, so it's the single source
    # of truth for `is_anomaly` + `predicted_issue` together. This guarantees
    # the two fields can never contradict each other in the API response.
    predicted_issue = "normal"
    confidence = 1.0 - anomaly_score
    is_anomaly = False
    explanation: dict[str, float] = {}

    rf = registry.models.get("random_forest")
    if rf is not None and hasattr(rf, "predict_proba"):
        proba = rf.predict_proba(vec)[0]
        classes = list(rf.classes_)
        best_idx = int(np.argmax(proba))
        rf_label = classes[best_idx]
        rf_confidence = float(proba[best_idx])
        label_map = registry.metadata.get("label_decoder", {})
        predicted_issue = label_map.get(str(rf_label), str(rf_label))
        confidence = rf_confidence
        is_anomaly = predicted_issue != "normal" and rf_confidence >= 0.5
        if is_anomaly:
            explanation = _explain_with_rf(rf, vec, feature_names)
    else:
        # No supervised model loaded — fall back to Isolation Forest alone.
        is_anomaly = iso_flagged
        predicted_issue = "abnormal_behavior" if iso_flagged else "normal"
        confidence = round(anomaly_score if iso_flagged else 1.0 - anomaly_score, 4)

    # Secondary, fully-unsupervised cross-check: the autoencoder's
    # reconstruction error is cheap to compute inline, so we always attach it
    # to the explanation for observability. It's only allowed to ESCALATE a
    # confident "normal" RF verdict — and only when Isolation Forest agrees
    # too — because a single unsupervised model disagreeing with a 97%-
    # accurate classifier is more often noise than a genuinely novel failure
    # mode. Requiring two independent unsupervised signals to agree before
    # overriding keeps the false-positive rate low.
    autoencoder = registry.models.get("autoencoder")
    threshold = registry.metadata.get("autoencoder_threshold")
    if autoencoder is not None and threshold is not None:
        try:
            recon = autoencoder.predict(vec, verbose=0)
            recon_error = float(np.mean(np.square(vec - recon)))
            explanation.setdefault("_autoencoder_reconstruction_error", round(recon_error, 5))
            ae_flagged = recon_error >= threshold
            if not is_anomaly and ae_flagged and iso_flagged:
                is_anomaly = True
                predicted_issue = "abnormal_behavior"
                confidence = round(float(np.clip(recon_error / (threshold * 2), 0.5, 0.85)), 4)
        except Exception:
            pass

    if not is_anomaly:
        predicted_issue = "normal"

    return {
        "model_name": model_name,
        "is_anomaly": is_anomaly,
        "anomaly_score": round(anomaly_score, 4),
        "predicted_issue": predicted_issue,
        "confidence": round(float(confidence), 4),
        "recommendation": RECOMMENDATIONS.get(predicted_issue, RECOMMENDATIONS["abnormal_behavior"]),
        "explanation": explanation,
    }
