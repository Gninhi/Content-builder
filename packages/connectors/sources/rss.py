from typing import List, Dict, Any
from packages.connectors.sources.web_extractor import WebExtractorConnector


class RSSConnector:
    """
    Ingests and normalizes RSS feeds into verifiable content sources.
    """

    @classmethod
    def parse_feed_items(cls, feed_url: str, raw_items: List[Dict[str, Any]], workspace_id: str = "default") -> List[Dict[str, Any]]:
        processed_items = []
        for item in raw_items:
            title = item.get("title", "")
            description = item.get("description", "") or item.get("summary", "")
            link = item.get("link", feed_url)
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
