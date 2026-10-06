import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from infra.db.database import init_db, SessionLocal
from infra.db.repository import ContentOpsRepository
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
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB schemas
    init_db()

    # Seed default workspace & initial brand profile for zero-friction start
    db = SessionLocal()
    try:
        repo = ContentOpsRepository(db)
        default_ws = repo.get_workspace("ws_default")
        if not default_ws:
            ws = repo.create_workspace(name="Default Editorial Workspace", timezone="UTC", owner_id="owner_martial")
            # Force the ID to be ws_default for consistent quickstart
            ws.id = "ws_default"
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


app = FastAPI(
    title="Content Operations Harness API",
    description="Governed agentic editorial operating system API built with LangGraph, FastAPI, and PostgreSQL/Supabase.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pathlib import Path

web_dir = Path(__file__).resolve().parent.parent / "web"
if web_dir.exists():
    app.mount("/ui", StaticFiles(directory=str(web_dir), html=True), name="ui")


@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "healthy",
        "service": "ContentOps Harness API",
        "version": "1.0.0",
        "engine": "LangGraph + FastAPI"
    }


@app.get("/", tags=["System"])
def root():
    return RedirectResponse(url="/ui")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("apps.api.main:app", host="0.0.0.0", port=8000, reload=True)
