"""Feature engineering shared by all training scripts.

CRITICAL: this must stay in lockstep with
`backend/app/ml_runtime/features.py` — the same named features, in the same
order, computed the same way — or trained models will silently receive
garbled inputs at serving time. See docs/ARCHITECTURE.md for the plan to
extract this into one shared package.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

ROLL_WINDOW = 6  # ~30s of history at a 5s collection interval

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


def _rolling_slope(series: pd.Series, window: int) -> pd.Series:
    def slope(vals):
        if len(vals) < 2:
            return 0.0
        x = np.arange(len(vals))
        y = np.asarray(vals)
        if x.var() == 0:
            return 0.0
        return float(np.polyfit(x, y, 1)[0])

    return series.rolling(window=window, min_periods=1).apply(slope, raw=False)


def add_rolling_features(df: pd.DataFrame, device_col: str = "device_id") -> pd.DataFrame:
    """Adds ROLLING_FEATURES columns in place, computed per-device on
    chronologically sorted data (must be pre-sorted by [device_col, timestamp])."""
    df = df.copy()
    grouped_cpu = df.groupby(device_col)["cpu_percent"]
    grouped_mem = df.groupby(device_col)["memory_percent"]
    grouped_disk = df.groupby(device_col)["disk_percent"]
    grouped_net = df.groupby(device_col)["net_sent_mb_s"]

    df["cpu_percent_roll_mean"] = grouped_cpu.transform(lambda s: s.rolling(ROLL_WINDOW, min_periods=1).mean())
    df["cpu_percent_roll_std"] = grouped_cpu.transform(lambda s: s.rolling(ROLL_WINDOW, min_periods=1).std().fillna(0.0))
    df["cpu_percent_roll_max"] = grouped_cpu.transform(lambda s: s.rolling(ROLL_WINDOW, min_periods=1).max())
    df["memory_percent_roll_mean"] = grouped_mem.transform(lambda s: s.rolling(ROLL_WINDOW, min_periods=1).mean())
    df["memory_percent_roll_std"] = grouped_mem.transform(lambda s: s.rolling(ROLL_WINDOW, min_periods=1).std().fillna(0.0))
    df["memory_percent_roll_slope"] = df.groupby(device_col)["memory_percent"].transform(
        lambda s: _rolling_slope(s, ROLL_WINDOW)
    )
    df["disk_percent_roll_slope"] = df.groupby(device_col)["disk_percent"].transform(
        lambda s: _rolling_slope(s, ROLL_WINDOW)
    )
    df["net_sent_mb_s_roll_mean"] = grouped_net.transform(lambda s: s.rolling(ROLL_WINDOW, min_periods=1).mean())

    return df
