import logging
import httpx
from app.core.config import settings
from app.services.voice_pipeline import PipelineProcessor, PipelineContext

logger = logging.getLogger(__name__)

LANG_MAP = {
    "kn": "kn-IN",
    "kn-IN": "kn-IN",
    "hi": "hi-IN",
    "hi-IN": "hi-IN",
    "en": "en-IN",
    "en-IN": "en-IN",
}


class GnaniSTTService:
    def __init__(self):
        self.endpoint = settings.GNANI_STT_ENDPOINT
        self.api_key = settings.GNANI_STT_API_KEY
        self.mock_voice = settings.MOCK_VOICE

    async def transcribe(self, audio_bytes: bytes, language: str = "kn") -> dict:
        if self.mock_voice or not self.api_key:
            logger.info("Mock STT active. Returning mock transcript.")
            return {
                "transcript": "[mock speech recognized]",
                "confidence": 0.9,
                "language": language,
            }

        headers = {
            "X-API-Key-ID": self.api_key,
            "Authorization": f"Bearer {self.api_key}",
        }

        lang_code = LANG_MAP.get(language, "hi-IN")

        files = {
            "audio_file": ("audio.wav", audio_bytes, "audio/wav")
        }
        data = {
            "model": "prisma-v3.0",
            "language_code": lang_code,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.endpoint,
                    headers=headers,
                    files=files,
                    data=data,
                )
                if response.status_code == 200:
                    res_json = response.json()
                    transcript = (
                        res_json.get("transcript")
                        or res_json.get("text")
                        or res_json.get("asr_output", "")
                    )
                    confidence = float(res_json.get("confidence", 0.95))
                    detected_lang = res_json.get("language_code", language)
                    return {
                        "transcript": transcript,
                        "confidence": confidence,
                        "language": detected_lang,
                    }
                else:
                    logger.error("Gnani STT returned status %s: %s", response.status_code, response.text)
                    return {
                        "transcript": "",
                        "confidence": 0.0,
                        "language": language,
                        "error": f"Gnani STT failed: {response.text}",
                    }
        except Exception as e:
            logger.warning("Error calling Gnani STT (%s)", e)
            return {
                "transcript": "",
                "confidence": 0.0,
                "language": language,
                "error": str(e),
            }


class GnaniSTTProcessor(PipelineProcessor):
    def __init__(self):
        self.service = GnaniSTTService()

    async def process(self, ctx: PipelineContext) -> PipelineContext:
        if ctx.skip_to_tts or ctx.error:
            return ctx

        # If transcript is already provided (e.g. from browser WebSocket in mock mode), keep it
        if ctx.transcript:
            return ctx

        if not ctx.audio_bytes:
            ctx.error = "No audio received"
            return ctx

        result = await self.service.transcribe(ctx.audio_bytes, ctx.language)
        if result.get("error"):
            ctx.error = result["error"]
            return ctx

        ctx.transcript = result.get("transcript", "")
        ctx.confidence = result.get("confidence", 0.9)
        if result.get("language"):
            ctx.language = result.get("language")

        return ctx
