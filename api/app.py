import sys
import os
import logging
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, Request, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

# ── SETTINGS ─────────────────────────────────────────────────────
from settings import settings

# ── RATE LIMITING ───────────────────────────────────────────────
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.extension import _rate_limit_exceeded_handler

# ── GATEWAY AGENT ─────────────────────────────────────────────────
from agent.executor import run_chat_turn
from agent.session_store import get_circuit, clear_session

# ── LOGGING ──────────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format=settings.log_format,
)
logger = logging.getLogger("circuitmind")

# ── APP ──────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.app_title,
    description=settings.app_description,
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── RATE LIMITER SETUP ──────────────────────────────────────────
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=settings.rate_limit_redis_url,
)
app.state.limiter = limiter

app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# ── API KEY SECURITY ─────────────────────────────────────────────
def verify_api_key(x_api_key: str = Header(default=None)):
    if not settings.circuitmind_api_key:
        return  # dev mode (open access)

    if x_api_key != settings.circuitmind_api_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key"
        )

# ── CORS ─────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ── MIDDLEWARE ───────────────────────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = round((time.time() - start) * 1000, 1)
    logger.info(f"{request.method} {request.url.path} → {response.status_code} ({duration}ms)")
    return response

# ── GLOBAL ERROR HANDLER ─────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error. Please try again."},
    )

# ── RATE LIMIT SHORTCUT ──────────────────────────────────────────
def rl(limit: str):
    return limiter.limit(limit)

# ── REQUEST MODELS ───────────────────────────────────────────────
class ChatRequest(BaseModel):
    session_id: str
    message: str

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("message cannot be empty")
        if len(v) > 1000:
            raise ValueError("message must be under 1000 characters")
        return v.strip()

    @field_validator("session_id")
    @classmethod
    def session_id_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("session_id cannot be empty")
        return v.strip()


class SessionRequest(BaseModel):
    session_id: str

    @field_validator("session_id")
    @classmethod
    def session_id_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("session_id cannot be empty")
        return v.strip()

# ── HEALTH ───────────────────────────────────────────────────────
@app.get("/", tags=["health"])
def root():
    return {
        "status": "running",
        "message": "CircuitMind API is live!",
        "version": settings.app_version,
    }

@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}

# ── GATEWAY ENDPOINT ───────────────────────────────────────────────
# Replaces the old /generate, /explain, /diagnose, /export, /hint, and
# /generate-and-explain routes. The agent decides which tool(s) to call
# based on the message and the session's existing state (chat history +
# current circuit).

@app.post("/chat", tags=["core"])
@rl(settings.chat_rate_limit)
def chat(
    request: Request,
    req: ChatRequest,
    _: None = Depends(verify_api_key),
):
    logger.info(f"Chat request [{req.session_id}]: '{req.message[:60]}'")

    try:
        reply = run_chat_turn(req.session_id, req.message)
    except Exception as e:
        logger.error(f"Agent invocation failed: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail="Agent failed to process the request.")

    return {
        "reply": reply,
        "circuit": get_circuit(req.session_id),
    }


@app.post("/chat/reset", tags=["core"])
def reset_chat(req: SessionRequest):
    logger.info(f"Resetting session [{req.session_id}]")
    clear_session(req.session_id)
    return {"status": "ok"}
