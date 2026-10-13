from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SearchEngineType(str, Enum):
    GOOGLE = "google"
    GOOGLE_NEWS = "google_news"
    GOOGLE_TRENDS = "google_trends"
    GOOGLE_SCHOLAR = "google_scholar"
    GOOGLE_JOBS = "google_jobs"
    DUCKDUCKGO = "duckduckgo"


class WebSearchResultItem(BaseModel):
    title: str = Field(description="Titre de la source")
    url: str = Field(description="URL canonique de la source")
    snippet: str = Field(description="Extrait textuel concis")
    published_date: Optional[str] = Field(default=None, description="Date de publication détectée (ISO ou texte)")
    source_name: str = Field(default="Web", description="Nom du média, éditeur ou plateforme")
    engine: str = Field(description="Moteur ayant fourni le résultat (serpapi, ddgs, etc.)")
    score: float = Field(default=0.8, description="Score de pertinence initial 0.0 - 1.0")
    cached: bool = Field(default=False, description="Indique si le résultat provient du cache local")

    @property
    def canonical_url(self) -> str:
        return self.url

    @property
    def domain(self) -> str:
        return self.source_name


class WebSearchResponse(BaseModel):
    query: str
    engine_used: str
    total_results: int
    results: List[WebSearchResultItem] = Field(default_factory=list)
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    status: str = "SUCCESS"  # SUCCESS, NO_DATA, RATE_LIMITED, ERROR
    error_message: Optional[str] = None

    @property
    def items(self) -> List[WebSearchResultItem]:
        return self.results


class BrowseRequest(BaseModel):
    url: str = Field(description="URL absolue à explorer")
    mode: str = Field(default="main_content", description="Mode d'extraction: main_content, metadata_only, text")
    timeout_seconds: float = Field(default=15.0, description="Délai maximum d'exécution")
    workspace_id: str = Field(default="default", description="Identifiant du workspace pour traçabilité")


class BrowseResponse(BaseModel):
    url: str
    canonical_url: str
    title: str
    content: str = Field(description="Contenu textuel principal extrait et épuré")
    published_date: Optional[str] = None
    author: Optional[str] = None
    status: str  # SUCCESS, SSRF_BLOCKED, FORBIDDEN_DOMAIN, ROBOTS_DISALLOWED, FAILED
    error_message: Optional[str] = None
    latency_ms: float = 0.0


class DataConnectorSource(str, Enum):
    ARXIV = "arxiv"
    GITHUB = "github"
    HACKERNEWS = "hackernews"
    HUGGINGFACE = "huggingface"
    RSS = "rss"


class OfficialDataSignalItem(BaseModel):
    source_type: DataConnectorSource
    identifier: str  # e.g. arxiv_id, repo/tag, hn_item_id
    title: str
    url: str
    summary: str
    published_date: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
