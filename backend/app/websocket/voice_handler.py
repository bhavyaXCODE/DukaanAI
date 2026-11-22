import json
import logging
from typing import Dict, List
from fastapi import WebSocket, WebSocketDisconnect
from app.services.voice_pipeline import VoicePipeline, PipelineProcessor, PipelineContext
from app.services.gnani_stt import GnaniSTTProcessor
from app.services.llm_service import LLMNLUProcessor
from app.services.customer_resolver import CustomerResolverProcessor
from app.services.transaction_validator import TransactionValidatorProcessor
from app.services.transaction_recovery import DraftSaveProcessor, DraftRecoveryService
from app.services.db_writer import DatabaseWriteProcessor
from app.services.gnani_tts import GnaniTTSProcessor
from app.core.config import settings

logger = logging.getLogger(__name__)


class VoiceConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info("WebSocket connected for session: %s", session_id)

    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info("WebSocket disconnected for session: %s", session_id)

    async def send_json(self, session_id: str, data: dict):
        ws = self.active_connections.get(session_id)
        if ws:
            await ws.send_json(data)

    async def send_bytes(self, session_id: str, data: bytes):
        ws = self.active_connections.get(session_id)
        if ws:
            await ws.send_bytes(data)


manager = VoiceConnectionManager()


def build_pipeline(include_stt: bool = True) -> VoicePipeline:
    processors: List[PipelineProcessor] = []
    if include_stt:
        processors.append(GnaniSTTProcessor())
    processors.extend([
        LLMNLUProcessor(),
        CustomerResolverProcessor(),
        TransactionValidatorProcessor(),
        DraftSaveProcessor(),
        DatabaseWriteProcessor(),
        GnaniTTSProcessor(),
    ])
    return VoicePipeline(processors)


async def handle_voice_websocket(websocket: WebSocket, session_id: str, shop_id: int = 1):
    await manager.connect(websocket, session_id)
    audio_buffer = bytearray()
    conversation_history: List[dict] = []

    try:
        # Check for pending draft on connection
        pending_draft = await DraftRecoveryService.get_draft_by_session(session_id)
        


        if pending_draft:
            # Discard any leftover draft from previous sessions to avoid auto‑pop‑up.
            # Users can retrieve drafts explicitly via a separate action.
            await DraftRecoveryService.cancel_draft(session_id)
            pending_draft = None

        while True:
            try:
                message_data = await websocket.receive()
            except WebSocketDisconnect:
                break
            except RuntimeError:
                # Disconnected socket
                break

            # Handle binary audio chunks
            if "bytes" in message_data and message_data["bytes"]:
                audio_buffer.extend(message_data["bytes"])
                continue

            # Handle JSON text messages
            if "text" in message_data and message_data["text"]:
                try:
                    msg = json.loads(message_data["text"])
                except Exception:
                    logger.warning("Failed to parse websocket message: %s", message_data["text"])
                    continue

                msg_type = msg.get("type", "").upper()

                if msg_type == "TRANSCRIPT":
                    # Mock voice mode: browser performs speech recognition and sends transcript directly
                    text = msg.get("text", "").strip()
                    lang = msg.get("language", "kn")
                    if not text:
                        continue

                    import re
                    # Normalize comma-formatted numbers e.g. "15,000" or "1,50,000" -> "15000", "150000"
                    text = re.sub(r'(\d+),\s*(?=\d{3}(?:\D|$))', r'\1', text)
                    text = re.sub(r'(?<=\d),(?=\d)', '', text)

                    conversation_history.append({"role": "user", "text": text})

                    ctx = PipelineContext(
                        session_id=session_id,
                        shop_id=shop_id,
                        transcript=text,
                        language=lang,
                        conversation_history=conversation_history,
                    )

                    pipeline = build_pipeline(include_stt=False)
                    ctx = await pipeline.run(ctx)

                    if ctx.response_text:
                        conversation_history.append({"role": "assistant", "text": ctx.response_text})

                    await manager.send_json(session_id, ctx.to_response_dict())

                    # If audio generated and Gnani TTS returned bytes, stream them
                    if ctx.has_audio and ctx.tts_audio:
                        length_prefix = len(ctx.tts_audio).to_bytes(4, byteorder="big")
                        await manager.send_bytes(session_id, length_prefix + ctx.tts_audio)

                elif msg_type == "STOP_RECORDING":
                    # Real mode: audio stream stopped, transcribe audio buffer
                    raw_audio = bytes(audio_buffer)
                    audio_buffer.clear()
                    lang = msg.get("language", "kn")

                    ctx = PipelineContext(
                        session_id=session_id,
                        shop_id=shop_id,
                        audio_bytes=raw_audio,
                        language=lang,
                        conversation_history=conversation_history,
                    )

                    pipeline = build_pipeline(include_stt=True)
                    ctx = await pipeline.run(ctx)

                    if ctx.transcript:
                        conversation_history.append({"role": "user", "text": ctx.transcript})
                    if ctx.response_text:
                        conversation_history.append({"role": "assistant", "text": ctx.response_text})

                    await manager.send_json(session_id, ctx.to_response_dict())

                    if ctx.has_audio and ctx.tts_audio:
                        length_prefix = len(ctx.tts_audio).to_bytes(4, byteorder="big")
                        await manager.send_bytes(session_id, length_prefix + ctx.tts_audio)

                elif msg_type in ("CONFIRM_DRAFT", "CONFIRM"):
                    c_name = msg.get("customer_name")
                    amt = msg.get("amount")
                    tx_type = msg.get("transaction_type") or msg.get("tx_type") or msg.get("type") or "CREDIT"
                    ctx = PipelineContext(
                        session_id=session_id,
                        shop_id=shop_id,
                        transcript="confirm",
                        language=msg.get("language", "kn"),
                        conversation_history=conversation_history,
                        confirmed_customer_name=c_name,
                    )
                    if c_name and amt:
                        from app.models.voice_session import NLUResult, VoiceIntent
                        ctx.nlu_result = NLUResult(
                            intent=VoiceIntent.CONFIRM,
                            customer_name=c_name,
                            amount=float(amt),
                            transaction_type=tx_type,
                            language_detected=msg.get("language", "kn"),
                            confidence=1.0,
                            raw_utterance=f"confirm {c_name} {amt}",
                        )
                    pipeline = build_pipeline(include_stt=False)
                    ctx = await pipeline.run(ctx)
                    if ctx.response_text:
                        conversation_history.append({"role": "assistant", "text": ctx.response_text})
                    await manager.send_json(session_id, ctx.to_response_dict())

                elif msg_type == "CANCEL_DRAFT":
                    await DraftRecoveryService.cancel_draft(session_id)
                    await manager.send_json(
                        session_id,
                        {
                            "type": "STATE",
                            "state": "DONE",
                            "message": "Draft cancelled successfully.",
                        },
                    )

                elif msg_type == "PING":
                    await manager.send_json(session_id, {"type": "PONG"})

    except WebSocketDisconnect:
        manager.disconnect(session_id)
    except Exception as e:
        logger.exception("Unexpected error in websocket session %s", session_id)
        manager.disconnect(session_id)
