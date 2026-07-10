from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.models import Device


def get_or_create_device(db: Session, device_uid: str, hostname: str, os_info: str, device_type: str) -> Device:
    device = db.query(Device).filter(Device.device_uid == device_uid).first()
    if device is None:
        device = Device(
            device_uid=device_uid,
            hostname=hostname,
            os_info=os_info,
            device_type=device_type,
        )
        db.add(device)
        db.commit()
        db.refresh(device)
    else:
        device.last_seen = datetime.now(timezone.utc)
        device.hostname = hostname or device.hostname
        device.os_info = os_info or device.os_info
        db.commit()
    return device
