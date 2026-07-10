"""Generates realistic synthetic laptop/IoT telemetry with labeled anomaly
episodes, since we don't yet have months of real failure data to train on.

Design: each simulated device is a state machine that spends most of its time
in `normal` and occasionally transitions into one of four fault modes for a
random duration:
  - cpu_overload        : sustained high CPU + correlated temp/load rise
  - memory_leak         : slow, monotonic memory ramp that doesn't recover
  - disk_degradation    : rising disk usage with erratic/slow I/O throughput
  - abnormal_behavior    : multi-metric irregular spikes (catch-all anomaly)

Run: python generate_data.py  ->  writes ml/data/dataset.csv
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from feature_lib import add_rolling_features  # noqa: E402

RNG = np.random.default_rng(42)

N_DEVICES = 12
SAMPLES_PER_DEVICE = 3000  # at 5s cadence ~= 4.2 hours per device
STATES = ["normal", "cpu_overload", "memory_leak", "disk_degradation", "abnormal_behavior"]

# Mean episode lengths (in samples) and transition probability out of "normal"
ANOMALY_ENTRY_PROB = 0.004  # per-sample chance of leaving 'normal' each step
EPISODE_LEN_RANGE = {
    "cpu_overload": (40, 150),
    "memory_leak": (200, 600),
    "disk_degradation": (150, 400),
    "abnormal_behavior": (30, 120),
}


def simulate_device(device_id: int) -> pd.DataFrame:
    rows = []
    state = "normal"
    state_progress = 0
    state_len = 0

    # Baseline per-device characteristics so devices aren't all identical
    base_cpu = RNG.uniform(12, 25)
    base_mem = RNG.uniform(35, 55)
    base_disk = RNG.uniform(30, 60)
    total_mem_mb = RNG.choice([8192, 16384, 32768])
    total_disk_gb = RNG.choice([256, 512, 1024])
    core_count = int(RNG.choice([4, 6, 8, 12, 16]))

    memory_leak_start = base_mem
    disk_growth_base = base_disk

    for t in range(SAMPLES_PER_DEVICE):
        if state == "normal" and RNG.random() < ANOMALY_ENTRY_PROB:
            state = RNG.choice(["cpu_overload", "memory_leak", "disk_degradation", "abnormal_behavior"])
            lo, hi = EPISODE_LEN_RANGE[state]
            state_len = int(RNG.integers(lo, hi))
            state_progress = 0
            if state == "memory_leak":
                memory_leak_start = base_mem

        # ---- generate metrics for current state ----
        if state == "normal":
            cpu = np.clip(RNG.normal(base_cpu, 6), 1, 55)
            mem = np.clip(RNG.normal(base_mem, 4), 10, 70)
            disk_growth_base += RNG.uniform(0, 0.0008)  # very slow organic growth
            disk = np.clip(disk_growth_base + RNG.normal(0, 0.3), 5, 80)
            disk_read = np.clip(RNG.normal(1.2, 0.8), 0, 10)
            disk_write = np.clip(RNG.normal(0.8, 0.6), 0, 10)
            net_sent = np.clip(RNG.exponential(0.4), 0, 8)
            net_recv = np.clip(RNG.exponential(0.8), 0, 12)
            temp = np.clip(30 + cpu * 0.35 + RNG.normal(0, 2), 28, 70)
            load1 = np.clip(cpu / 100 * core_count * RNG.uniform(0.6, 1.0), 0, core_count * 1.2)
            gpu = np.clip(RNG.exponential(4), 0, 30)
            gpu_mem = np.clip(gpu * RNG.uniform(0.5, 1.2), 0, 40)
            proc_count = int(np.clip(RNG.normal(180, 15), 90, 260))

        elif state == "cpu_overload":
            progress_ratio = state_progress / max(state_len, 1)
            cpu = np.clip(RNG.normal(93, 4), 65, 100)
            mem = np.clip(RNG.normal(base_mem + 8, 5), 10, 85)
            disk = np.clip(disk_growth_base + RNG.normal(0, 0.3), 5, 85)
            disk_read = np.clip(RNG.normal(1.0, 0.7), 0, 10)
            disk_write = np.clip(RNG.normal(0.7, 0.5), 0, 10)
            net_sent = np.clip(RNG.exponential(0.4), 0, 8)
            net_recv = np.clip(RNG.exponential(0.8), 0, 12)
            temp = np.clip(35 + cpu * 0.5 + RNG.normal(0, 2), 30, 98)
            load1 = np.clip(cpu / 100 * core_count * RNG.uniform(0.9, 1.3), 0, core_count * 1.8)
            gpu = np.clip(RNG.exponential(6), 0, 40)
            gpu_mem = np.clip(gpu * RNG.uniform(0.5, 1.2), 0, 50)
            proc_count = int(np.clip(RNG.normal(210, 25), 100, 320))

        elif state == "memory_leak":
            # Monotonic ramp toward saturation, small noise, doesn't recover mid-episode
            progress_ratio = state_progress / max(state_len, 1)
            memory_leak_start = min(97, memory_leak_start + RNG.uniform(0.05, 0.25))
            cpu = np.clip(RNG.normal(base_cpu + 5, 6), 1, 70)
            mem = np.clip(memory_leak_start + RNG.normal(0, 1.5), 10, 99)
            disk = np.clip(disk_growth_base + RNG.normal(0, 0.3), 5, 85)
            disk_read = np.clip(RNG.normal(1.2, 0.8), 0, 10)
            disk_write = np.clip(RNG.normal(0.8, 0.6), 0, 10)
            net_sent = np.clip(RNG.exponential(0.4), 0, 8)
            net_recv = np.clip(RNG.exponential(0.8), 0, 12)
            temp = np.clip(30 + cpu * 0.35 + RNG.normal(0, 2), 28, 75)
            load1 = np.clip(cpu / 100 * core_count * RNG.uniform(0.6, 1.1), 0, core_count * 1.3)
            gpu = np.clip(RNG.exponential(4), 0, 30)
            gpu_mem = np.clip(gpu * RNG.uniform(0.5, 1.2), 0, 40)
            proc_count = int(np.clip(RNG.normal(190, 20) + progress_ratio * 40, 90, 300))

        elif state == "disk_degradation":
            progress_ratio = state_progress / max(state_len, 1)
            disk_growth_base += RNG.uniform(0.01, 0.05)  # accelerated growth
            disk = np.clip(disk_growth_base + RNG.normal(0, 0.5), 5, 99)
            # Erratic / degraded throughput: high variance, occasional near-zero (stalls)
            disk_read = np.clip(RNG.choice([RNG.normal(0.2, 0.2), RNG.normal(8, 4)], p=None), 0, 20)
            disk_write = np.clip(RNG.choice([RNG.normal(0.1, 0.1), RNG.normal(6, 3)]), 0, 20)
            cpu = np.clip(RNG.normal(base_cpu + 8, 8), 1, 80)
            mem = np.clip(RNG.normal(base_mem + 5, 5), 10, 85)
            net_sent = np.clip(RNG.exponential(0.4), 0, 8)
            net_recv = np.clip(RNG.exponential(0.8), 0, 12)
            temp = np.clip(30 + cpu * 0.35 + RNG.normal(0, 2), 28, 75)
            load1 = np.clip(cpu / 100 * core_count * RNG.uniform(0.7, 1.2), 0, core_count * 1.4)
            gpu = np.clip(RNG.exponential(4), 0, 30)
            gpu_mem = np.clip(gpu * RNG.uniform(0.5, 1.2), 0, 40)
            proc_count = int(np.clip(RNG.normal(190, 20), 90, 280))

        else:  # abnormal_behavior — irregular multi-metric spikes, catch-all
            cpu = np.clip(RNG.normal(55, 20), 1, 100)
            mem = np.clip(RNG.normal(base_mem + 15, 12), 10, 95)
            disk = np.clip(disk_growth_base + RNG.normal(0, 0.5), 5, 90)
            disk_read = np.clip(RNG.normal(3, 3), 0, 20)
            disk_write = np.clip(RNG.normal(2, 2), 0, 20)
            net_sent = np.clip(RNG.exponential(4), 0, 25)  # unusually high egress
            net_recv = np.clip(RNG.exponential(3), 0, 20)
            temp = np.clip(35 + cpu * 0.4 + RNG.normal(0, 4), 28, 95)
            load1 = np.clip(cpu / 100 * core_count * RNG.uniform(0.8, 1.6), 0, core_count * 2.0)
            gpu = np.clip(RNG.exponential(10), 0, 60)
            gpu_mem = np.clip(gpu * RNG.uniform(0.5, 1.3), 0, 70)
            proc_count = int(np.clip(RNG.normal(250, 40), 100, 400))

        cpu_freq = np.clip(RNG.normal(2800 + cpu * 5, 150), 800, 4800)
        swap = np.clip((mem - 60) * 0.8 + RNG.normal(0, 2), 0, 90) if mem > 60 else np.clip(RNG.normal(1, 1), 0, 15)
        battery = np.clip(100 - (t % 1200) / 12, 5, 100)
        plugged = bool(RNG.random() < 0.7)
        uptime = t * 5 + RNG.integers(0, 5)

        rows.append(
            {
                "device_id": device_id,
                "t": t,
                "cpu_percent": round(float(cpu), 2),
                "cpu_freq_mhz": round(float(cpu_freq), 1),
                "cpu_core_count": core_count,
                "load_avg_1m": round(float(load1), 2),
                "memory_percent": round(float(mem), 2),
                "memory_used_mb": round(float(mem / 100 * total_mem_mb), 1),
                "memory_total_mb": total_mem_mb,
                "swap_percent": round(float(max(swap, 0)), 2),
                "disk_percent": round(float(disk), 2),
                "disk_used_gb": round(float(disk / 100 * total_disk_gb), 1),
                "disk_total_gb": total_disk_gb,
                "disk_read_mb_s": round(float(disk_read), 2),
                "disk_write_mb_s": round(float(disk_write), 2),
                "net_sent_mb_s": round(float(net_sent), 2),
                "net_recv_mb_s": round(float(net_recv), 2),
                "temperature_c": round(float(temp), 2),
                "gpu_percent": round(float(gpu), 2),
                "gpu_memory_percent": round(float(gpu_mem), 2),
                "battery_percent": round(float(battery), 1),
                "battery_plugged": plugged,
                "uptime_seconds": uptime,
                "process_count": proc_count,
                "label": state,
            }
        )

        if state != "normal":
            state_progress += 1
            if state_progress >= state_len:
                state = "normal"
                state_progress = 0

    return pd.DataFrame(rows)


def main() -> None:
    out_dir = Path(__file__).resolve().parent / "data"
    out_dir.mkdir(parents=True, exist_ok=True)

    frames = [simulate_device(d) for d in range(N_DEVICES)]
    df = pd.concat(frames, ignore_index=True)
    df = df.sort_values(["device_id", "t"]).reset_index(drop=True)

    df = add_rolling_features(df, device_col="device_id")
    df["is_anomaly"] = (df["label"] != "normal").astype(int)

    out_path = out_dir / "dataset.csv"
    df.to_csv(out_path, index=False)

    print(f"Generated {len(df):,} rows across {N_DEVICES} simulated devices -> {out_path}")
    print("\nLabel distribution:")
    print(df["label"].value_counts())
    print(f"\nAnomaly rate: {df['is_anomaly'].mean():.2%}")


if __name__ == "__main__":
    main()
