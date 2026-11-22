from pydantic_settings import BaseSettings
from typing import List, Union
from pydantic import field_validator
import json


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://dukaanai:dukaanai@localhost:5432/dukaanai"
    GNANI_STT_API_KEY: str = ""
    GNANI_STT_ENDPOINT: str = "https://api.gnani.ai/prisma/v3/stt"
    GNANI_TTS_API_KEY: str = ""
    GNANI_TTS_ENDPOINT: str = "https://api.gnani.ai/timbre/v3/tts"
    GEMINI_API_KEY: str = ""
    MOCK_VOICE: bool = True
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    SECRET_KEY: str = "dukaanai-dev-secret"
    DRAFT_TTL_HOURS: int = 24
    SHOP_ID: int = 1

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                return [i.strip() for i in v.split(",") if i.strip()]
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
