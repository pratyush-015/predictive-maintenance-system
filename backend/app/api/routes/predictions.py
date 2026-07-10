from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.db.database import get_db
from app.db.models import Device, Prediction, User
from app.ml_runtime.model_loader import registry
from app.schemas.metrics import ModelComparisonEntry, ModelComparisonOut, PredictionOut

router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.get("", response_model=list[PredictionOut])
def list_predictions(
    device_uid: str | None = None,
    anomalies_only: bool = False,
    limit: int = Query(default=100, le=2000),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(Prediction)
    if device_uid:
        device = db.query(Device).filter(Device.device_uid == device_uid).first()
        if device:
            q = q.filter(Prediction.device_id == device.id)
    if anomalies_only:
        q = q.filter(Prediction.is_anomaly.is_(True))
    rows = q.order_by(desc(Prediction.timestamp)).limit(limit).all()
    return list(reversed(rows))


@router.get("/model-comparison", response_model=ModelComparisonOut)
def model_comparison(_: User = Depends(get_current_user)):
    registry.ensure_loaded()
    comp = registry.comparison
    entries = [ModelComparisonEntry(**m) for m in comp.get("models", [])]
    return ModelComparisonOut(
        generated_at=comp.get("generated_at", datetime.now(timezone.utc).isoformat()),
        models=entries,
        best_model=comp.get("best_model", "n/a"),
    )


@router.post("/reload-models")
def reload_models(_: User = Depends(require_role("admin", "operator"))):
    registry.reload()
    return {"status": "reloaded", "models_loaded": list(registry.models.keys())}
