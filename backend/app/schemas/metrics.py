"""Pydantic schemas (API contracts). Kept separate from ORM models on purpose
so the wire format can evolve independently of storage.
"""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class MetricIn(BaseModel):
    """Payload the monitoring agent POSTs every collection cycle."""

    device_uid: str = Field(..., description="Stable unique id for the machine, e.g. MAC-derived hash")
    hostname: str = "unknown-host"
    os_info: str = ""
    device_type: str = "laptop"
    timestamp: Optional[datetime] = None

    cpu_percent: float = 0.0
    cpu_freq_mhz: float = 0.0
    cpu_core_count: int = 0
    load_avg_1m: float = 0.0

    memory_percent: float = 0.0
    memory_used_mb: float = 0.0
    memory_total_mb: float = 0.0
    swap_percent: float = 0.0

    disk_percent: float = 0.0
    disk_used_gb: float = 0.0
    disk_total_gb: float = 0.0
    disk_read_mb_s: float = 0.0
    disk_write_mb_s: float = 0.0

    net_sent_mb_s: float = 0.0
    net_recv_mb_s: float = 0.0

    temperature_c: float = 0.0
    gpu_percent: float = 0.0
    gpu_memory_percent: float = 0.0
    battery_percent: float = -1.0
    battery_plugged: bool = True

    uptime_seconds: float = 0.0
    process_count: int = 0
    top_processes: list[dict[str, Any]] = Field(default_factory=list)

    extra: dict[str, Any] = Field(default_factory=dict)


class MetricBatchIn(BaseModel):
    """Agent can batch multiple readings (e.g. after reconnecting from offline buffer)."""

    readings: list[MetricIn]


class MetricOut(BaseModel):
    """Read-model for a stored metric. Deliberately NOT inheriting from
    MetricIn — device identity (device_uid/hostname/...) lives on `Device`,
    not on every single reading, so it isn't required here."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: int
    timestamp: datetime

    cpu_percent: float
    cpu_freq_mhz: float
    cpu_core_count: int
    load_avg_1m: float

    memory_percent: float
    memory_used_mb: float
    memory_total_mb: float
    swap_percent: float

    disk_percent: float
    disk_used_gb: float
    disk_total_gb: float
    disk_read_mb_s: float
    disk_write_mb_s: float

    net_sent_mb_s: float
    net_recv_mb_s: float

    temperature_c: float
    gpu_percent: float
    gpu_memory_percent: float
    battery_percent: float
    battery_plugged: bool

    uptime_seconds: float
    process_count: int
    top_processes: list[dict[str, Any]] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)


class PredictionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: int
    metric_id: int
    timestamp: datetime
    model_name: str
    is_anomaly: bool
    anomaly_score: float
    predicted_issue: str
    confidence: float
    recommendation: str
    explanation: dict[str, Any] = Field(default_factory=dict)


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: int
    metric_id: Optional[int]
    prediction_id: Optional[int]
    timestamp: datetime
    severity: str
    category: str
    source: str
    message: str
    resolved: bool
    resolved_at: Optional[datetime]


class IncidentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: int
    title: str
    summary: str
    severity: str
    status: str
    opened_at: datetime
    closed_at: Optional[datetime]
    alert_ids: list[int]


class DeviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_uid: str
    hostname: str
    os_info: str
    device_type: str
    is_active: bool
    last_seen: datetime


class ModelComparisonEntry(BaseModel):
    model_name: str
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    roc_auc: float
    inference_time_ms: float


class ModelComparisonOut(BaseModel):
    generated_at: datetime
    models: list[ModelComparisonEntry]
    best_model: str
