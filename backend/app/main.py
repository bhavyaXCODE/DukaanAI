import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, Query
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine, Base
import app.models  # Ensure all models are registered in Base.metadata
from app.api import dashboard, customers, transactions, reports, voice, promises, scan
from app.websocket.voice_handler import handle_voice_websocket


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database tables on startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="DukaanAI API",
    description="The Intelligent Voice Khata – Gnani Voice Hackathon PS2 | Team Lumina",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(customers.router, prefix="/api/customers", tags=["Customers"])
app.include_router(transactions.router, prefix="/api/transactions", tags=["Transactions"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(voice.router, prefix="/api", tags=["Voice"])
app.include_router(promises.router, prefix="/api/promises", tags=["Promises"])
app.include_router(scan.router, prefix="/api/scan", tags=["Scan Book"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "DukaanAI", "version": "1.0.0"}


@app.websocket("/ws/voice")
async def websocket_voice(
    websocket: WebSocket,
    session_id: str = Query(default=None),
    shop_id: int = Query(default=1),
):
    if not session_id:
        session_id = str(uuid.uuid4())
    await handle_voice_websocket(websocket, session_id, shop_id)
