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


class GnaniTTSService:
    def __init__(self):
        self.endpoint = settings.GNANI_TTS_ENDPOINT
        self.api_key = settings.GNANI_TTS_API_KEY
        self.mock_voice = settings.MOCK_VOICE

    async def synthesize(self, text: str, language: str = "kn") -> bytes:
        if self.mock_voice or not self.api_key or not text:
            return b""

        headers = {
            "Content-Type": "application/json",
            "X-API-Key-ID": self.api_key,
            "Authorization": f"Bearer {self.api_key}",
        }

        lang_code = LANG_MAP.get(language, "hi-IN")

        payload = {
            "text": text,
            "voice": "Pranav",
            "model": "timbre-v2.5",
            "language": lang_code,
            "speed": 1.0,
        }

        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.post(
                    self.endpoint,
                    headers=headers,
                    json=payload,
                )
                if response.status_code == 200:
                    logger.info("Gnani Timbre TTS synthesized %d audio bytes for '%s'", len(response.content), text[:30])
                    return response.content
                else:
                    logger.warning("Gnani TTS returned status %s: %s", response.status_code, response.text)
                    return b""
        except Exception as e:
            logger.warning("Gnani TTS network call skipped (%s)", e)
            return b""


class GnaniTTSProcessor(PipelineProcessor):
    def __init__(self):
        self.service = GnaniTTSService()

    async def process(self, ctx: PipelineContext) -> PipelineContext:
        if not ctx.response_text:
            return ctx

        audio_bytes = await self.service.synthesize(ctx.response_text, ctx.language)
        if audio_bytes:
            ctx.tts_audio = audio_bytes
            ctx.has_audio = True
        else:
            ctx.tts_audio = None
            ctx.has_audio = False

        return ctx
