from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.db.database import get_db
from app.db.models import Alert, Device, Incident, User
from app.schemas.metrics import AlertOut, IncidentOut

router = APIRouter(tags=["alerts"])


@router.get("/alerts", response_model=list[AlertOut])
def list_alerts(
    device_uid: str | None = None,
    unresolved_only: bool = False,
    severity: str | None = None,
    limit: int = Query(default=100, le=2000),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(Alert)
    if device_uid:
        device = db.query(Device).filter(Device.device_uid == device_uid).first()
        if device:
            q = q.filter(Alert.device_id == device.id)
    if unresolved_only:
        q = q.filter(Alert.resolved.is_(False))
    if severity:
        q = q.filter(Alert.severity == severity)
    rows = q.order_by(desc(Alert.timestamp)).limit(limit).all()
    return rows


@router.post("/alerts/{alert_id}/resolve", response_model=AlertOut)
def resolve_alert(alert_id: int, db: Session = Depends(get_db), _: User = Depends(require_role("admin", "operator"))):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.resolved = True
    alert.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(alert)
    return alert


@router.get("/incidents", response_model=list[IncidentOut])
def list_incidents(
    device_uid: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(Incident)
    if device_uid:
        device = db.query(Device).filter(Device.device_uid == device_uid).first()
        if device:
            q = q.filter(Incident.device_id == device.id)
    if status_filter:
        q = q.filter(Incident.status == status_filter)
    rows = q.order_by(desc(Incident.opened_at)).limit(limit).all()
    return rows
