import pytest
from unittest.mock import patch, MagicMock

from packages.tools.browse import validate_target_url_security, fetch_safe_url
from packages.tools.data_connectors import OfficialDataConnectors


def test_ssrf_rejects_non_http_protocols():
    """Verify non-http/https protocols (file://, ftp://, gopher://) are blocked."""
    with pytest.raises(PermissionError, match="Protocole non autorisé"):
        validate_target_url_security("file:///etc/passwd")

    with pytest.raises(PermissionError, match="Protocole non autorisé"):
        validate_target_url_security("gopher://127.0.0.1:6379/")


def test_ssrf_rejects_embedded_credentials():
    """Verify URLs with embedded username/password are blocked."""
    with pytest.raises(PermissionError, match="Identifiants"):
        validate_target_url_security("http://admin:secret@example.com/feed.xml")


def test_ssrf_blocks_localhost_and_loopback():
    """Verify localhost, 127.0.0.1, and loopback ranges are blocked."""
    with pytest.raises(PermissionError, match="adresse privée ou locale"):
        validate_target_url_security("http://127.0.0.1:8000/rss")

    with pytest.raises(PermissionError, match="adresse privée ou locale"):
        validate_target_url_security("http://127.0.0.2:8000/rss")


def test_ssrf_blocks_cloud_metadata():
    """Verify AWS/GCP/Azure link-local metadata endpoints are blocked."""
    with pytest.raises(PermissionError, match="métadonnées cloud"):
        validate_target_url_security("http://169.254.169.254/latest/meta-data/")

    with pytest.raises(PermissionError, match="métadonnées cloud"):
        validate_target_url_security("http://metadata.google.internal/computeMetadata/v1/")


def test_ssrf_blocks_private_subnets():
    """Verify RFC 1918 private subnets (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16) are blocked."""
    with pytest.raises(PermissionError, match="adresse privée ou locale"):
        validate_target_url_security("http://10.0.0.5/feed")

    with pytest.raises(PermissionError, match="adresse privée ou locale"):
        validate_target_url_security("http://172.16.1.100/atom.xml")

    with pytest.raises(PermissionError, match="adresse privée ou locale"):
        validate_target_url_security("http://192.168.1.1/rss")


def test_ssrf_blocks_domain_resolving_to_private_ip():
    """Verify domain resolving to a private/loopback IP is blocked."""
    with patch("socket.getaddrinfo", return_value=[(None, None, None, None, ("127.0.0.1", 80))]):
        with pytest.raises(PermissionError, match="résout vers une IP privée ou locale"):
            validate_target_url_security("http://local-rebinding.attacker.com/rss")


def test_fetch_safe_url_blocks_redirect_to_private_ip():
    """Verify safe fetch detects and rejects redirect pointing to an internal IP."""
    # First request returns 302 redirecting to http://127.0.0.1:8080/admin
    mock_resp_1 = MagicMock()
    mock_resp_1.is_redirect = True
    mock_resp_1.headers = {"location": "http://127.0.0.1:8080/admin"}

    with patch("packages.tools.browse.validate_target_url_security") as mock_validate:
        # First call succeeds for public url, second call fails for private redirect target
        def side_effect(url):
            if "127.0.0.1" in url:
                raise PermissionError("SSRF: Redirect to private IP blocked")
            return None

        mock_validate.side_effect = side_effect

        with patch("httpx.Client.get", return_value=mock_resp_1):
            with pytest.raises(PermissionError, match="SSRF: Redirect to private IP blocked"):
                fetch_safe_url("https://example.com/valid-feed.xml")


def test_fetch_safe_url_enforces_size_limit():
    """Verify fetch_safe_url rejects payloads exceeding max_bytes."""
    mock_resp = MagicMock()
    mock_resp.is_redirect = False
    mock_resp.content = b"X" * 1050  # Over 1000 limit

    with patch("packages.tools.browse.validate_target_url_security"):
        with patch("httpx.Client.get", return_value=mock_resp):
            with pytest.raises(ValueError, match="Taille de contenu trop volumineuse"):
                fetch_safe_url("https://example.com/giant.xml", max_bytes=1000)


def test_xml_valid_rss_and_atom_parsing():
    """Verify valid RSS 2.0 and Atom feeds parse cleanly into OfficialDataSignalItem."""
    rss_content = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <title>Tech News</title>
            <item>
                <title>Release 2.0</title>
                <link>https://tech.example.com/r2</link>
                <description>New multi-agent engine release</description>
                <pubDate>2026-10-15</pubDate>
            </item>
        </channel>
    </rss>"""

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = rss_content

    with patch("packages.tools.data_connectors.fetch_safe_url", return_value=mock_resp):
        items = OfficialDataConnectors.fetch_rss_feed("https://tech.example.com/rss.xml")
        assert len(items) == 1
        assert items[0].title == "Release 2.0"
        assert items[0].url == "https://tech.example.com/r2"


def test_xml_malformed_feed_handled_gracefully():
    """Verify malformed/truncated XML does not raise an unhandled exception."""
    bad_xml = "<rss><channel><item><title>Unclosed"
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = bad_xml

    with patch("packages.tools.data_connectors.fetch_safe_url", return_value=mock_resp):
        items = OfficialDataConnectors.fetch_rss_feed("https://tech.example.com/broken.xml")
        assert items == []


def test_xxe_payload_defused_and_rejected():
    """Verify XXE external entity expansion and DTD bombs are blocked by defusedxml."""
    xxe_payload = """<?xml version="1.0"?>
    <!DOCTYPE lolz [
        <!ENTITY lol "lol">
        <!ENTITY lol1 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
        <!ENTITY lol2 "&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;&lol1;">
    ]>
    <rss version="2.0">
        <channel>
            <item>
                <title>&lol2;</title>
            </item>
        </channel>
    </rss>"""

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = xxe_payload

    with patch("packages.tools.data_connectors.fetch_safe_url", return_value=mock_resp):
        # defusedxml will detect entity expansion / DTD and refuse to resolve it
        items = OfficialDataConnectors.fetch_rss_feed("https://tech.example.com/xxe.xml")
        # Either handled cleanly returning [] or logged without expanding
        assert items == []
