import uuid
from typing import Optional
from fastapi import APIRouter, WebSocket, Query, HTTPException
from app.websocket.voice_handler import handle_voice_websocket
from app.services.transaction_recovery import DraftRecoveryService

router = APIRouter()


@router.websocket("/ws/voice")
async def voice_websocket_endpoint(
    websocket: WebSocket,
    session_id: Optional[str] = Query(default=None),
    shop_id: int = Query(default=1),
):
    if not session_id:
        session_id = str(uuid.uuid4())
    await handle_voice_websocket(websocket, session_id, shop_id)


@router.get("/voice/session/{session_id}/draft")
async def get_session_draft(session_id: str):
    draft = await DraftRecoveryService.get_draft_by_session(session_id)
    if not draft:
        raise HTTPException(status_code=404, detail="No active draft for this session")
    return DraftRecoveryService.resume_draft(draft)


@router.get("/voice/pending")
async def get_pending_shop_draft(shop_id: int = Query(default=1)):
    draft = await DraftRecoveryService.get_pending_draft(shop_id)
    if not draft:
        return {"has_draft": False, "draft": None}
    return {
        "has_draft": True,
        "draft": DraftRecoveryService.resume_draft(draft),
    }
