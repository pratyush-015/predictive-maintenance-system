from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.database import SessionLocal
from app.db.models import User
from app.services.ws_manager import manager

router = APIRouter(tags=["ws"])


def _authorized(token: str | None) -> bool:
    if not token:
        return False
    try:
        payload = decode_token(token)
    except ValueError:
        return False
    if payload.get("type") != "access":
        return False
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.username == payload.get("sub")).first()
        return bool(user and user.is_active)
    finally:
        db.close()


@router.websocket("/ws/live")
async def ws_live(websocket: WebSocket, token: str | None = Query(default=None)):
    if not _authorized(token):
        await websocket.close(code=4401)
        return

    await manager.connect(websocket)
    try:
        while True:
            # Connection is push-only from server; just keep it alive and drain
            # any client pings/messages without acting on them.
            await websocket.receive_text()
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
