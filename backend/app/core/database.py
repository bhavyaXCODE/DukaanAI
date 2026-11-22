import socket
import logging
from typing import AsyncGenerator
from urllib.parse import urlparse
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.core.config import settings

logger = logging.getLogger(__name__)


def resolve_database_url() -> str:
    url = settings.DATABASE_URL
    if "postgresql" in url:
        try:
            parsed = urlparse(url)
            host = parsed.hostname or "localhost"
            port = parsed.port or 5432
            s = socket.socket()
            s.settimeout(0.5)
            res = s.connect_ex((host, port))
            s.close()
            if res != 0:
                logger.warning(
                    "PostgreSQL not reachable at %s:%s. Falling back to SQLite (sqlite+aiosqlite:///./dukaanai.db) for local execution.",
                    host,
                    port,
                )
                return "sqlite+aiosqlite:///./dukaanai.db"
        except Exception as e:
            logger.warning("Error probing PostgreSQL (%s). Falling back to SQLite.", e)
            return "sqlite+aiosqlite:///./dukaanai.db"
    return url


ACTIVE_DB_URL = resolve_database_url()

engine = create_async_engine(
    ACTIVE_DB_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
