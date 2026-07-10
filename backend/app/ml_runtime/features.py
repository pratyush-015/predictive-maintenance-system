"""Builds the exact feature vector the trained ML models expect from a live
metric reading plus its recent device history.

IMPORTANT: this mirrors `ml/feature_lib.py` used at training time. If you
change feature engineering, update BOTH files (see docs/ARCHITECTURE.md for
why these aren't a single shared package yet, and how to refactor that).
"""
from __future__ import annotations

import numpy as np
from sqlalchemy.orm import Session

from app.db.models import Metric

ROLL_WINDOW = 6  # number of recent readings used for rolling stats (~30s at 5s interval)

BASE_FEATURES = [
    "cpu_percent",
    "cpu_freq_mhz",
    "load_avg_1m",
    "memory_percent",
    "swap_percent",
    "disk_percent",
    "disk_read_mb_s",
    "disk_write_mb_s",
    "net_sent_mb_s",
    "net_recv_mb_s",
    "temperature_c",
    "gpu_percent",
    "gpu_memory_percent",
    "process_count",
]

ROLLING_FEATURES = [
    "cpu_percent_roll_mean",
    "cpu_percent_roll_std",
    "cpu_percent_roll_max",
    "memory_percent_roll_mean",
    "memory_percent_roll_std",
    "memory_percent_roll_slope",
    "disk_percent_roll_slope",
    "net_sent_mb_s_roll_mean",
]

ALL_FEATURES = BASE_FEATURES + ROLLING_FEATURES


def _slope(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    x = np.arange(len(values))
    y = np.array(values)
    # simple linear regression slope
    denom = (x.var() * len(x))
    if denom == 0:
        return 0.0
    return float(np.polyfit(x, y, 1)[0])


def build_feature_vector(db: Session, device_id: int, current: Metric) -> dict[str, float]:
    """Fetch the last ROLL_WINDOW metrics (including current) and compute the
    full named feature dict the models were trained on."""
    history: list[Metric] = (
        db.query(Metric)
        .filter(Metric.device_id == device_id)
        .order_by(Metric.timestamp.desc())
        .limit(ROLL_WINDOW)
        .all()
    )
    history = list(reversed(history))  # chronological order
    if not history or history[-1].id != current.id:
        history.append(current)

    cpu_vals = [m.cpu_percent for m in history]
    mem_vals = [m.memory_percent for m in history]
    disk_vals = [m.disk_percent for m in history]
    net_vals = [m.net_sent_mb_s for m in history]

    features = {name: float(getattr(current, name)) for name in BASE_FEATURES}
    features.update(
        {
            "cpu_percent_roll_mean": float(np.mean(cpu_vals)),
            "cpu_percent_roll_std": float(np.std(cpu_vals)),
            "cpu_percent_roll_max": float(np.max(cpu_vals)),
            "memory_percent_roll_mean": float(np.mean(mem_vals)),
            "memory_percent_roll_std": float(np.std(mem_vals)),
            "memory_percent_roll_slope": _slope(mem_vals),
            "disk_percent_roll_slope": _slope(disk_vals),
            "net_sent_mb_s_roll_mean": float(np.mean(net_vals)),
        }
    )
    return features


def to_vector(features: dict[str, float], feature_names: list[str]) -> np.ndarray:
    return np.array([[features.get(name, 0.0) for name in feature_names]])
