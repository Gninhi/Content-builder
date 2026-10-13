import os
import pytest
from playwright.sync_api import sync_playwright

CHROME_BIN = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
BASE_URL = os.environ.get("CONTENTOPS_BASE_URL", "http://localhost:3000/ui/")

@pytest.fixture(scope="module")
def browser_context():
    with sync_playwright() as p:
        kwargs = {"headless": True}
        if os.path.exists(CHROME_BIN):
            kwargs["executable_path"] = CHROME_BIN
        browser = p.chromium.launch(**kwargs)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        yield context
        browser.close()

def authenticate_session(page):
    """Ensure user is logged in via demo or credentials."""
    page.goto(BASE_URL, wait_until="networkidle")
    demo_btn = page.locator("button:has-text('démo'), button:has-text('Démo')")
    if demo_btn.count() > 0:
        demo_btn.first.click()
        page.wait_for_timeout(2000)

def test_full_navigation_cycle_profil_veille_ideation_profil(browser_context):
    """
    Validates complete navigation cycle: Profil -> Veille -> Idéation -> Profil.
    Verifies sidebar, topbar, and main content remain visible at every step,
    and captures 0 unhandled pageerror exceptions.
    """
    page = browser_context.new_page()
    page_errors = []
    page.on("pageerror", lambda err: page_errors.append(f"{err.message}\n{err.stack}"))

    # 1. Login
    authenticate_session(page)

    # 2. Go to Profile
    page.evaluate("window.location.hash = 'profile'")
    page.wait_for_timeout(1500)
    assert page.locator("#sidebar-navigation").is_visible(), "Sidebar must be visible on Profil"
    assert page.locator("header, div:has-text('ContentOps')").first.is_visible(), "Header must be visible on Profil"
    assert len(page_errors) == 0, f"No page errors on Profil: {page_errors}"

    # 3. Profil -> Veille
    veille_btn = page.locator("button:has-text('Veille Technologique')")
    if veille_btn.count() > 0:
        veille_btn.first.click()
    else:
        page.evaluate("window.location.hash = 'veille'")
    page.wait_for_timeout(2000)

    assert page.locator("#sidebar-navigation").is_visible(), "Sidebar must be visible on Veille"
    assert page.locator("header, div:has-text('ContentOps')").first.is_visible(), "Header must be visible on Veille"
    assert page.locator("h1:has-text('Veille Technologique'), div:has-text('Veille')").first.is_visible(), "Veille content must be visible"
    root_html = page.inner_html("#root")
    assert len(root_html) > 5000, f"Root must not be empty or crashed (len={len(root_html)})"
    assert len(page_errors) == 0, f"No page errors when navigating to Veille: {page_errors}"

    # 4. Veille -> Idéation
    ideation_btn = page.locator("button:has-text('Idéation & Angles')")
    if ideation_btn.count() > 0:
        ideation_btn.first.click()
    else:
        page.evaluate("window.location.hash = 'ideation'")
    page.wait_for_timeout(2000)

    assert page.locator("#sidebar-navigation").is_visible(), "Sidebar must be visible on Idéation"
    assert page.locator("header, div:has-text('ContentOps')").first.is_visible(), "Header must be visible on Idéation"
    assert page.locator("h2:has-text('Idéation'), div:has-text('Idéation')").first.is_visible(), "Idéation content must be visible"
    root_html = page.inner_html("#root")
    assert len(root_html) > 5000, f"Root must not be empty or crashed (len={len(root_html)})"
    assert len(page_errors) == 0, f"No page errors when navigating to Idéation: {page_errors}"

    # 5. Idéation -> Profil
    profile_btn = page.locator("button:has-text('Profil de Marque')")
    if profile_btn.count() > 0:
        profile_btn.first.click()
    else:
        page.evaluate("window.location.hash = 'profile'")
    page.wait_for_timeout(1500)

    assert page.locator("#sidebar-navigation").is_visible(), "Sidebar must be visible after return to Profil"
    assert len(page_errors) == 0, f"Total page errors must be 0: {page_errors}"
    page.close()

def test_direct_route_access_and_reload(browser_context):
    """
    Validates direct access via URL hash and page reloads on #veille and #ideation.
    """
    page = browser_context.new_page()
    page_errors = []
    page.on("pageerror", lambda err: page_errors.append(f"{err.message}\n{err.stack}"))

    authenticate_session(page)

    # Direct access #veille + reload
    page.goto(f"{BASE_URL}#veille", wait_until="networkidle")
    page.wait_for_timeout(1500)
    assert page.locator("#sidebar-navigation").is_visible()
    assert page.locator("h1:has-text('Veille Technologique'), div:has-text('Veille')").first.is_visible()

    page.reload(wait_until="networkidle")
    page.wait_for_timeout(1500)
    assert page.locator("#sidebar-navigation").is_visible()
    assert len(page_errors) == 0

    # Direct access #ideation + reload
    page.goto(f"{BASE_URL}#ideation", wait_until="networkidle")
    page.wait_for_timeout(1500)
    assert page.locator("#sidebar-navigation").is_visible()
    assert page.locator("h2:has-text('Idéation'), div:has-text('Idéation')").first.is_visible()

    page.reload(wait_until="networkidle")
    page.wait_for_timeout(1500)
    assert page.locator("#sidebar-navigation").is_visible()
    assert len(page_errors) == 0
    page.close()

def test_empty_api_state_handling(browser_context):
    """
    Intercepts /v1/ideas to return an empty array [].
    Verifies that the page renders an explicit EmptyState, without crashing or blank screen.
    """
    page = browser_context.new_page()
    page_errors = []
    page.on("pageerror", lambda err: page_errors.append(f"{err.message}\n{err.stack}"))

    authenticate_session(page)

    # Route interception: return empty ideas array
    def handle_ideas_route(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body="[]"
        )

    page.route("**/v1/ideas*", handle_ideas_route)
    page.evaluate("window.location.hash = 'ideation'")
    page.wait_for_timeout(2000)

    assert page.locator("#sidebar-navigation").is_visible(), "Sidebar must remain visible on empty ideas"
    root_html = page.inner_html("#root")
    assert len(root_html) > 5000, "Root DOM must not be wiped"
    # EmptyState title "Aucune idée trouvée" is rendered
    assert page.get_by_text("Aucune idée trouvée").is_visible(), "Empty state message must be visible"
    assert len(page_errors) == 0
    page.close()

def test_api_error_state_and_boundary_resilience(browser_context):
    """
    Intercepts /v1/ideas with a 500 error.
    Verifies that the application does NOT crash to a black screen,
    and that ErrorState handles the failure gracefully with preserved navigation.
    """
    page = browser_context.new_page()
    page_errors = []
    page.on("pageerror", lambda err: page_errors.append(f"{err.message}\n{err.stack}"))

    authenticate_session(page)

    # Route interception: return 500 internal server error
    def handle_error_route(route):
        route.fulfill(
            status=500,
            content_type="application/json",
            body='{"detail": "Internal database connection failure"}'
        )

    page.route("**/v1/ideas*", handle_error_route)
    page.evaluate("window.location.hash = 'ideation'")
    page.wait_for_timeout(2000)

    assert page.locator("#sidebar-navigation").is_visible(), "Sidebar navigation must stay visible even on API 500"
    root_html = page.inner_html("#root")
    assert len(root_html) > 5000, "Root DOM must not collapse to black screen"
    # Should display ErrorState component
    assert page.get_by_text("Erreur de chargement").is_visible(), "ErrorState title must be visible"
    assert page.get_by_text("Internal database connection failure").is_visible(), "Error detail must be visible"
    assert len(page_errors) == 0, f"No unhandled React pageerror crashes: {page_errors}"
    page.close()

def test_expired_session_graceful_recovery(browser_context):
    """
    Simulates session expiration (all API endpoints return 401).
    Verifies that the application gracefully redirects to the authentication screen
    with visible login interface, without crashing to a black screen.
    """
    page = browser_context.new_page()
    page_errors = []
    page.on("pageerror", lambda err: page_errors.append(f"{err.message}\n{err.stack}"))

    authenticate_session(page)

    # All subsequent API requests return 401 Unauthorized
    page.route("**/v1/**", lambda r: r.fulfill(status=401, content_type="application/json", body='{"detail": "Token expired"}'))
    page.evaluate("window.location.hash = 'veille'")
    page.wait_for_timeout(2000)

    root_html = page.inner_html("#root")
    assert len(root_html) > 3000, "Auth screen must be rendered, root DOM must not be empty"
    assert page.get_by_text("Connexion").first.is_visible(), "Login interface must be presented to user"
    assert len(page_errors) == 0, f"No unhandled errors on session expiration: {page_errors}"
    page.close()
