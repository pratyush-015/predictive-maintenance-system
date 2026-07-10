from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.core.config import settings
from app.db.database import get_db
from app.db.models import Device, Metric, Prediction
from app.ml_runtime.features import build_feature_vector
from app.ml_runtime import predictor
from app.schemas.metrics import MetricBatchIn, MetricIn, MetricOut, PredictionOut
from app.services.alert_service import create_ml_alert, evaluate_rule_based_alerts
from app.services.device_service import get_or_create_device
from app.services.influx_service import write_metric_point
from app.services.ws_manager import manager

router = APIRouter(prefix="/metrics", tags=["metrics"])


def verify_agent_key(x_agent_key: str | None = Header(default=None)) -> None:
    """Lightweight shared-secret auth for the monitoring agent (separate from
    user JWT auth — agents are machines, not interactive users)."""
    if x_agent_key != settings.AGENT_API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing agent API key")


async def _ingest_one(db: Session, payload: MetricIn) -> tuple[Metric, list, Prediction | None]:
    device = get_or_create_device(db, payload.device_uid, payload.hostname, payload.os_info, payload.device_type)

    data = payload.model_dump(exclude={"device_uid", "hostname", "os_info", "device_type", "timestamp"})
    metric = Metric(device_id=device.id, timestamp=payload.timestamp or datetime.now(timezone.utc), **data)
    db.add(metric)
    db.commit()
    db.refresh(metric)

    write_metric_point(payload.device_uid, data)

    alerts = evaluate_rule_based_alerts(db, device, metric)

    prediction_obj = None
    try:
        features = build_feature_vector(db, device.id, metric)
        result = predictor.predict(features)
        prediction_obj = Prediction(device_id=device.id, metric_id=metric.id, **result)
        db.add(prediction_obj)
        db.commit()
        db.refresh(prediction_obj)
        ml_alert = create_ml_alert(db, device, metric, prediction_obj)
        if ml_alert:
            alerts.append(ml_alert)
    except Exception:
        # Prediction failures must never break ingestion — monitoring keeps flowing.
        import logging

        logging.getLogger("aiops").exception("Prediction failed for metric %s", metric.id)

    return metric, alerts, prediction_obj


@router.post("", status_code=status.HTTP_201_CREATED)
async def ingest_metric(payload: MetricIn, _: None = Depends(verify_agent_key), db: Session = Depends(get_db)):
    metric, alerts, prediction = await _ingest_one(db, payload)
    await manager.broadcast(
        {
            "type": "metric",
            "metric": MetricOut.model_validate(metric).model_dump(mode="json"),
            "prediction": PredictionOut.model_validate(prediction).model_dump(mode="json") if prediction else None,
            "alerts": [a.id for a in alerts],
        }
    )
    if alerts:
        await manager.broadcast({"type": "alerts", "count": len(alerts)})
    return {"status": "ok", "metric_id": metric.id, "alerts_created": len(alerts)}


@router.post("/batch", status_code=status.HTTP_201_CREATED)
async def ingest_metric_batch(payload: MetricBatchIn, _: None = Depends(verify_agent_key), db: Session = Depends(get_db)):
    """Used by the agent to flush its offline local buffer once connectivity returns."""
    ids = []
    for reading in payload.readings:
        metric, _alerts, _pred = await _ingest_one(db, reading)
        ids.append(metric.id)
    if ids:
        await manager.broadcast({"type": "batch_synced", "count": len(ids)})
    return {"status": "ok", "ingested": len(ids)}


@router.get("/latest", response_model=MetricOut | None)
def latest_metric(device_uid: str | None = None, db: Session = Depends(get_db), _: object = Depends(get_current_user)):
    q = db.query(Metric)
    if device_uid:
        device = db.query(Device).filter(Device.device_uid == device_uid).first()
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        q = q.filter(Metric.device_id == device.id)
    metric = q.order_by(desc(Metric.timestamp)).first()
    return metric


@router.get("/history", response_model=list[MetricOut])
def metric_history(
    device_uid: str | None = None,
    limit: int = Query(default=200, le=5000),
    db: Session = Depends(get_db),
    _: object = Depends(get_current_user),
):
    q = db.query(Metric)
    if device_uid:
        device = db.query(Device).filter(Device.device_uid == device_uid).first()
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        q = q.filter(Metric.device_id == device.id)
    rows = q.order_by(desc(Metric.timestamp)).limit(limit).all()
    return list(reversed(rows))
