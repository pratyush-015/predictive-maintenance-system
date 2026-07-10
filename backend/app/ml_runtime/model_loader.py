"""Loads trained ML artifacts produced by `ml/train_baseline.py` and
`ml/train_deep.py`. Models are loaded once and cached in-process; call
`reload()` (exposed via an admin API route) after retraining to hot-swap
without restarting the API.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Optional

import joblib
import numpy as np

from app.core.config import settings

logger = logging.getLogger("aiops.ml")


class ModelRegistry:
    def __init__(self) -> None:
        self.models: dict[str, Any] = {}
        self.scaler = None
        self.metadata: dict[str, Any] = {}
        self.comparison: dict[str, Any] = {}
        self._loaded = False

    @property
    def model_dir(self) -> Path:
        # Resolve relative to the backend app directory so it works regardless of CWD
        base = Path(__file__).resolve().parent.parent.parent
        path = (base / settings.ML_MODEL_DIR).resolve()
        return path

    def reload(self) -> None:
        d = self.model_dir
        self.models = {}
        self.scaler = None
        self.metadata = {}
        self.comparison = {}

        if not d.exists():
            logger.warning("Model directory %s does not exist yet — predictions disabled until trained.", d)
            self._loaded = False
            return

        metadata_path = d / "metadata.json"
        if metadata_path.exists():
            self.metadata = json.loads(metadata_path.read_text())

        scaler_path = d / "scaler.joblib"
        if scaler_path.exists():
            self.scaler = joblib.load(scaler_path)

        for f in d.glob("*.joblib"):
            if f.stem == "scaler":
                continue
            try:
                self.models[f.stem] = joblib.load(f)
                logger.info("Loaded model '%s' from %s", f.stem, f)
            except Exception:
                logger.exception("Failed to load model %s", f)

        # Optional deep learning models (.keras) — loaded lazily/optionally so
        # the API still boots fine on machines without TensorFlow installed.
        keras_files = list(d.glob("*.keras"))
        if keras_files:
            try:
                import tensorflow as tf  # local import: optional heavy dependency

                for f in keras_files:
                    try:
                        self.models[f.stem] = tf.keras.models.load_model(f)
                        logger.info("Loaded deep learning model '%s' from %s", f.stem, f)
                    except Exception:
                        logger.exception("Failed to load Keras model %s", f)
            except ImportError:
                logger.info("TensorFlow not installed — skipping %d .keras model(s).", len(keras_files))

        comparison_path = d / "comparison.json"
        if comparison_path.exists():
            self.comparison = json.loads(comparison_path.read_text())

        self._loaded = bool(self.models)

    def ensure_loaded(self) -> None:
        if not self._loaded:
            self.reload()

    @property
    def feature_names(self) -> list[str]:
        return self.metadata.get("feature_names", [])

    @property
    def issue_labels(self) -> list[str]:
        return self.metadata.get("issue_labels", ["normal", "cpu_overload", "memory_leak", "disk_degradation", "abnormal_behavior"])


registry = ModelRegistry()
