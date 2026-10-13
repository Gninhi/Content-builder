import asyncio
import ipaddress
import json
import logging
import re
import socket
import time
from typing import Set
from urllib.parse import urlparse, urljoin
import urllib.robotparser

import httpx
from bs4 import BeautifulSoup

from packages.security.prompt_injection import sanitize_untrusted_text
from packages.tools.schemas import BrowseResponse

logger = logging.getLogger(__name__)

FORBIDDEN_DOMAINS: Set[str] = {
    "linkedin.com",
    "www.linkedin.com",
    "licdn.com",
    "twitter.com",
    "www.twitter.com",
    "x.com",
    "www.x.com",
    "twimg.com",
    "t.co",
}

DEFAULT_USER_AGENT = (
    "ContentOps-Harness-Bot/1.0 (+https://content-builder.local/compliance)"
)
MAX_CONTENT_BYTES = 1_000_000  # 1 MB maximum content limit


def validate_target_url_security(url: str) -> None:
    """
    Strict SSRF and domain guard:
    1. Rejects non-HTTP(S) protocols.
    2. Blocks private IPs, loopback, link-local, cloud metadata endpoints.
    3. Blocks scraping targets with strictly enforced official APIs (LinkedIn, X).
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise PermissionError(
            f"Protocole non autorisé : '{parsed.scheme}'. Seuls http et https sont acceptés."
        )

    hostname = (parsed.hostname or "").lower()
    if not hostname:
        raise ValueError("URL sans nom d'hôte valide.")

    # 1. Block LinkedIn and X
    for forbidden in FORBIDDEN_DOMAINS:
        if hostname == forbidden or hostname.endswith(f".{forbidden}"):
            raise PermissionError(
                f"Navigation/scraping interdit sur '{hostname}' : usage exclusif des APIs officielles."
            )

    # 2. Block Local/Private IPs (SSRF protection)
    try:
        ip = ipaddress.ip_address(hostname)
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_unspecified
        ):
            raise PermissionError(
                f"Sécurité SSRF : L'IP cible ({hostname}) est une adresse privée ou locale interdite."
            )
    except ValueError:
        # Resolve hostname to check underlying IP
        try:
            resolved_ips = socket.getaddrinfo(hostname, None)
            for item in resolved_ips:
                target_ip = item[4][0]
                ip_obj = ipaddress.ip_address(target_ip)
                if (
                    ip_obj.is_private
                    or ip_obj.is_loopback
                    or ip_obj.is_link_local
                ):
                    raise PermissionError(
                        f"Sécurité SSRF : Le domaine '{hostname}' résout vers une IP privée ({target_ip})."
                    )
        except socket.gaierror:
            pass  # DNS resolution will fail naturally later


def check_robots_txt_allowed(url: str, user_agent: str = "*") -> bool:
    """Checks robots.txt compliance before reading an external page."""
    try:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url(robots_url)
        # Fast 3s read of robots.txt
        with httpx.Client(timeout=3.0, follow_redirects=True) as client:
            resp = client.get(robots_url)
            if resp.status_code == 200:
                rp.parse(resp.text.splitlines())
                return rp.can_fetch(user_agent, url)
            elif resp.status_code in (401, 403):
                return False
            return True
    except Exception:
        # Default allow if robots.txt unreachable
        return True


def extract_metadata_and_text(html: str, target_url: str) -> dict:
    """Extracts canonical URL, title, published date, author, and clean main text from HTML."""
    soup = BeautifulSoup(html[:MAX_CONTENT_BYTES], "html.parser")

    # Remove non-content tags
    for tag in soup(
        ["script", "style", "nav", "footer", "header", "aside", "noscript", "svg", "form"]
    ):
        tag.decompose()

    # Title
    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    elif soup.find("meta", property="og:title"):
        title = str(soup.find("meta", property="og:title").get("content", ""))

    # Canonical URL
    canon = target_url
    link_canon = soup.find("link", rel="canonical")
    if link_canon and link_canon.get("href"):
        canon = str(link_canon.get("href"))

    # Publication date
    pub_date = None
    date_meta = (
        soup.find("meta", property="article:published_time")
        or soup.find("meta", attrs={"name": "date"})
        or soup.find("meta", attrs={"name": "pubdate"})
        or soup.find("meta", attrs={"name": "publication_date"})
    )
    if date_meta and date_meta.get("content"):
        pub_date = str(date_meta.get("content"))

    # JSON-LD Schema detection
    if not pub_date:
        for s in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(s.string or "{}")
                if isinstance(data, dict):
                    pub_date = data.get("datePublished") or data.get(
                        "dateCreated"
                    )
                elif isinstance(data, list) and data:
                    pub_date = data[0].get("datePublished")
                if pub_date:
                    break
            except Exception:
                continue

    # Clean text extraction
    text = soup.get_text(separator=" ", strip=True)
    clean_text = re.sub(r"\s+", " ", text).strip()

    return {
        "title": title or "Sans titre",
        "canonical_url": canon,
        "published_date": pub_date,
        "content": sanitize_untrusted_text(clean_text[:5000]),  # 5000 chars max
    }


class SafeBrowserTool:
    """
    Playwright-based sandboxed browser with SSRF guard, robots.txt, and fast httpx fallback.
    """

    def __init__(self, max_concurrent: int = 3):
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def browse(
        self,
        url: str,
        mode: str = "main_content",
        timeout_seconds: float = 15.0,
        workspace_id: str = "default",
    ) -> BrowseResponse:
        t0 = time.time()

        # 1. Security & SSRF checks
        try:
            validate_target_url_security(url)
        except PermissionError as pe:
            return BrowseResponse(
                url=url,
                canonical_url=url,
                title="",
                content="",
                status="FORBIDDEN_DOMAIN" if "officielle" in str(pe) else "SSRF_BLOCKED",
                error_message=str(pe),
                latency_ms=round((time.time() - t0) * 1000, 2),
            )
        except Exception as e:
            return BrowseResponse(
                url=url,
                canonical_url=url,
                title="",
                content="",
                status="FAILED",
                error_message=str(e),
                latency_ms=round((time.time() - t0) * 1000, 2),
            )

        # 2. Check robots.txt
        if not check_robots_txt_allowed(url, DEFAULT_USER_AGENT):
            return BrowseResponse(
                url=url,
                canonical_url=url,
                title="",
                content="",
                status="ROBOTS_DISALLOWED",
                error_message="Accès refusé par le fichier robots.txt du site.",
                latency_ms=round((time.time() - t0) * 1000, 2),
            )

        # 3. Attempt Playwright Chromium Execution
        async with self._semaphore:
            try:
                from playwright.async_api import async_playwright

                async with async_playwright() as p:
                    browser = await p.chromium.launch(
                        headless=True,
                        args=[
                            "--no-sandbox",
                            "--disable-setuid-sandbox",
                            "--disable-dev-shm-usage",
                            "--disable-gpu",
                        ],
                    )
                    context = await browser.new_context(
                        user_agent=DEFAULT_USER_AGENT,
                        viewport={"width": 1280, "height": 800},
                        java_script_enabled=True,
                        ignore_https_errors=False,
                    )
                    page = await context.new_page()

                    # Block media, fonts, images and intercept SSRF on redirects/subrequests
                    async def handle_pw_route(route):
                        req_url = route.request.url
                        try:
                            validate_target_url_security(req_url)
                        except Exception:
                            logger.warning(f"Playwright route aborted due to security guard: {req_url}")
                            await route.abort()
                            return

                        if route.request.resource_type in ("image", "media", "font", "stylesheet"):
                            await route.abort()
                        else:
                            await route.continue_()

                    await page.route("**/*", handle_pw_route)

                    await page.goto(
                        url,
                        wait_until="domcontentloaded",
                        timeout=int(timeout_seconds * 1000),
                    )
                    final_url = page.url
                    validate_target_url_security(final_url)
                    html = await page.content()
                    await browser.close()

                    meta = extract_metadata_and_text(html, final_url)
                    return BrowseResponse(
                        url=url,
                        canonical_url=meta["canonical_url"],
                        title=meta["title"],
                        content=meta["content"],
                        published_date=meta["published_date"],
                        status="SUCCESS",
                        latency_ms=round((time.time() - t0) * 1000, 2),
                    )
            except PermissionError as pw_perm_err:
                logger.warning(f"Playwright SSRF blocked: {pw_perm_err}")
                return BrowseResponse(
                    url=url,
                    canonical_url=url,
                    title="",
                    content="",
                    status="SSRF_BLOCKED",
                    error_message=str(pw_perm_err),
                    latency_ms=round((time.time() - t0) * 1000, 2),
                )
            except Exception as pw_err:
                logger.warning(
                    f"Playwright navigation failed ({pw_err}), falling back to secure HTTP request"
                )

        # 4. Fallback to secure HTTP request with explicit redirect validation (FND-04)
        try:
            async with httpx.AsyncClient(
                timeout=timeout_seconds,
                follow_redirects=False,
                headers={"User-Agent": DEFAULT_USER_AGENT},
            ) as client:
                current_url = url
                max_redirects = 5
                resp = None

                for _ in range(max_redirects + 1):
                    validate_target_url_security(current_url)
                    resp = await client.get(current_url)

                    if resp.is_redirect:
                        location = resp.headers.get("Location")
                        if not location:
                            break
                        next_url = urljoin(current_url, location)
                        validate_target_url_security(next_url)
                        current_url = next_url
                        continue
                    break

                if resp and resp.status_code == 200:
                    meta = extract_metadata_and_text(resp.text, current_url)
                    return BrowseResponse(
                        url=url,
                        canonical_url=meta["canonical_url"],
                        title=meta["title"],
                        content=meta["content"],
                        published_date=meta["published_date"],
                        status="SUCCESS",
                        latency_ms=round((time.time() - t0) * 1000, 2),
                    )
                else:
                    status_code = resp.status_code if resp else "NO_RESPONSE"
                    return BrowseResponse(
                        url=url,
                        canonical_url=url,
                        title="",
                        content="",
                        status="FAILED",
                        error_message=f"HTTP {status_code}",
                        latency_ms=round((time.time() - t0) * 1000, 2),
                    )
        except PermissionError as perm_err:
            logger.warning(f"SSRF blocked during redirect in browse: {perm_err}")
            return BrowseResponse(
                url=url,
                canonical_url=url,
                title="",
                content="",
                status="SSRF_BLOCKED",
                error_message=str(perm_err),
                latency_ms=round((time.time() - t0) * 1000, 2),
            )
        except Exception as http_err:
            return BrowseResponse(
                url=url,
                canonical_url=url,
                title="",
                content="",
                status="FAILED",
                error_message=str(http_err),
                latency_ms=round((time.time() - t0) * 1000, 2),
            )


# Global singleton instance
safe_browser_tool = SafeBrowserTool()
