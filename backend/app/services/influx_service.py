"""Optional InfluxDB integration.

Postgres (via SQLAlchemy) is the system of record the dashboard reads from —
it's simpler to query relationally for the alerts/incidents/predictions the
UI needs. InfluxDB is offered alongside it, disabled by default, for
deployments that want a dedicated high-resolution time-series store (e.g. for
long-retention raw telemetry or Grafana dashboards outside this app). Toggle
with `INFLUX_ENABLED=true`.
"""
from __future__ import annotations

import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger("aiops.influx")

_client = None
_write_api = None


def _get_write_api():
    global _client, _write_api
    if not settings.INFLUX_ENABLED:
        return None
    if _write_api is None:
        try:
            from influxdb_client import InfluxDBClient
            from influxdb_client.client.write_api import SYNCHRONOUS

            _client = InfluxDBClient(url=settings.INFLUX_URL, token=settings.INFLUX_TOKEN, org=settings.INFLUX_ORG)
            _write_api = _client.write_api(write_options=SYNCHRONOUS)
        except Exception:
            logger.exception("Failed to initialize InfluxDB client — writes will be skipped.")
            return None
    return _write_api


def write_metric_point(device_uid: str, fields: dict) -> None:
    """Best-effort write; never raises — InfluxDB is a secondary sink and
    must not be able to break metric ingestion if it's down."""
    write_api = _get_write_api()
    if write_api is None:
        return
    try:
        from influxdb_client import Point

        numeric_fields = {k: v for k, v in fields.items() if isinstance(v, (int, float)) and not isinstance(v, bool)}
        point = Point("system_metrics").tag("device_uid", device_uid)
        for k, v in numeric_fields.items():
            point = point.field(k, float(v))
        write_api.write(bucket=settings.INFLUX_BUCKET, record=point)
    except Exception:
        logger.exception("InfluxDB write failed (non-fatal, continuing).")
