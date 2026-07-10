"""Alert generation.

Two independent sources feed alerts, deliberately kept decoupled:
1. Rule-based thresholds — simple, deterministic, always available even if no
   ML model is loaded yet. This is the safety net.
2. ML-based — created from `Prediction` results when the model flags an
   anomaly with a category and confidence.
"""
from app.core.config import settings
from app.db.models import Alert, Device, Metric, Prediction
from sqlalchemy.orm import Session


def evaluate_rule_based_alerts(db: Session, device: Device, metric: Metric) -> list[Alert]:
    new_alerts: list[Alert] = []

    def add(category: str, severity: str, message: str):
        alert = Alert(
            device_id=device.id,
            metric_id=metric.id,
            severity=severity,
            category=category,
            source="rule",
            message=message,
        )
        db.add(alert)
        new_alerts.append(alert)

    if metric.cpu_percent >= settings.CPU_ALERT_THRESHOLD:
        add("cpu_overload", "critical", f"CPU usage at {metric.cpu_percent:.1f}% (threshold {settings.CPU_ALERT_THRESHOLD}%)")
    if metric.memory_percent >= settings.MEMORY_ALERT_THRESHOLD:
        add("memory_pressure", "critical", f"Memory usage at {metric.memory_percent:.1f}% (threshold {settings.MEMORY_ALERT_THRESHOLD}%)")
    if metric.disk_percent >= settings.DISK_ALERT_THRESHOLD:
        add("disk_degradation", "warning", f"Disk usage at {metric.disk_percent:.1f}% (threshold {settings.DISK_ALERT_THRESHOLD}%)")
    if 0 <= metric.battery_percent <= 10 and not metric.battery_plugged:
        add("battery_low", "warning", f"Battery at {metric.battery_percent:.0f}% and not charging")
    if metric.temperature_c >= 85:
        add("thermal", "critical", f"Temperature at {metric.temperature_c:.1f}\u00b0C")

    if new_alerts:
        db.commit()
        for a in new_alerts:
            db.refresh(a)
    return new_alerts


def create_ml_alert(db: Session, device: Device, metric: Metric, prediction: Prediction) -> Alert | None:
    if not prediction.is_anomaly:
        return None

    severity = "critical" if prediction.confidence >= 0.8 else "warning"
    message = (
        f"ML model '{prediction.model_name}' flagged anomaly: {prediction.predicted_issue} "
        f"(confidence {prediction.confidence:.0%}). {prediction.recommendation}"
    )
    alert = Alert(
        device_id=device.id,
        metric_id=metric.id,
        prediction_id=prediction.id,
        severity=severity,
        category=prediction.predicted_issue,
        source="ml",
        message=message,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert
