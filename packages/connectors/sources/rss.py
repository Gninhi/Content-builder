from typing import List, Dict, Any
import defusedxml.ElementTree as ET
from packages.connectors.sources.web_extractor import WebExtractorConnector
from packages.tools.browse import validate_target_url_security, fetch_safe_url


class RSSConnector:
    """
    Ingests and normalizes RSS/Atom feeds into verifiable content sources with strict SSRF protection.
    """

    @classmethod
    def parse_feed_items(cls, feed_url: str, raw_items: List[Dict[str, Any]], workspace_id: str = "default") -> List[Dict[str, Any]]:
        if feed_url and feed_url.startswith(("http://", "https://")):
            validate_target_url_security(feed_url)
        processed_items = []
        for item in raw_items:
            title = item.get("title", "")
            description = item.get("description", "") or item.get("summary", "")
            link = item.get("link", feed_url)
            if link and link.startswith(("http://", "https://")):
                validate_target_url_security(link)
            author = item.get("author", "Feed Author")

            full_text = f"{title}\n\n{description}"
            source_payload = WebExtractorConnector.process_source(
                source_type="rss",
                content=full_text,
                url=link,
                author=author,
                workspace_id=workspace_id
            )
            processed_items.append(source_payload)
        return processed_items

    @classmethod
    def fetch_and_parse_feed(cls, feed_url: str, workspace_id: str = "default", max_items: int = 10) -> List[Dict[str, Any]]:
        """Fetches an RSS/Atom XML feed safely via fetch_safe_url and parses its items."""
        validate_target_url_security(feed_url)
        resp = fetch_safe_url(feed_url, timeout=8.0)
        if resp.status_code != 200 or not resp.text:
            return []
        root = ET.fromstring(resp.text)
        raw_items: List[Dict[str, Any]] = []
        # RSS 2.0 items
        for item in root.findall(".//item")[:max_items]:
            raw_items.append({
                "title": (item.findtext("title") or "").strip(),
                "description": (item.findtext("description") or "").strip(),
                "link": (item.findtext("link") or feed_url).strip(),
                "author": (item.findtext("author") or item.findtext("dc:creator") or "Feed Author").strip(),
            })
        # Atom entries fallback
        if not raw_items:
            ns = {"atom": "http://www.w3.org/2005/Atom"}
            for entry in root.findall(".//atom:entry", ns)[:max_items]:
                link_el = entry.find("atom:link", ns)
                href = link_el.attrib.get("href", feed_url) if link_el is not None else feed_url
                raw_items.append({
                    "title": (entry.findtext("atom:title", default="", namespaces=ns) or "").strip(),
                    "description": (
                        entry.findtext("atom:summary", default="", namespaces=ns)
                        or entry.findtext("atom:content", default="", namespaces=ns)
                        or ""
                    ).strip(),
                    "link": href.strip(),
                    "author": "Feed Author",
                })
        return cls.parse_feed_items(feed_url, raw_items, workspace_id=workspace_id)
