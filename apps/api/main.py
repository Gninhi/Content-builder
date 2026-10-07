import os
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from dotenv import load_dotenv, find_dotenv

# Prioritize values from .env file unconditionally over inherited shell values
load_dotenv(find_dotenv(usecwd=True), override=True)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from infra.db.database import init_db, SessionLocal
from infra.db.repository import ContentOpsRepository
from packages.security.limiter import limiter
from packages.observability.correlation import set_correlation_id
from apps.api.routers import (
    workspaces,
    sources,
    ideas,
    briefs,
    content,
    publications,
    calendar,
    analytics,
    strategy,
    auth,
    oauth,
)

logger = logging.getLogger("apps.api.main")


# Max request body size: default 1 MB
MAX_REQUEST_BODY_SIZE = int(os.getenv("MAX_REQUEST_BODY_SIZE_BYTES", str(1024 * 1024)))


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Enforce fail-closed security configuration in production
    from packages.security.auth import validate_jwt_configuration
    validate_jwt_configuration()

    # Initialize DB schemas
    init_db()

    # Seed default workspace & initial brand profile for zero-friction start
    # and reconcile any orphan PUBLISHING jobs left over from unexpected process stops
    db = SessionLocal()
    try:
        from infra.db.models import PublicationJobModel, ContentVariantModel
        from packages.domain.state_machine import ContentStatus
        orphan_jobs = (
            db.query(PublicationJobModel)
            .filter(PublicationJobModel.status == ContentStatus.PUBLISHING.value)
            .all()
        )
        for job in orphan_jobs:
            logger.warning(
                f"Startup reconciliation: publication job '{job.id}' was in PUBLISHING state. "
                "Transitioning to PUBLISH_UNKNOWN for safe at-most-once reconciliation."
            )
            job.status = ContentStatus.PUBLISH_UNKNOWN.value  # type: ignore[assignment]
            variant = db.query(ContentVariantModel).filter(ContentVariantModel.id == job.variant_id).first()
            if variant:
                variant.status = ContentStatus.PUBLISH_UNKNOWN.value  # type: ignore[assignment]
        if orphan_jobs:
            db.commit()

        repo = ContentOpsRepository(db)
        default_ws = repo.get_workspace("ws_default")
        if not default_ws:
            ws = repo.create_workspace(name="Default Editorial Workspace", timezone="UTC", owner_id="owner_martial")
            # Force the ID to be ws_default for consistent quickstart
            ws.id = "ws_default"  # type: ignore[assignment]
            db.commit()

            repo.create_or_version_brand_profile(
                workspace_id="ws_default",
                audience=["Tech Leads", "AI Engineers", "CTOs", "Founders"],
                voice="Expert, pragmatique, direct, orienté retour d'expérience et architecture sans jargon creux.",
                pillars=["IA générative & LLMs", "Systèmes multi-agents & LangGraph", "Automatisation d'entreprise"],
                prohibited_topics=["Spéculation crypto", "Rumeurs non vérifiées", "Dénigrement concurrent direct"],
                cta_policy={
                    "allowed_ctas": ["Partagez votre avis en commentaire", "Visiter le dépôt GitHub", "S'inscrire à la veille"],
                    "max_per_post": 1
                }
            )
            # Add an initial high-quality source
            repo.add_source(
                workspace_id="ws_default",
                source_type="url",
                canonical_url="https://arxiv.org/abs/2402.01234",
                raw_content_ref="storage/sources/initial_benchmark.txt",
                extracted_facts=[
                    {"fact_id": "fact_1", "claim": "Les architectures agentiques déterministes réduisent de 73% le taux d'erreur par rapport aux chaînes libres.", "confidence": 0.95},
                    {"fact_id": "fact_2", "claim": "L'intervention humaine asynchrone (HITL) permet d'atteindre 99.4% de conformité de marque.", "confidence": 0.98}
                ],
                provenance={"source": "Benchmark Systèmes Agentiques 2026", "author": "Research Lab"}
            )
    finally:
        db.close()

    yield

    # Graceful shutdown: flush pending observability traces to Langfuse
    from packages.observability.tracing import ObservabilityTracer
    ObservabilityTracer.flush()



app = FastAPI(
    title="Content Operations Harness API",
    description="Governed agentic editorial operating system API built with LangGraph, FastAPI, and PostgreSQL/Supabase.",
    version="1.0.0",
    lifespan=lifespan
)

# Attach rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]
app.add_middleware(SlowAPIMiddleware)

# Restrictive CORS configuration
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:8000,http://127.0.0.1:3000,http://127.0.0.1:8000"
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)
@app.middleware("http")
async def security_and_size_middleware(request: Request, call_next):
    # Extract or generate correlation ID
    incoming_cid = request.headers.get("x-correlation-id") or request.headers.get("x-trace-id")
    corr_id = set_correlation_id(incoming_cid)

    # Enforce request payload size limit
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_REQUEST_BODY_SIZE:
                return JSONResponse(
                    status_code=413,
                    content={
                        "error": "payload_too_large",
                        "detail": f"La taille de la requête ({int(content_length)} octets) dépasse la limite autorisée ({MAX_REQUEST_BODY_SIZE} octets)."
                    },
                    headers={"X-Correlation-ID": corr_id}
                )
        except ValueError:
            pass

    response = await call_next(request)

    # Invert/inject robust security headers and correlation ID
    response.headers["X-Correlation-ID"] = corr_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none';"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "http_error", "detail": exc.detail},
        headers=getattr(exc, "headers", None)
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(f"Internal unhandled error during {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "detail": "Une erreur interne est survenue. Veuillez contacter le support."
        }
    )


# Include all sub-routers
app.include_router(workspaces.router)
app.include_router(sources.router)
app.include_router(ideas.router)
app.include_router(briefs.router)
app.include_router(content.router)
app.include_router(publications.router)
app.include_router(calendar.router)
app.include_router(analytics.router)
app.include_router(strategy.router)
app.include_router(auth.router)
app.include_router(oauth.router)

web_dir = Path(__file__).resolve().parent.parent / "web"
dist_dir = web_dir / "dist"
target_static_dir = dist_dir if dist_dir.exists() else web_dir
if target_static_dir.exists():
    app.mount("/ui", StaticFiles(directory=str(target_static_dir), html=True), name="ui")


@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "healthy",
        "service": "ContentOps Harness API",
        "version": "1.0.0",
        "engine": "LangGraph + FastAPI"
    }


@app.get("/ready", tags=["System"])
def readiness_check():
    """
    Readiness probe checking database, LangGraph checkpointer, and LLM configuration.
    Returns HTTP 200 if dependencies are ready, HTTP 503 if critical dependencies are down.
    """
    checks = {}
    is_ready = True

    # 1. Database Connectivity
    try:
        from infra.db.database import SessionLocal
        from sqlalchemy import text
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            checks["database"] = "ok"
        finally:
            db.close()
    except Exception as e:
        checks["database"] = f"error: {str(e)}"
        is_ready = False

    # 2. LangGraph Checkpointer
    try:
        from services.orchestration.checkpointer import get_checkpointer
        cp = get_checkpointer()
        checks["checkpointer"] = "ok" if cp is not None else "unavailable"
        if cp is None:
            is_ready = False
    except Exception as e:
        checks["checkpointer"] = f"error: {str(e)}"
        is_ready = False

    # 3. Google Gemini API Key
    from services.orchestration.llm import is_gemini_available
    has_llm = is_gemini_available()
    checks["llm_key"] = "configured" if has_llm else "missing_or_placeholder"

    status_code = 200 if is_ready else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if is_ready else "not_ready",
            "checks": checks,
            "version": "1.0.0"
        }
    )


@app.get("/", tags=["System"])
def root():
    return RedirectResponse(url="/ui")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("apps.api.main:app", host="0.0.0.0", port=8000, reload=True)
