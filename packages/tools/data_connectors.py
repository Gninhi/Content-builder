import logging
import defusedxml.ElementTree as ET
import defusedxml.common
from typing import List
import httpx

from packages.tools.schemas import OfficialDataSignalItem, DataConnectorSource
from packages.security.prompt_injection import sanitize_untrusted_text
from packages.tools.browse import fetch_safe_url

logger = logging.getLogger(__name__)


class OfficialDataConnectors:
    """
    Connectors for official and structured data feeds:
    - arXiv (Research papers in AI / CS)
    - GitHub Releases (Frameworks & tooling releases)
    - Hacker News (Community signal & discussions)
    - Hugging Face (Model releases & paper trends)
    - RSS Feeds (Standard technical press & official blogs)
    """

    @classmethod
    def fetch_arxiv_signals(cls, query: str, max_results: int = 5) -> List[OfficialDataSignalItem]:
        url = "http://export.arxiv.org/api/query"
        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending"
        }
        signals: List[OfficialDataSignalItem] = []
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.get(url, params=params)
                if resp.status_code == 200:
                    root = ET.fromstring(resp.text)
                    ns = {"atom": "http://www.w3.org/2005/Atom"}
                    for entry in root.findall("atom:entry", ns):
                        title = entry.find("atom:title", ns)
                        summary = entry.find("atom:summary", ns)
                        published = entry.find("atom:published", ns)
                        id_elem = entry.find("atom:id", ns)
                        
                        raw_title = title.text.strip().replace("\n", " ") if title is not None and title.text else "arXiv Paper"
                        raw_summary = summary.text.strip().replace("\n", " ") if summary is not None and summary.text else ""
                        pub_date = published.text.strip() if published is not None and published.text else ""
                        paper_url = id_elem.text.strip() if id_elem is not None and id_elem.text else ""

                        signals.append(OfficialDataSignalItem(
                            source_type=DataConnectorSource.ARXIV,
                            identifier=paper_url.split("/")[-1] if "/" in paper_url else paper_url,
                            title=raw_title,
                            url=paper_url,
                            summary=sanitize_untrusted_text(raw_summary[:500]),
                            published_date=pub_date,
                            metadata={"category": "ai_research"}
                        ))
        except Exception as e:
            logger.warning(f"arXiv signal fetch failed: {e}")

        return signals

    @classmethod
    def fetch_github_releases(cls, repo: str, max_results: int = 3) -> List[OfficialDataSignalItem]:
        """
        Fetches official releases for a repository (e.g. 'langchain-ai/langgraph' or 'vllm-project/vllm').
        """
        url = f"https://api.github.com/repos/{repo}/releases"
        headers = {"User-Agent": "ContentOps-Harness-Bot/1.0", "Accept": "application/vnd.github.v3+json"}
        signals: List[OfficialDataSignalItem] = []
        try:
            with httpx.Client(timeout=8.0) as client:
                resp = client.get(url, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data[:max_results]:
                        tag = item.get("tag_name", "")
                        name = item.get("name") or tag
                        body = item.get("body", "")
                        html_url = item.get("html_url", f"https://github.com/{repo}/releases/tag/{tag}")
                        pub_date = item.get("published_at", "")

                        signals.append(OfficialDataSignalItem(
                            source_type=DataConnectorSource.GITHUB,
                            identifier=f"{repo}@{tag}",
                            title=f"Release {repo} {tag}: {name}",
                            url=html_url,
                            summary=sanitize_untrusted_text(body[:500]),
                            published_date=pub_date,
                            metadata={"repo": repo, "tag": tag}
                        ))
        except Exception as e:
            logger.warning(f"GitHub releases fetch failed for {repo}: {e}")

        return signals

    @classmethod
    def fetch_hackernews_signals(cls, query: str, max_results: int = 5) -> List[OfficialDataSignalItem]:
        """Queries Algolia Hacker News Search API for trending developer signals."""
        url = "https://hn.algolia.com/api/v1/search_by_date"
        params = {"query": query, "tags": "story", "hitsPerPage": max_results}
        signals: List[OfficialDataSignalItem] = []
        try:
            with httpx.Client(timeout=8.0) as client:
                resp = client.get(url, params=params)
                if resp.status_code == 200:
                    hits = resp.json().get("hits", [])
                    for h in hits:
                        title = h.get("title", "")
                        h_url = h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}"
                        points = h.get("points", 0)
                        comments = h.get("num_comments", 0)
                        created_at = h.get("created_at", "")

                        signals.append(OfficialDataSignalItem(
                            source_type=DataConnectorSource.HACKERNEWS,
                            identifier=str(h.get("objectID")),
                            title=title,
                            url=h_url,
                            summary=f"Discussion Hacker News ({points} points, {comments} commentaires)",
                            published_date=created_at,
                            metadata={"points": points, "comments": comments}
                        ))
        except Exception as e:
            logger.warning(f"Hacker News signal fetch failed: {e}")

        return signals

    @classmethod
    def fetch_huggingface_signals(cls, query: str, max_results: int = 5) -> List[OfficialDataSignalItem]:
        """Queries Hugging Face model hub API for latest model releases."""
        url = "https://huggingface.co/api/models"
        params = {"search": query, "sort": "lastModified", "direction": -1, "limit": max_results}
        signals: List[OfficialDataSignalItem] = []
        try:
            with httpx.Client(timeout=8.0) as client:
                resp = client.get(url, params=params)
                if resp.status_code == 200:
                    models = resp.json()
                    for m in models:
                        m_id = m.get("id") or m.get("modelId", "")
                        hf_url = f"https://huggingface.co/{m_id}"
                        pipeline = m.get("pipeline_tag", "llm")
                        downloads = m.get("downloads", 0)
                        last_mod = m.get("lastModified", "")

                        signals.append(OfficialDataSignalItem(
                            source_type=DataConnectorSource.HUGGINGFACE,
                            identifier=m_id,
                            title=f"HuggingFace Model: {m_id}",
                            url=hf_url,
                            summary=f"Modèle '{m_id}' ({pipeline}, {downloads} téléchargements récents)",
                            published_date=last_mod,
                            metadata={"pipeline": pipeline, "downloads": downloads}
                        ))
        except Exception as e:
            logger.warning(f"Hugging Face signal fetch failed: {e}")

        return signals

    @classmethod
    def fetch_rss_feed(cls, feed_url: str, max_results: int = 5) -> List[OfficialDataSignalItem]:
        """
        Parses standard RSS 2.0 and Atom feeds with strict SSRF validation,
        redirect re-checking, size limit enforcement, and safe defusedxml parsing.
        """
        signals: List[OfficialDataSignalItem] = []
        try:
            resp = fetch_safe_url(feed_url, timeout=8.0, max_redirects=3, max_bytes=1_000_000)
            if resp.status_code == 200:
                root = ET.fromstring(resp.text)
                # Check RSS 2.0 (<channel><item>)
                channel = root.find("channel")
                items = channel.findall("item") if channel is not None else root.findall("item")
                if not items:
                    # Try Atom (<feed><entry>)
                    ns = {"atom": "http://www.w3.org/2005/Atom"}
                    items = root.findall("atom:entry", ns)

                for it in items[:max_results]:
                    title = it.findtext("title") or "Flux RSS Article"
                    link = it.findtext("link") or feed_url
                    desc = it.findtext("description") or it.findtext("summary") or ""
                    pub_date = it.findtext("pubDate") or it.findtext("published") or it.findtext("updated") or ""

                    signals.append(OfficialDataSignalItem(
                        source_type=DataConnectorSource.RSS,
                        identifier=link,
                        title=title.strip(),
                        url=link.strip(),
                        summary=sanitize_untrusted_text(desc[:400].strip()),
                        published_date=pub_date.strip(),
                        metadata={"feed_url": feed_url}
                    ))
        except defusedxml.common.DefusedXmlException as xml_err:
            logger.warning(f"XML security guard (XXE/DTD) blocked malicious feed for {feed_url}: {xml_err}")
            return []
        except (PermissionError, ValueError) as ssrf_err:
            logger.warning(f"SSRF or size guard blocked RSS fetch for {feed_url}: {ssrf_err}")
            raise
        except Exception as e:
            logger.warning(f"RSS feed fetch/parse failed for {feed_url}: {e}")

        return signals
