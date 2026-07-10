#!/usr/bin/env python3
"""AIOps Monitoring Agent.

Collects system telemetry every `AIOPS_COLLECT_INTERVAL` seconds (default 5s)
and posts it to the backend. If the backend is unreachable, readings are
buffered locally (SQLite) and flushed automatically once connectivity
returns — no data is lost during a network blip or backend restart.

Run:
    python main.py

Configure via environment variables (see config.py) or a `.env` file in this
directory, e.g.:
    AIOPS_BACKEND_URL=http://localhost:8000
    AIOPS_AGENT_API_KEY=dev-agent-key-change-me
"""
from __future__ import annotations

import logging
import signal
import sys
import time

import requests

from buffer import LocalBuffer
from collector import MetricsCollector
from config import config
from device_identity import get_device_uid, get_hostname, get_os_info

logging.basicConfig(
    level=getattr(logging, config.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("aiops.agent")

_shutdown = False


def _handle_signal(signum, frame):
    global _shutdown
    logger.info("Received signal %s, shutting down gracefully...", signum)
    _shutdown = True


signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)


class Agent:
    def __init__(self) -> None:
        self.device_uid = get_device_uid()
        self.hostname = get_hostname()
        self.os_info = get_os_info()
        self.collector = MetricsCollector(top_n_processes=config.top_n_processes)
        self.buffer = LocalBuffer(config.buffer_db_path)
        self.session = requests.Session()
        self.session.headers.update({"X-Agent-Key": config.api_key, "Content-Type": "application/json"})
        logger.info("Agent starting for device_uid=%s hostname=%s os=%s", self.device_uid, self.hostname, self.os_info)

    def _envelope(self, reading: dict) -> dict:
        payload = dict(reading)
        payload.update(
            {
                "device_uid": self.device_uid,
                "hostname": self.hostname,
                "os_info": self.os_info,
                "device_type": config.device_type,
            }
        )
        return payload

    def _post_single(self, payload: dict) -> bool:
        try:
            resp = self.session.post(config.ingest_url, json=payload, timeout=config.request_timeout_seconds)
            if resp.status_code in (200, 201):
                return True
            logger.warning("Backend rejected reading (status %s): %s", resp.status_code, resp.text[:200])
            return False
        except requests.RequestException as exc:
            logger.debug("Network error posting reading: %s", exc)
            return False

    def _flush_buffer(self) -> None:
        pending = self.buffer.count()
        if pending == 0:
            return
        logger.info("Attempting to flush %d buffered reading(s)...", pending)
        batch = self.buffer.peek_batch(config.max_batch_size)
        if not batch:
            return
        ids = [i for i, _ in batch]
        readings = [r for _, r in batch]
        try:
            resp = self.session.post(
                config.batch_ingest_url, json={"readings": readings}, timeout=config.request_timeout_seconds * 2
            )
            if resp.status_code in (200, 201):
                self.buffer.remove(ids)
                logger.info("Flushed %d buffered reading(s). %d remaining.", len(ids), self.buffer.count())
            else:
                logger.warning("Batch flush rejected (status %s): %s", resp.status_code, resp.text[:200])
        except requests.RequestException as exc:
            logger.debug("Batch flush failed, will retry later: %s", exc)

    def run_forever(self) -> None:
        last_flush = 0.0
        while not _shutdown:
            cycle_start = time.time()
            try:
                reading = self.collector.collect()
                payload = self._envelope(reading)

                sent = self._post_single(payload)
                if not sent:
                    self.buffer.add(payload)
                    logger.info("Backend unreachable — buffered reading locally (%d pending).", self.buffer.count())
                else:
                    logger.debug(
                        "Sent reading: cpu=%.1f%% mem=%.1f%% disk=%.1f%% temp=%.1f\u00b0C",
                        reading.get("cpu_percent", 0),
                        reading.get("memory_percent", 0),
                        reading.get("disk_percent", 0),
                        reading.get("temperature_c", 0),
                    )
            except Exception:
                logger.exception("Unexpected error during collection cycle — continuing.")

            if time.time() - last_flush >= config.flush_interval_seconds:
                self._flush_buffer()
                last_flush = time.time()

            elapsed = time.time() - cycle_start
            sleep_for = max(0.0, config.collect_interval_seconds - elapsed)
            time.sleep(sleep_for)

        logger.info("Agent stopped.")


def main() -> None:
    logger.info("=" * 60)
    logger.info("AIOps Monitoring Agent")
    logger.info("Backend: %s", config.backend_url)
    logger.info("Collection interval: %ss", config.collect_interval_seconds)
    logger.info("=" * 60)
    agent = Agent()
    agent.run_forever()


if __name__ == "__main__":
    main()
