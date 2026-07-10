"""Derives a stable, privacy-preserving unique ID for this machine.

We hash the machine's MAC address (or a UUID fallback) rather than sending
it in the clear, and cache the result to disk so the ID survives restarts
even if network interfaces change order.
"""
import hashlib
import json
import os
import platform
import uuid

_CACHE_PATH = os.path.join(os.path.dirname(__file__), ".device_identity.json")


def _compute_uid() -> str:
    mac = uuid.getnode()
    raw = f"{mac}-{platform.node()}-{platform.system()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def get_device_uid() -> str:
    if os.path.exists(_CACHE_PATH):
        try:
            with open(_CACHE_PATH) as f:
                data = json.load(f)
                if data.get("device_uid"):
                    return data["device_uid"]
        except (json.JSONDecodeError, OSError):
            pass

    uid = _compute_uid()
    try:
        with open(_CACHE_PATH, "w") as f:
            json.dump({"device_uid": uid}, f)
    except OSError:
        pass
    return uid


def get_os_info() -> str:
    return f"{platform.system()} {platform.release()} ({platform.machine()})"


def get_hostname() -> str:
    return platform.node() or "unknown-host"
