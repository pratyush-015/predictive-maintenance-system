"""Cross-platform system telemetry collector.

Collects the parameters called out in the project brief: CPU, RAM, disk,
network, temperature, GPU, battery, uptime, and running processes.

Notes on cross-platform support (documented here so future contributors
don't "fix" what's actually a platform limitation):
  - `sensors_temperatures()` is Linux-only in psutil; returns {} elsewhere.
  - `getloadavg()` is emulated by psutil on Windows but less meaningful there.
  - GPU stats use `nvidia-smi` if present (NVIDIA only); otherwise 0. AMD/
    Apple Silicon GPU support is a documented future extension point.
"""
from __future__ import annotations

import logging
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import psutil

logger = logging.getLogger("aiops.agent.collector")

_NVIDIA_SMI = shutil.which("nvidia-smi")


@dataclass
class _IOState:
    disk_read_bytes: int = 0
    disk_write_bytes: int = 0
    net_sent_bytes: int = 0
    net_recv_bytes: int = 0
    timestamp: float = field(default_factory=time.time)


class MetricsCollector:
    def __init__(self, top_n_processes: int = 5) -> None:
        self.top_n_processes = top_n_processes
        self._prev_io: Optional[_IOState] = None
        # Prime per-process cpu_percent (first call always returns 0.0 by design)
        for p in psutil.process_iter():
            try:
                p.cpu_percent(None)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        psutil.cpu_percent(None)  # prime system-wide cpu percent too

    # ---- individual metric groups -------------------------------------------------

    def _cpu(self) -> dict[str, Any]:
        freq = psutil.cpu_freq()
        try:
            load1, _, _ = psutil.getloadavg()
        except (OSError, AttributeError):
            load1 = 0.0
        return {
            "cpu_percent": psutil.cpu_percent(interval=None),
            "cpu_freq_mhz": float(freq.current) if freq else 0.0,
            "cpu_core_count": psutil.cpu_count(logical=True) or 0,
            "load_avg_1m": float(load1),
        }

    def _memory(self) -> dict[str, Any]:
        vm = psutil.virtual_memory()
        swap = psutil.swap_memory()
        return {
            "memory_percent": vm.percent,
            "memory_used_mb": round(vm.used / (1024 * 1024), 1),
            "memory_total_mb": round(vm.total / (1024 * 1024), 1),
            "swap_percent": swap.percent,
        }

    def _disk(self, io_state: _IOState, dt: float) -> dict[str, Any]:
        usage = psutil.disk_usage("/")
        io = psutil.disk_io_counters()
        read_rate = write_rate = 0.0
        if io is not None and dt > 0:
            read_rate = max(0.0, (io.read_bytes - io_state.disk_read_bytes) / dt / (1024 * 1024))
            write_rate = max(0.0, (io.write_bytes - io_state.disk_write_bytes) / dt / (1024 * 1024))
        return {
            "disk_percent": usage.percent,
            "disk_used_gb": round(usage.used / (1024**3), 2),
            "disk_total_gb": round(usage.total / (1024**3), 2),
            "disk_read_mb_s": round(read_rate, 3),
            "disk_write_mb_s": round(write_rate, 3),
            "_io_read_bytes": io.read_bytes if io else 0,
            "_io_write_bytes": io.write_bytes if io else 0,
        }

    def _network(self, io_state: _IOState, dt: float) -> dict[str, Any]:
        net = psutil.net_io_counters()
        sent_rate = recv_rate = 0.0
        if net is not None and dt > 0:
            sent_rate = max(0.0, (net.bytes_sent - io_state.net_sent_bytes) / dt / (1024 * 1024))
            recv_rate = max(0.0, (net.bytes_recv - io_state.net_recv_bytes) / dt / (1024 * 1024))
        return {
            "net_sent_mb_s": round(sent_rate, 3),
            "net_recv_mb_s": round(recv_rate, 3),
            "_net_sent_bytes": net.bytes_sent if net else 0,
            "_net_recv_bytes": net.bytes_recv if net else 0,
        }

    def _temperature(self) -> float:
        try:
            temps = psutil.sensors_temperatures()
        except AttributeError:
            temps = {}
        if not temps:
            return 0.0
        readings = [t.current for entries in temps.values() for t in entries if t.current]
        return round(sum(readings) / len(readings), 1) if readings else 0.0

    def _gpu(self) -> dict[str, float]:
        if not _NVIDIA_SMI:
            return {"gpu_percent": 0.0, "gpu_memory_percent": 0.0}
        try:
            out = subprocess.run(
                [_NVIDIA_SMI, "--query-gpu=utilization.gpu,memory.used,memory.total", "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=3,
            )
            line = out.stdout.strip().splitlines()[0]
            util, mem_used, mem_total = [float(x.strip()) for x in line.split(",")]
            mem_pct = (mem_used / mem_total * 100) if mem_total else 0.0
            return {"gpu_percent": util, "gpu_memory_percent": round(mem_pct, 1)}
        except Exception:
            return {"gpu_percent": 0.0, "gpu_memory_percent": 0.0}

    def _battery(self) -> dict[str, Any]:
        try:
            batt = psutil.sensors_battery()
        except AttributeError:
            batt = None
        if batt is None:
            return {"battery_percent": -1.0, "battery_plugged": True}
        return {"battery_percent": float(batt.percent), "battery_plugged": bool(batt.power_plugged)}

    def _uptime(self) -> float:
        return max(0.0, time.time() - psutil.boot_time())

    def _processes(self) -> dict[str, Any]:
        procs = []
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                info = p.info
                procs.append(
                    {
                        "pid": info["pid"],
                        "name": info["name"] or "unknown",
                        "cpu_percent": round(info["cpu_percent"] or 0.0, 1),
                        "memory_percent": round(info["memory_percent"] or 0.0, 2),
                    }
                )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        procs.sort(key=lambda x: x["cpu_percent"], reverse=True)
        return {
            "process_count": len(procs),
            "top_processes": procs[: self.top_n_processes],
        }

    # ---- public API -----------------------------------------------------------

    def collect(self) -> dict[str, Any]:
        now = time.time()
        dt = (now - self._prev_io.timestamp) if self._prev_io else 0.0
        io_state = self._prev_io or _IOState(timestamp=now)

        reading: dict[str, Any] = {}
        reading.update(self._cpu())
        reading.update(self._memory())
        disk = self._disk(io_state, dt)
        reading["_next_io_read_bytes"] = disk.pop("_io_read_bytes")
        reading["_next_io_write_bytes"] = disk.pop("_io_write_bytes")
        reading.update(disk)

        net = self._network(io_state, dt)
        reading["_next_net_sent_bytes"] = net.pop("_net_sent_bytes")
        reading["_next_net_recv_bytes"] = net.pop("_net_recv_bytes")
        reading.update(net)

        reading["temperature_c"] = self._temperature()
        reading.update(self._gpu())
        reading.update(self._battery())
        reading["uptime_seconds"] = self._uptime()
        reading.update(self._processes())

        # roll IO state forward for next delta computation
        self._prev_io = _IOState(
            disk_read_bytes=reading.pop("_next_io_read_bytes"),
            disk_write_bytes=reading.pop("_next_io_write_bytes"),
            net_sent_bytes=reading.pop("_next_net_sent_bytes"),
            net_recv_bytes=reading.pop("_next_net_recv_bytes"),
            timestamp=now,
        )

        return reading
