import os
from fastapi import Request, Response
from prometheus_client import (
    Counter,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
    REGISTRY
)

# Standard Prometheus metrics definitions
HTTP_REQUESTS_TOTAL = Counter(
    "contentops_http_requests_total",
    "Total count of HTTP requests processed by ContentOps Harness API",
    ["method", "endpoint", "status"]
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "contentops_http_request_duration_seconds",
    "Histogram of HTTP request latencies in seconds",
    ["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

PUBLICATION_JOBS_TOTAL = Counter(
    "contentops_publication_jobs_total",
    "Total publication jobs processed by PublisherWorker",
    ["platform", "status"]
)

LLM_INFERENCES_TOTAL = Counter(
    "contentops_llm_inferences_total",
    "Total LLM inferences executed across providers",
    ["provider", "model"]
)


def get_prometheus_metrics_response(request: Request) -> Response:
    """
    Renders Prometheus metrics.
    If METRICS_AUTH_TOKEN is configured in the environment, validates Authorization header.
    """
    expected_token = os.getenv("METRICS_AUTH_TOKEN")
    if expected_token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header != f"Bearer {expected_token}":
            return Response(content="Unauthorized\n", status_code=401, media_type="text/plain")

    data = generate_latest(REGISTRY)
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)
