import logging
import pytest
from unittest.mock import MagicMock, patch
import httpx

from packages.connectors.social.linkedin import LinkedInSocialPublisher
from packages.connectors.social.models import PublicationStatus
from packages.connectors.search.tavily import TavilySearchConnector
from packages.connectors.social.vault import EncryptedOAuthTokenVault


def test_linkedin_delete_logs_warning_on_exception(caplog):
    """Verifies that an exception during LinkedIn delete emits a structured warning log."""
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.delete.side_effect = httpx.ConnectError("Connection refused by peer")

    publisher = LinkedInSocialPublisher(
        access_token="test-access-token",
        sandbox_mode=False,
        http_client=mock_client
    )

    with caplog.at_level(logging.WARNING):
        res = publisher.delete("urn:li:share:12345")
        assert res is False
        assert any(
            "Error deleting LinkedIn post" in record.message and "Connection refused" in record.message
            for record in caplog.records
        ), f"Expected warning log not found in: {[r.message for r in caplog.records]}"


def test_linkedin_get_status_logs_warning_on_exception(caplog):
    """Verifies that an exception during LinkedIn get_status emits a structured warning log."""
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.side_effect = httpx.ReadTimeout("Read timed out")

    publisher = LinkedInSocialPublisher(
        access_token="test-access-token",
        sandbox_mode=False,
        http_client=mock_client
    )

    with caplog.at_level(logging.WARNING):
        status = publisher.get_status("urn:li:share:12345")
        assert status == PublicationStatus.FAILED
        assert any(
            "Error fetching status for LinkedIn post" in record.message and "Read timed out" in record.message
            for record in caplog.records
        ), f"Expected warning log not found in: {[r.message for r in caplog.records]}"


def test_linkedin_publish_json_parse_failure_logs_warning(caplog):
    """Verifies that a malformed JSON body on 201 response emits a warning log."""
    mock_client = MagicMock(spec=httpx.Client)
    # 201 response without x-restli-id header and invalid JSON body
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 201
    mock_response.headers = {}
    mock_response.text = "{invalid json content"
    mock_response.json.side_effect = ValueError("Expecting value: line 1 column 2")
    mock_client.post.return_value = mock_response

    publisher = LinkedInSocialPublisher(
        access_token="test-access-token",
        author_urn="urn:li:person:author123",
        sandbox_mode=False,
        http_client=mock_client
    )

    with caplog.at_level(logging.WARNING):
        res = publisher.publish("This is a valid test publication exceeding minimum 10 chars.")
        assert res.status == PublicationStatus.PUBLISHED
        assert any(
            "Failed to parse JSON body" in record.message
            for record in caplog.records
        ), f"Expected warning log not found in: {[r.message for r in caplog.records]}"


def test_tavily_search_failure_logs_warning_and_falls_back(caplog):
    """Verifies that Tavily search failure emits a warning log rather than silently passing."""
    connector = TavilySearchConnector(api_key="tvly-mock-valid-key-format-12345")

    with patch("packages.connectors.search.tavily.TavilyClient", create=True) as mock_tavily_cls:
        # Simulate Tavily client import & call failure
        mock_instance = MagicMock()
        mock_instance.search.side_effect = RuntimeError("API rate limit exceeded")
        mock_tavily_cls.return_value = mock_instance

        # We need TavilyClient to be importable in tavily.py
        with patch.dict("sys.modules", {"tavily": MagicMock(TavilyClient=mock_tavily_cls)}):
            with caplog.at_level(logging.WARNING):
                results = connector.search("agentic governance")
                assert len(results) > 0  # Fallback results returned
                assert results[0]["provenance"]["engine"] == "sandbox_feed"
                assert any(
                    "Tavily search API failed" in record.message or "Tavily live search failed" in record.message
                    for record in caplog.records
                ), f"Expected warning log not found in: {[r.message for r in caplog.records]}"


def test_vault_db_error_logs_warning(caplog):
    """Verifies that database lookup failure in EncryptedOAuthTokenVault emits a warning log."""
    mock_session_factory = MagicMock()
    mock_session = MagicMock()
    mock_session.query.side_effect = RuntimeError("DB connection dropped")
    mock_session_factory.return_value = mock_session

    vault = EncryptedOAuthTokenVault(session_factory=mock_session_factory)

    with caplog.at_level(logging.WARNING):
        res = vault.get_token(workspace_id="ws-123", provider="linkedin", account_id="acc-456")
        assert res is None
        assert any(
            "social account" in record.message.lower() and "failed" in record.message.lower()
            for record in caplog.records
        ), f"Expected warning log not found in: {[r.message for r in caplog.records]}"
