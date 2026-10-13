import os
import time
import json
import sqlite3
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse, urlunparse
from pathlib import Path
import httpx

from packages.tools.schemas import (
    WebSearchResultItem,
    WebSearchResponse,
    SearchEngineType
)
from packages.resilience import get_circuit_breaker
from packages.security.prompt_injection import sanitize_untrusted_text

logger = logging.getLogger(__name__)

SERPAPI_ENDPOINT = "https://serpapi.com/search.json"
SERPAPI_COST_PER_CALL = 0.01  # ~$0.01 / request on typical paid tier


class SearchCache:
    """Persistent SQLite cache for search queries to prevent redundant external API expenditure."""
    def __init__(self, db_path: Optional[str] = None):
        if not db_path:
            project_root = Path(__file__).resolve().parent.parent.parent
            cache_dir = project_root / "artifacts" / "cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(cache_dir / "search_cache.sqlite")

        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS search_cache (
                    cache_key TEXT PRIMARY KEY,
                    engine TEXT NOT NULL,
                    query TEXT NOT NULL,
                    results_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS workspace_search_budget (
                    workspace_id TEXT,
                    period_month TEXT,
                    calls_count INTEGER DEFAULT 0,
                    cost_usd REAL DEFAULT 0.0,
                    PRIMARY KEY (workspace_id, period_month)
                )
            """)
            conn.commit()

    def get(self, cache_key: str) -> Optional[List[Dict[str, Any]]]:
        now = time.time()
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT results_json FROM search_cache WHERE cache_key = ? AND expires_at > ?",
                    (cache_key, now)
                )
                row = cursor.fetchone()
                if row:
                    return json.loads(row[0])
        except Exception as e:
            logger.warning(f"Search cache read error: {e}")
        return None

    def set(self, cache_key: str, engine: str, query: str, results: List[Dict[str, Any]], ttl_seconds: int = 86400) -> None:
        now = time.time()
        expires_at = now + ttl_seconds
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO search_cache (cache_key, engine, query, results_json, created_at, expires_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (cache_key, engine, query, json.dumps(results), now, expires_at)
                )
                conn.commit()
        except Exception as e:
            logger.warning(f"Search cache write error: {e}")

    def increment_budget(self, workspace_id: str, cost: float) -> int:
        period = time.strftime("%Y-%m")
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO workspace_search_budget (workspace_id, period_month, calls_count, cost_usd)
                    VALUES (?, ?, 1, ?)
                    ON CONFLICT(workspace_id, period_month) DO UPDATE SET
                        calls_count = calls_count + 1,
                        cost_usd = cost_usd + ?
                """, (workspace_id, period, cost, cost))
                conn.commit()
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT calls_count FROM workspace_search_budget WHERE workspace_id = ? AND period_month = ?",
                    (workspace_id, period)
                )
                row = cursor.fetchone()
                return row[0] if row else 1
        except Exception as e:
            logger.warning(f"Budget tracking error: {e}")
            return 1


_SEARCH_CACHE = SearchCache()


def canonicalize_url(url: str) -> str:
    """Strips query parameters like utm_*, ref, etc. to normalize URLs for deduplication."""
    try:
        parsed = urlparse(url)
        # Strip trailing slash and lower host
        netloc = parsed.netloc.lower()
        path = parsed.path.rstrip("/")
        # Filter tracking params
        query_parts = []
        if parsed.query:
            for pair in parsed.query.split("&"):
                if pair:
                    k = pair.split("=")[0].lower()
                    if not k.startswith("utm_") and k not in ("ref", "fbclid", "gclid", "mc_cid"):
                        query_parts.append(pair)
        clean_query = "&".join(query_parts)
        return urlunparse((parsed.scheme, netloc, path, parsed.params, clean_query, ""))
    except Exception:
        return url


class WebSearchTool:
    """
    Unified multi-provider web search tool exposing typed Pydantic responses.
    Chain: SerpAPI (primary) -> DuckDuckGo (fallback) -> Clean Empty (No hallucination).
    """

    def __init__(self):
        self.serpapi_cb = get_circuit_breaker("serpapi", failure_threshold=3, recovery_timeout=60.0)
        self.ddg_cb = get_circuit_breaker("duckduckgo", failure_threshold=4, recovery_timeout=45.0)

    def _query_serpapi(
        self,
        query: str,
        engine: str = "google",
        time_period: Optional[str] = None,
        country: str = "fr",
        language: str = "fr",
        max_results: int = 5
    ) -> List[WebSearchResultItem]:
        api_key = os.getenv("SERPAPI_API_KEY", "").strip()
        if not api_key or api_key.startswith("your_"):
            return []

        if not self.serpapi_cb.can_execute():
            logger.warning("SerpAPI circuit breaker is OPEN, skipping to fallback.")
            return []

        # Map engines
        serp_engine = "google"
        if engine == SearchEngineType.GOOGLE_NEWS.value:
            serp_engine = "google_news"
        elif engine == SearchEngineType.GOOGLE_SCHOLAR.value:
            serp_engine = "google_scholar"
        elif engine == SearchEngineType.GOOGLE_JOBS.value:
            serp_engine = "google_jobs"

        params: Dict[str, Any] = {
            "engine": serp_engine,
            "q": query,
            "api_key": api_key,
            "gl": country,
            "hl": language,
            "num": max_results
        }
        if time_period:
            params["tbs"] = time_period

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(SERPAPI_ENDPOINT, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    self.serpapi_cb.record_success()
                    results: List[WebSearchResultItem] = []
                    
                    # Extract from standard organic results or news results
                    raw_items = data.get("organic_results") or data.get("news_results") or []
                    for item in raw_items[:max_results]:
                        link = item.get("link") or item.get("url")
                        if not link:
                            continue
                        canon_url = canonicalize_url(link)
                        snippet = item.get("snippet") or item.get("highlight") or ""
                        results.append(WebSearchResultItem(
                            title=item.get("title", "Sans titre"),
                            url=canon_url,
                            snippet=sanitize_untrusted_text(snippet[:400]),
                            published_date=item.get("date") or item.get("published_date"),
                            source_name=item.get("source") or urlparse(canon_url).netloc,
                            engine=f"serpapi:{serp_engine}",
                            score=0.95,
                            cached=False
                        ))
                    return results
                else:
                    self.serpapi_cb.record_failure(Exception(f"SerpAPI returned HTTP {resp.status_code}"))
        except Exception as e:
            self.serpapi_cb.record_failure(e)
            logger.warning(f"SerpAPI request failed ({e}), falling back to DuckDuckGo")

        return []

    def _query_duckduckgo(
        self,
        query: str,
        region: str = "fr-fr",
        max_results: int = 5
    ) -> List[WebSearchResultItem]:
        if not self.ddg_cb.can_execute():
            logger.warning("DuckDuckGo circuit breaker is OPEN.")
            return []

        try:
            import warnings
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*renamed to.*")
                try:
                    from ddgs import DDGS
                except ImportError:
                    from duckduckgo_search import DDGS

                results: List[WebSearchResultItem] = []
                with DDGS() as ddgs:
                    raw_items = list(ddgs.text(query, region=region, max_results=max_results))
                for item in raw_items:
                    href = item.get("href")
                    if not href:
                        continue
                    canon_url = canonicalize_url(href)
                    body = item.get("body", "")
                    results.append(WebSearchResultItem(
                        title=item.get("title", "Sans titre"),
                        url=canon_url,
                        snippet=sanitize_untrusted_text(body[:400]),
                        published_date=item.get("date"),
                        source_name=urlparse(canon_url).netloc,
                        engine="duckduckgo:ddgs",
                        score=0.85,
                        cached=False
                    ))
            self.ddg_cb.record_success()
            return results
        except Exception as e:
            self.ddg_cb.record_failure(e)
            logger.warning(f"DuckDuckGo search failed: {e}")

        return []

    def search(
        self,
        query: str,
        engine: str = "google",
        time_period: Optional[str] = None,
        country: str = "fr",
        language: str = "fr",
        max_results: int = 5,
        workspace_id: str = "default"
    ) -> WebSearchResponse:
        t0 = time.time()
        cache_key = f"{engine}:{country}:{language}:{query.strip().lower()}"

        # 1. Check persistent cache
        cached_data = _SEARCH_CACHE.get(cache_key)
        if cached_data:
            cached_items = [WebSearchResultItem(**item) for item in cached_data]
            for it in cached_items:
                it.cached = True
            return WebSearchResponse(
                query=query,
                engine_used="cache",
                total_results=len(cached_items),
                results=cached_items[:max_results],
                cost_usd=0.0,
                latency_ms=round((time.time() - t0) * 1000, 2),
                status="SUCCESS"
            )

        # 2. Query SerpAPI (Primary)
        serp_results = self._query_serpapi(
            query=query,
            engine=engine,
            time_period=time_period,
            country=country,
            language=language,
            max_results=max_results
        )

        cost_usd = 0.0
        engine_used = "serpapi"
        final_results = serp_results

        if serp_results:
            cost_usd = SERPAPI_COST_PER_CALL
            _SEARCH_CACHE.increment_budget(workspace_id, cost_usd)
        else:
            # 3. Query DuckDuckGo (Fallback)
            engine_used = "duckduckgo"
            ddg_results = self._query_duckduckgo(
                query=query,
                region=f"{country}-{language}",
                max_results=max_results
            )
            final_results = ddg_results

        # 4. Deduplicate results by canonical URL
        seen_urls = set()
        deduped: List[WebSearchResultItem] = []
        for r in final_results:
            if r.url not in seen_urls:
                seen_urls.add(r.url)
                deduped.append(r)

        latency_ms = round((time.time() - t0) * 1000, 2)

        # 5. Populate cache if results found
        if deduped:
            _SEARCH_CACHE.set(
                cache_key=cache_key,
                engine=engine_used,
                query=query,
                results=[it.model_dump() for it in deduped],
                ttl_seconds=86400  # 24h cache
            )
            return WebSearchResponse(
                query=query,
                engine_used=engine_used,
                total_results=len(deduped),
                results=deduped,
                cost_usd=cost_usd,
                latency_ms=latency_ms,
                status="SUCCESS"
            )

        # Strict safety requirement: Return explicit NO_DATA, NEVER fabricated content
        return WebSearchResponse(
            query=query,
            engine_used=engine_used,
            total_results=0,
            results=[],
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            status="NO_DATA",
            error_message="Aucun résultat trouvé sur les moteurs de recherche configurés."
        )


# Global singleton tool instance
web_search_tool = WebSearchTool()
