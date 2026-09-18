import sys
import os
import logging
import time
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, Request, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator
from typing import Optional

# ── SETTINGS ─────────────────────────────────────────────────────
from settings import settings

# ── RATE LIMITING ───────────────────────────────────────────────
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.extension import _rate_limit_exceeded_handler

# ── LOCAL MODULES ───────────────────────────────────────────────
from generate.generate import generate_circuit
from explain.explain_module import explain_circuit
from diagnose.diagnose_module import diagnose_circuit
from export.export_module import export_module
from hint.hint_module import generate_hint

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
# storage_uri points at Redis (e.g. Upstash) in production so limits hold
# across serverless instances; falls back to in-memory when unset (local dev).
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
class GenerateRequest(BaseModel):
    prompt: str

    @field_validator("prompt")
    @classmethod
    def prompt_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("prompt cannot be empty")
        if len(v) > 1000:
            raise ValueError("prompt must be under 1000 characters")
        return v.strip()

class CircuitRequest(BaseModel):
    circuit_json: dict

class ExportRequest(BaseModel):
    circuit_json: dict
    export_format: Optional[str] = "spice"

    @field_validator("export_format")
    @classmethod
    def valid_format(cls, v: str) -> str:
        allowed = {"spice", "svg", "gate_json"}
        if v not in allowed:
            raise ValueError(f"export_format must be one of {allowed}")
        return v

class HintRequest(BaseModel):
    problem_title: str = ""
    problem_description: Optional[str] = ""
    inputs: list[str] = []
    outputs: list[str] = []
    truth_table: list[dict] = []
    gates: list[dict] = []
    wires: list[dict] = []
    last_result: Optional[dict] = None

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

# ── CORE ENDPOINTS ───────────────────────────────────────────────

@app.post("/generate", tags=["core"])
@rl(settings.generate_rate_limit)
def generate(
    request: Request,
    req: GenerateRequest,
    _: None = Depends(verify_api_key),
):
    logger.info(f"Generate request: '{req.prompt[:60]}'")

    result = generate_circuit(req.prompt)
    if "error" in result:
        raise HTTPException(status_code=422, detail=result["error"])

    return result


@app.post("/explain", tags=["core"])
@rl(settings.explain_rate_limit)
def explain(
    request: Request,
    req: CircuitRequest,
    _: None = Depends(verify_api_key),
):
    logger.info("Explain request received")
    return explain_circuit(req.circuit_json)


@app.post("/diagnose", tags=["core"])
@rl(settings.diagnose_rate_limit)
def diagnose(
    request: Request,
    req: CircuitRequest,
    _: None = Depends(verify_api_key),
):
    logger.info("Diagnose request received")
    return diagnose_circuit(req.circuit_json)


@app.post("/export", tags=["core"])
@rl(settings.export_rate_limit)
def export(
    request: Request,
    req: ExportRequest,
    _: None = Depends(verify_api_key),
):
    logger.info(f"Export request: format={req.export_format}")

    json_str = json.dumps(req.circuit_json)
    result = export_module(json_str, export_format=req.export_format)

    if result.get("status") == "error":
        raise HTTPException(status_code=422, detail=result["message"])

    return result


@app.post("/hint", tags=["core"])
@rl(settings.hint_rate_limit)
def hint(
    request: Request,
    req: HintRequest,
    _: None = Depends(verify_api_key),
):
    logger.info(f"Hint request: '{req.problem_title[:60]}'")
    return generate_hint(req.model_dump())


@app.post("/generate-and-explain", tags=["core"])
@rl(settings.generate_and_explain_rate_limit)
def generate_and_explain(
    request: Request,
    req: GenerateRequest,
    _: None = Depends(verify_api_key),
):
    logger.info(f"Generate-and-explain request: '{req.prompt[:60]}'")

    circuit = generate_circuit(req.prompt)
    if "error" in circuit:
        raise HTTPException(status_code=422, detail=circuit["error"])

    return {
        "circuit": circuit,
        "explanation": explain_circuit(circuit),
        "diagnosis": diagnose_circuit(circuit),
    }
