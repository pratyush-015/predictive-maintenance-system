"""ORM models.

Design notes (read this before extending):
- `Device` exists from day one even though the current scope monitors a single
  laptop — this is what lets the platform grow to many hosts/IoT devices
  later without a schema rewrite (the project brief explicitly asks for that).
- `Metric.extra` is a JSON "escape hatch" column. New sensor readings (e.g. a
  new GPU vendor, a new IoT sensor type) can be added there without a
  migration; promote a field to a real column only once it's stable and
  queried often.
- Every table carries `created_at` for auditability.
"""
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(16), default="viewer", nullable=False)  # admin | operator | viewer
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Device(Base):
    """A monitored endpoint. Today: 'my laptop'. Tomorrow: a fleet."""

    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_uid: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    hostname: Mapped[str] = mapped_column(String(128), nullable=False)
    os_info: Mapped[str] = mapped_column(String(256), default="")
    device_type: Mapped[str] = mapped_column(String(32), default="laptop")  # laptop | server | iot
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    metrics: Mapped[list["Metric"]] = relationship(back_populates="device", cascade="all, delete-orphan")


class Metric(Base):
    __tablename__ = "metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    # CPU
    cpu_percent: Mapped[float] = mapped_column(Float, default=0.0)
    cpu_freq_mhz: Mapped[float] = mapped_column(Float, default=0.0)
    cpu_core_count: Mapped[int] = mapped_column(Integer, default=0)
    load_avg_1m: Mapped[float] = mapped_column(Float, default=0.0)

    # Memory
    memory_percent: Mapped[float] = mapped_column(Float, default=0.0)
    memory_used_mb: Mapped[float] = mapped_column(Float, default=0.0)
    memory_total_mb: Mapped[float] = mapped_column(Float, default=0.0)
    swap_percent: Mapped[float] = mapped_column(Float, default=0.0)

    # Disk
    disk_percent: Mapped[float] = mapped_column(Float, default=0.0)
    disk_used_gb: Mapped[float] = mapped_column(Float, default=0.0)
    disk_total_gb: Mapped[float] = mapped_column(Float, default=0.0)
    disk_read_mb_s: Mapped[float] = mapped_column(Float, default=0.0)
    disk_write_mb_s: Mapped[float] = mapped_column(Float, default=0.0)

    # Network
    net_sent_mb_s: Mapped[float] = mapped_column(Float, default=0.0)
    net_recv_mb_s: Mapped[float] = mapped_column(Float, default=0.0)

    # Thermal / power
    temperature_c: Mapped[float] = mapped_column(Float, default=0.0)
    gpu_percent: Mapped[float] = mapped_column(Float, default=0.0)
    gpu_memory_percent: Mapped[float] = mapped_column(Float, default=0.0)
    battery_percent: Mapped[float] = mapped_column(Float, default=-1.0)
    battery_plugged: Mapped[bool] = mapped_column(Boolean, default=True)

    # System
    uptime_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    process_count: Mapped[int] = mapped_column(Integer, default=0)
    top_processes: Mapped[dict] = mapped_column(JSON, default=list)

    # Extensibility escape hatch for future sensors/features
    extra: Mapped[dict] = mapped_column(JSON, default=dict)

    device: Mapped["Device"] = relationship(back_populates="metrics")


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True, nullable=False)
    metric_id: Mapped[int] = mapped_column(ForeignKey("metrics.id"), index=True, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    model_name: Mapped[str] = mapped_column(String(64), nullable=False)
    is_anomaly: Mapped[bool] = mapped_column(Boolean, default=False)
    anomaly_score: Mapped[float] = mapped_column(Float, default=0.0)
    predicted_issue: Mapped[str] = mapped_column(String(64), default="normal")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    recommendation: Mapped[str] = mapped_column(Text, default="")
    explanation: Mapped[dict] = mapped_column(JSON, default=dict)  # top contributing features (XAI)


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True, nullable=False)
    metric_id: Mapped[int | None] = mapped_column(ForeignKey("metrics.id"), nullable=True)
    prediction_id: Mapped[int | None] = mapped_column(ForeignKey("predictions.id"), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    severity: Mapped[str] = mapped_column(String(16), default="warning")  # info | warning | critical
    category: Mapped[str] = mapped_column(String(64), default="general")
    source: Mapped[str] = mapped_column(String(16), default="rule")  # rule | ml
    message: Mapped[str] = mapped_column(Text, nullable=False)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Incident(Base):
    """Groups related alerts into a timeline entry for the dashboard."""

    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="")
    severity: Mapped[str] = mapped_column(String(16), default="warning")
    status: Mapped[str] = mapped_column(String(16), default="open")  # open | monitoring | resolved
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    alert_ids: Mapped[list] = mapped_column(JSON, default=list)
