from typing import Dict, Any
from services.orchestration.state.base import AnalyticsState


def normalize_metrics_node(state: AnalyticsState) -> Dict[str, Any]:
    """
    Normalizes raw post metrics across platforms and time windows.
    """
    raw = state.get("raw_metrics", {})
    impressions = max(1, raw.get("impressions", 0))
    engagements = raw.get("engagements", 0)
    clicks = raw.get("clicks", 0)
    comments = raw.get("comments", 0)
    shares = raw.get("shares", 0)

    engagement_rate = round((engagements / impressions) * 100, 2)
    ctr = round((clicks / impressions) * 100, 2)
    amplification_rate = round((shares / impressions) * 100, 2)

    normalized = {
        "impressions": impressions,
        "engagements": engagements,
        "clicks": clicks,
        "comments": comments,
        "shares": shares,
        "engagement_rate_pct": engagement_rate,
        "click_through_rate_pct": ctr,
        "amplification_rate_pct": amplification_rate,
        "performance_index": round((engagement_rate * 0.6) + (ctr * 0.4), 2)
    }

    return {
        "normalized_metrics": normalized,
        "status": "MEASURED"
    }
