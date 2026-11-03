import time
import logging
from typing import Dict, Any, Optional, List, Callable, Type, Literal
from pydantic import BaseModel, Field

from packages.security.prompt_injection import sanitize_untrusted_text
from packages.tools.browse import (
    validate_target_url_security,
    fetch_safe_url,
    extract_metadata_and_text,
)
from packages.tools.web_search import WebSearchTool
from packages.tools.data_connectors import OfficialDataConnectors
from packages.connectors.sources.rss import RSSConnector

logger = logging.getLogger(__name__)


class WebSearchToolInput(BaseModel):
    query: str = Field(..., min_length=2, max_length=256)
    limit: int = Field(default=3, ge=1, le=10)
    time_period: Literal["day", "week", "month", "year"] = Field(default="month")


class SafeBrowseToolInput(BaseModel):
    url: str = Field(..., min_length=8, max_length=2048)
    max_chars: int = Field(default=4000, ge=200, le=12000)


class OfficialConnectorToolInput(BaseModel):
    connector: Literal["arxiv", "github", "hackernews", "huggingface"] = Field(...)
    query_or_repo: str = Field(..., min_length=2, max_length=256)
    max_results: int = Field(default=3, ge=1, le=10)


class RSSFetchToolInput(BaseModel):
    feed_url: str = Field(..., min_length=8, max_length=2048)
    max_items: int = Field(default=5, ge=1, le=20)


class ToolPolicy(BaseModel):
    name: str
    description: str
    input_schema: Type[BaseModel]
    timeout_seconds: float = 10.0
    max_calls_per_run: int = 2
    max_output_chars: int = 6000
    allowed_roles: List[str] = Field(default_factory=lambda: ["Owner", "Editor", "ServiceAgent"])
    requires_ssrf_check: bool = False


class ToolExecutionRecord(BaseModel):
    tool_name: str
    workspace_id: str
    caller_role: str
    arguments: Dict[str, Any]
    status: Literal["SUCCESS", "BLOCKED", "FAILED"]
    duration_ms: float
    output_summary: str
    error: Optional[str] = None


class ToolExecutionResult(BaseModel):
    tool_name: str
    status: Literal["SUCCESS", "BLOCKED", "FAILED"]
    data: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0


class AgentToolRegistry:
    """
    Centralized, governed tool registry and execution sandbox for ContentOps agents (Sections 8.3 & 10.1).
    Enforces:
    - Strict Pydantic input validation
    - Workspace scope and RBAC role check
    - Per-run call budget (`max_calls_per_run` and `max_total_calls`)
    - Mandatory SSRF validation on any URL-taking tool
    - Prompt injection sanitization and output truncation on all untrusted external responses
    - Full execution trace logging (`execution_history`)
    """

    def __init__(
        self,
        workspace_id: str,
        caller_role: str = "ServiceAgent",
        max_total_calls: int = 2,
    ):
        if not workspace_id or not str(workspace_id).strip():
            raise ValueError("AgentToolRegistry requires a non-empty workspace_id.")
        self.workspace_id = str(workspace_id).strip()
        self.caller_role = caller_role
        self.max_total_calls = max_total_calls
        self.total_calls = 0
        self.call_counts: Dict[str, int] = {}
        self.execution_history: List[ToolExecutionRecord] = []

        self._policies: Dict[str, ToolPolicy] = {
            "web_search": ToolPolicy(
                name="web_search",
                description="Search recent web sources for missing facts on a specific topic.",
                input_schema=WebSearchToolInput,
                timeout_seconds=10.0,
                max_calls_per_run=2,
                max_output_chars=4000,
                requires_ssrf_check=False,
            ),
            "safe_browse": ToolPolicy(
                name="safe_browse",
                description="Fetch and extract clean documentary text from a public HTTP/HTTPS URL with SSRF protection.",
                input_schema=SafeBrowseToolInput,
                timeout_seconds=8.0,
                max_calls_per_run=2,
                max_output_chars=5000,
                requires_ssrf_check=True,
            ),
            "official_connectors": ToolPolicy(
                name="official_connectors",
                description="Query official structured feeds (arXiv, GitHub releases, HackerNews, HuggingFace).",
                input_schema=OfficialConnectorToolInput,
                timeout_seconds=10.0,
                max_calls_per_run=2,
                max_output_chars=4000,
                requires_ssrf_check=False,
            ),
            "rss_fetch": ToolPolicy(
                name="rss_fetch",
                description="Fetch and parse an external RSS/Atom feed with SSRF and defusedxml protection.",
                input_schema=RSSFetchToolInput,
                timeout_seconds=8.0,
                max_calls_per_run=2,
                max_output_chars=4000,
                requires_ssrf_check=True,
            ),
        }

        self._handlers: Dict[str, Callable[[BaseModel], Any]] = {
            "web_search": self._handle_web_search,
            "safe_browse": self._handle_safe_browse,
            "official_connectors": self._handle_official_connectors,
            "rss_fetch": self._handle_rss_fetch,
        }

    def list_policies(self) -> List[ToolPolicy]:
        return list(self._policies.values())

    def execute(self, tool_name: str, raw_arguments: Dict[str, Any]) -> ToolExecutionResult:
        t0 = time.monotonic()
        policy = self._policies.get(tool_name)
        if not policy:
            err = f"Unknown or unregistered tool: '{tool_name}'"
            self._record(tool_name, raw_arguments, "BLOCKED", 0.0, "", err)
            return ToolExecutionResult(tool_name=tool_name, status="BLOCKED", error=err)

        # 1. Role check
        if self.caller_role not in policy.allowed_roles:
            err = f"Role '{self.caller_role}' is not authorized to invoke tool '{tool_name}'"
            self._record(tool_name, raw_arguments, "BLOCKED", 0.0, "", err)
            return ToolExecutionResult(tool_name=tool_name, status="BLOCKED", error=err)

        # 2. Budget check (total run budget and per-tool budget)
        tool_calls = self.call_counts.get(tool_name, 0)
        if self.total_calls >= self.max_total_calls:
            err = f"Run tool call budget exhausted ({self.total_calls}/{self.max_total_calls})"
            self._record(tool_name, raw_arguments, "BLOCKED", 0.0, "", err)
            return ToolExecutionResult(tool_name=tool_name, status="BLOCKED", error=err)
        if tool_calls >= policy.max_calls_per_run:
            err = f"Tool '{tool_name}' call budget exhausted ({tool_calls}/{policy.max_calls_per_run})"
            self._record(tool_name, raw_arguments, "BLOCKED", 0.0, "", err)
            return ToolExecutionResult(tool_name=tool_name, status="BLOCKED", error=err)

        # 3. Validate input schema
        try:
            validated_args = policy.input_schema.model_validate(raw_arguments)
        except Exception as e:
            err = f"Invalid arguments for tool '{tool_name}': {e}"
            self._record(tool_name, raw_arguments, "BLOCKED", 0.0, "", err)
            return ToolExecutionResult(tool_name=tool_name, status="BLOCKED", error=err)

        # 4. SSRF check on URL arguments if required
        if policy.requires_ssrf_check:
            target_url = getattr(validated_args, "url", None) or getattr(validated_args, "feed_url", None)
            if target_url:
                try:
                    validate_target_url_security(str(target_url))
                except Exception as e:
                    err = f"SSRF Security Policy blocked URL '{target_url}': {e}"
                    self._record(tool_name, raw_arguments, "BLOCKED", 0.0, "", err)
                    return ToolExecutionResult(tool_name=tool_name, status="BLOCKED", error=err)

        # 5. Execute tool handler and sanitize output
        self.total_calls += 1
        self.call_counts[tool_name] = tool_calls + 1
        handler = self._handlers[tool_name]

        try:
            data = handler(validated_args)
            duration_ms = round((time.monotonic() - t0) * 1000.0, 2)
            summary = str(data)[:240]
            self._record(tool_name, validated_args.model_dump(), "SUCCESS", duration_ms, summary, None)
            return ToolExecutionResult(
                tool_name=tool_name,
                status="SUCCESS",
                data=data,
                duration_ms=duration_ms,
            )
        except Exception as e:
            duration_ms = round((time.monotonic() - t0) * 1000.0, 2)
            err = str(e)
            self._record(tool_name, validated_args.model_dump(), "FAILED", duration_ms, "", err)
            return ToolExecutionResult(
                tool_name=tool_name,
                status="FAILED",
                error=err,
                duration_ms=duration_ms,
            )

    def _record(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        status: Literal["SUCCESS", "BLOCKED", "FAILED"],
        duration_ms: float,
        output_summary: str,
        error: Optional[str],
    ) -> None:
        self.execution_history.append(
            ToolExecutionRecord(
                tool_name=tool_name,
                workspace_id=self.workspace_id,
                caller_role=self.caller_role,
                arguments=arguments,
                status=status,
                duration_ms=duration_ms,
                output_summary=output_summary,
                error=error,
            )
        )

    def _handle_web_search(self, args: BaseModel) -> List[Dict[str, Any]]:
        req_args = WebSearchToolInput.model_validate(args.model_dump())
        service = WebSearchTool()
        tp_map = {
            "day": "qdr:d",
            "week": "qdr:w",
            "month": "qdr:m",
            "year": "qdr:y",
        }
        res = service.search(
            query=req_args.query,
            max_results=req_args.limit,
            time_period=tp_map.get(req_args.time_period, "qdr:m"),
            workspace_id=self.workspace_id,
        )
        items: List[Dict[str, Any]] = []
        for item in res.results[: req_args.limit]:
            items.append(
                {
                    "title": sanitize_untrusted_text(str(item.title or ""))[:300],
                    "url": str(item.url),
                    "content": sanitize_untrusted_text(str(item.snippet or ""))[:1200],
                    "source_type": "web_search",
                }
            )
        return items

    def _handle_safe_browse(self, args: BaseModel) -> Dict[str, Any]:
        req_args = SafeBrowseToolInput.model_validate(args.model_dump())
        resp = fetch_safe_url(req_args.url, timeout=8.0, max_redirects=3)
        if resp.status_code != 200:
            raise ValueError(f"HTTP status {resp.status_code} when browsing {req_args.url}")
        meta = extract_metadata_and_text(resp.text, req_args.url)
        clean_text = sanitize_untrusted_text(str(meta.get("clean_text") or ""))[: req_args.max_chars]
        return {
            "title": sanitize_untrusted_text(str(meta.get("title") or req_args.url))[:300],
            "url": str(meta.get("canonical_url") or req_args.url),
            "content": clean_text,
            "published_date": meta.get("published_date"),
            "source_type": "safe_browse",
        }

    def _handle_official_connectors(self, args: BaseModel) -> List[Dict[str, Any]]:
        req_args = OfficialConnectorToolInput.model_validate(args.model_dump())
        if req_args.connector == "arxiv":
            signals = OfficialDataConnectors.fetch_arxiv_signals(req_args.query_or_repo, max_results=req_args.max_results)
        elif req_args.connector == "github":
            signals = OfficialDataConnectors.fetch_github_releases(req_args.query_or_repo, max_results=req_args.max_results)
        elif req_args.connector == "hackernews":
            signals = OfficialDataConnectors.fetch_hackernews_signals(query=req_args.query_or_repo, max_results=req_args.max_results)
        else:
            signals = OfficialDataConnectors.fetch_huggingface_signals(query=req_args.query_or_repo, max_results=req_args.max_results)

        return [
            {
                "title": sanitize_untrusted_text(str(s.title))[:300],
                "url": str(s.url),
                "content": sanitize_untrusted_text(str(s.summary))[:1500],
                "published_date": s.published_date,
                "source_type": req_args.connector,
            }
            for s in signals
        ]

    def _handle_rss_fetch(self, args: BaseModel) -> List[Dict[str, Any]]:
        req_args = RSSFetchToolInput.model_validate(args.model_dump())
        connector = RSSConnector()
        entries = connector.fetch_and_parse_feed(req_args.feed_url, max_items=req_args.max_items)
        return [
            {
                "title": sanitize_untrusted_text(str(e.get("title") or ""))[:300],
                "url": str(e.get("link") or req_args.feed_url),
                "content": sanitize_untrusted_text(str(e.get("summary") or ""))[:1500],
                "published_date": e.get("published"),
                "source_type": "rss_fetch",
            }
            for e in entries[: req_args.max_items]
        ]
