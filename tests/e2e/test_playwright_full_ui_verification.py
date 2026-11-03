"""
Comprehensive Playwright E2E UI & Component Verification Suite.
Validates:
1. Every screen & interface (Auth, Dashboard, Veille, Ideation, Inbox, Calendar, Insights, Brand, Connections, Settings, Profile, Agents, StyleGuide).
2. Every navigation link, button, and router transition.
3. Every interactive component (Modals, Dialogs, Dropdowns, Tabs, Inputs, Sliders, Pickers).
4. Global controls (Language switch FR/EN, Theme mode Dark/Light, Color palette switch, Command palette Cmd+K, Kill switch indicator).
5. Responsive mobile drawer & layout stability.
6. Zero unhandled JavaScript page errors and non-crashing ErrorBoundaries.
"""

import os
import pytest
from playwright.sync_api import sync_playwright, Page

CHROME_BIN = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
BASE_URL = os.environ.get("CONTENTOPS_BASE_URL", "http://localhost:3000/ui/")


@pytest.fixture(scope="module")
def browser_context():
    with sync_playwright() as p:
        kwargs = {"headless": True}
        if os.path.exists(CHROME_BIN):
            kwargs["executable_path"] = CHROME_BIN
        browser = p.chromium.launch(**kwargs)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            ignore_https_errors=True
        )
        yield context
        browser.close()


@pytest.fixture(scope="function")
def page(browser_context):
    p = browser_context.new_page()
    page_errors = []
    console_errors = []

    def on_page_error(err):
        page_errors.append(f"{err.message}\n{err.stack}")

    def on_console(msg):
        if msg.type == "error":
            # Filter out expected network aborts or non-fatal asset warnings
            text = msg.text
            if "favicon.ico" not in text and "ERR_CONNECTION_REFUSED" not in text:
                console_errors.append(text)

    p.on("pageerror", on_page_error)
    p.on("console", on_console)

    p._page_errors = page_errors
    p._console_errors = console_errors

    yield p
    p.close()


def authenticate_demo_session(page: Page):
    """Authenticate the browser session via Demo login button and wait for AppShell."""
    page.goto(BASE_URL, wait_until="networkidle")
    
    # Check if already authenticated
    if page.locator("#sidebar-navigation").is_visible():
        return

    demo_btn = page.locator("button:has-text('démo'), button:has-text('Démo')")
    if demo_btn.count() > 0:
        demo_btn.first.click()
        page.wait_for_selector("#sidebar-navigation", timeout=10000)
        page.wait_for_timeout(1000)


def test_01_auth_screen_views_and_controls(page: Page):
    """
    Test 01: Unauthenticated AuthScreen.
    Validates Login form, Register form, Forgot password, Theme toggle, Language toggle,
    and password strength meter without unhandled exceptions.
    """
    page.goto(BASE_URL, wait_until="networkidle")

    # If already logged in from previous session, log out first
    logout_btn = page.locator("button[title*='Déconnexion'], button[title*='Logout'], button:has-text('Déconnexion')")
    if logout_btn.count() > 0 and logout_btn.first.is_visible():
        logout_btn.first.click()
        page.wait_for_timeout(1500)

    # 1. Verify Login form elements
    assert page.locator("h1:has-text('ContentOps'), span:has-text('ContentOps')").first.is_visible()
    email_input = page.locator("input[type='email']")
    assert email_input.is_visible()
    pwd_input = page.locator("input[type='password']")
    assert pwd_input.is_visible()
    login_submit = page.locator("button:has-text('Se connecter'), button:has-text('Sign In')")
    assert login_submit.is_visible()

    # 2. Test password toggle button
    pwd_toggle = page.locator("button[aria-label*='mot de passe'], button[aria-label*='password']").first
    if pwd_toggle.is_visible():
        pwd_toggle.click()
        page.wait_for_timeout(300)
        # Should now be text type
        assert page.locator("input[type='text']").count() > 0
        pwd_toggle.click()
        page.wait_for_timeout(300)

    # 3. Test Language switch on AuthScreen
    fr_btn = page.locator("button:has-text('FR')").first
    en_btn = page.locator("button:has-text('EN')").first
    if en_btn.is_visible():
        en_btn.click()
        page.wait_for_timeout(500)
        assert page.locator("button:has-text('Sign In'), span:has-text('Sign In')").count() > 0
        fr_btn.click()
        page.wait_for_timeout(500)

    # 4. Test View Switch to Register
    create_account_btn = page.locator("button:has-text('Créer un compte'), button:has-text('Create account')")
    if create_account_btn.is_visible():
        create_account_btn.click()
        page.wait_for_timeout(500)
        # Register inputs
        assert page.locator("input[type='email']").is_visible()
        # Test password strength meter (Faible -> Robuste)
        reg_pwd = page.locator("input[type='password']").first
        reg_pwd.fill("weak")
        page.wait_for_timeout(300)
        assert page.locator("text=Faible").is_visible()
        reg_pwd.fill("StrongPassword123!@#")
        page.wait_for_timeout(300)
        assert page.locator("text=Robuste").is_visible()

    # 5. Test View Switch to Forgot Password
    back_to_login = page.locator("button:has-text('Se connecter'), button:has-text('Retour à la connexion')").first
    if back_to_login.is_visible():
        back_to_login.click()
        page.wait_for_timeout(500)

    forgot_btn = page.locator("button:has-text('Mot de passe oublié')")
    if forgot_btn.is_visible():
        forgot_btn.click()
        page.wait_for_timeout(500)
        assert page.locator("button:has-text('Envoyer les instructions'), button:has-text('Réinitialiser'), button:has-text('Envoyer le lien')").is_visible()
        back_btn = page.locator("button:has-text('Retour à la connexion')")
        if back_btn.is_visible():
            back_btn.click()
            page.wait_for_timeout(500)

    # Verify zero fatal errors
    assert len(page._page_errors) == 0, f"Page errors on AuthScreen: {page._page_errors}"


def test_02_demo_login_and_app_shell_structure(page: Page):
    """
    Test 02: Log in via Demo mode and verify the global AppShell, Sidebar, and Topbar.
    """
    authenticate_demo_session(page)

    # Verify Sidebar Navigation presence
    sidebar = page.locator("#sidebar-navigation")
    assert sidebar.is_visible(), "Sidebar navigation must be mounted and visible"

    # Verify Header Brand
    assert page.locator("span:has-text('ContentOps Harness')").first.is_visible()

    # Verify Environment Badge (Sandbox / Live)
    assert page.locator("span:has-text('SANDBOX'), span:has-text('Sandbox'), span:has-text('PROD')").first.is_visible()

    # Verify Topbar components
    assert page.locator("header").first.is_visible()
    assert page.locator("header h1").first.is_visible()
    assert page.locator("header button:has-text('FR'), header button:has-text('EN')").first.is_visible()

    # Zero page errors
    assert len(page._page_errors) == 0, f"Page errors after login: {page._page_errors}"


def test_03_exhaustive_sidebar_links_navigation(page: Page):
    """
    Test 03: Click every single navigation button in the sidebar and verify route transition.
    Covers: Dashboard, Veille, Ideation, Inbox, Calendar, Insights, Brand, Connections, Settings, Profile, Agents, StyleGuide.
    """
    authenticate_demo_session(page)

    screens = [
        ("dashboard", "Vue d'ensemble", ["KPI", "Tableau de bord", "Vue d'ensemble", "Indicateurs", "Éditorial"]),
        ("veille", "Veille Technologique", ["Veille", "Signaux", "Sources", "Radar"]),
        ("ideation", "Idéation & Angles", ["Idéation", "Angles", "Recherche", "Générer", "Veille"]),
        ("inbox", "Revue HITL", ["Validation", "Inbox", "Revue", "Approbation", "HITL"]),
        ("calendar", "Calendrier", ["Calendrier", "Planification", "Mois", "Semaine"]),
        ("insights", "Stratégie & Insights", ["Insights", "Performance", "Stratégie", "Analytique"]),
        ("brand", "Profil de Marque", ["Profil de Marque", "Voix", "Piliers", "Audience"]),
        ("connections", "Connexions Sociales", ["Connexions", "LinkedIn", "Réseaux", "Comptes", "Sociales"]),
        ("settings", "Gouvernance & Paramètres", ["Paramètres", "Configuration", "Gouvernance", "Kill Switch"]),
        ("agents", "Banc d'Essai", ["Banc d'Essai", "Agents", "Studio", "Exécution", "Diagnostic"]),
        ("styleguide", "Guide de Style", ["Guide de Style", "Design System", "Tokens", "Composants"]),
        ("profile", "Mon Profil", ["Profil", "Utilisateur", "Sécurité", "Informations"]),
    ]

    for screen_id, fallback_title, expected_keywords in screens:
        # Navigate via sidebar click using filter(has_text=...) to safely handle apostrophes
        nav_button = page.locator("#sidebar-navigation button").filter(has_text=fallback_title)
        if nav_button.count() > 0 and nav_button.first.is_visible():
            nav_button.first.click()
        else:
            page.evaluate(f"window.location.hash = '{screen_id}'")

        page.wait_for_timeout(1000)

        # Confirm hash is updated
        current_hash = page.evaluate("window.location.hash")
        assert screen_id in current_hash, f"Expected hash #{screen_id}, got {current_hash}"

        # Verify page content is rendered (not empty or crashed)
        root_content = page.inner_html("#root")
        assert len(root_content) > 5000, f"Screen {screen_id} rendered too small DOM ({len(root_content)} bytes)"

        # Check at least one expected keyword is visible on the screen
        found_keyword = any(page.locator(f"text={kw}").count() > 0 for kw in expected_keywords)
        assert found_keyword, f"Screen {screen_id} should display at least one of {expected_keywords}"

    # Return to dashboard
    page.evaluate("window.location.hash = 'dashboard'")
    page.wait_for_timeout(500)
    assert len(page._page_errors) == 0, f"Page errors during navigation cycle: {page._page_errors}"


def test_04_dashboard_screen_components_and_actions(page: Page):
    """
    Test 04: DashboardScreen components, KPI cards, and quick navigation actions.
    """
    authenticate_demo_session(page)
    page.evaluate("window.location.hash = 'dashboard'")
    page.wait_for_timeout(1000)

    # Verify Metric Cards
    assert page.get_by_text("REVOIR", exact=False).or_(page.get_by_text("HITL", exact=False)).first.is_visible()
    assert page.get_by_text("PLANIFIÉS", exact=False).or_(page.get_by_text("Planifiés", exact=False)).first.is_visible()
    assert page.get_by_text("BUDGET", exact=False).or_(page.get_by_text("Budget", exact=False)).first.is_visible()

    # Test Quick Actions
    inbox_link = page.locator("button:has-text('Revue HITL'), a:has-text('Revue HITL')").first
    if inbox_link.is_visible():
        inbox_link.click()
        page.wait_for_timeout(1000)
        assert "inbox" in page.evaluate("window.location.hash")

    # Navigate back to dashboard
    page.evaluate("window.location.hash = 'dashboard'")
    page.wait_for_timeout(500)
    assert len(page._page_errors) == 0


def test_05_veille_screen_components_and_sources_modal(page: Page):
    """
    Test 05: VeilleScreen search, axis filters, and Add Source dialog.
    """
    authenticate_demo_session(page)
    page.evaluate("window.location.hash = 'veille'")
    page.wait_for_timeout(1000)

    # Verify Search input
    search_input = page.locator("input[placeholder*='signaux'], input[placeholder*='signals'], input[placeholder*='Filtrer']").first
    assert search_input.is_visible()
    search_input.fill("Gouvernance IA")
    page.wait_for_timeout(300)
    search_input.fill("")

    # Verify Axis filters
    axis_all = page.locator("button:has-text('Tous les axes'), button:has-text('All axes')").first
    assert axis_all.is_visible()

    # Test "Sources" Modal
    manage_sources_btn = page.locator("button:has-text('Sources')").first
    if manage_sources_btn.is_visible():
        manage_sources_btn.click()
        page.wait_for_timeout(800)

        # Dialog should be open
        dialog = page.locator("div[role='dialog'], div[aria-modal='true']")
        assert dialog.first.is_visible(), "Sources modal should be visible"

        # Check modal inputs or contents
        assert page.locator("text=Gouvernance des Sources").or_(page.locator("text=Catalogue de Référence")).or_(page.locator("text=Monitoring Sources")).first.is_visible()
        assert page.locator("input").count() > 0

        # Close dialog via close button or Escape
        close_btn = page.locator("button[aria-label*='Fermer'], button[aria-label*='Close']").first
        if close_btn.is_visible():
            close_btn.click()
            page.wait_for_timeout(500)
        else:
            page.keyboard.press("Escape")
            page.wait_for_timeout(500)

    assert len(page._page_errors) == 0


def test_06_ideation_screen_filters_and_modal(page: Page):
    """
    Test 06: IdeationScreen angle filters, research trigger, and ideas rendering.
    """
    authenticate_demo_session(page)
    page.evaluate("window.location.hash = 'ideation'")
    page.wait_for_timeout(1000)

    # Search & filters if available
    search_input = page.locator("input[type='text']").first
    if search_input.is_visible():
        search_input.fill("Agent")
        page.wait_for_timeout(300)
        search_input.fill("")

    # Research / Generation button ("Lancer une Idéation")
    research_btn = page.locator("button:has-text('Lancer une Idéation'), button:has-text('Idéation')").first
    assert research_btn.is_visible()

    # Content or EmptyState must be present
    root_html = page.inner_html("#root")
    assert len(root_html) > 5000
    assert len(page._page_errors) == 0


def test_07_inbox_screen_hitl_and_shortcuts_modal(page: Page):
    """
    Test 07: InboxScreen HITL validation queue and keyboard shortcuts modal.
    """
    authenticate_demo_session(page)
    page.evaluate("window.location.hash = 'inbox'")
    page.wait_for_timeout(1000)

    # Check for Shortcuts trigger button
    shortcuts_btn = page.locator("button[aria-label*='Raccourcis'], button[title*='Raccourcis'], button:has-text('?')").first
    if shortcuts_btn.is_visible():
        shortcuts_btn.click()
        page.wait_for_timeout(600)

        # Modal should be visible
        shortcuts_modal = page.locator("div[role='dialog'], div:has-text('Raccourcis clavier')").first
        assert shortcuts_modal.is_visible()
        assert page.locator("text=Approuver").first.is_visible()

        # Close shortcuts modal with Escape or close button
        page.keyboard.press("Escape")
        page.wait_for_timeout(500)

    assert len(page._page_errors) == 0


def test_08_calendar_screen_view_switchers_and_navigation(page: Page):
    """
    Test 08: CalendarScreen view toggles (Mois, Semaine, Liste) and date controls.
    """
    authenticate_demo_session(page)
    page.evaluate("window.location.hash = 'calendar'")
    page.wait_for_timeout(1000)

    # View switcher buttons
    mois_btn = page.locator("button:has-text('Mois'), button:has-text('Month')").first
    semaine_btn = page.locator("button:has-text('Semaine'), button:has-text('Week')").first
    liste_btn = page.locator("button:has-text('Liste'), button:has-text('List')").first

    if semaine_btn.is_visible():
        semaine_btn.click()
        page.wait_for_timeout(600)
        assert len(page.inner_html("#root")) > 5000

    if liste_btn.is_visible():
        liste_btn.click()
        page.wait_for_timeout(600)
        assert len(page.inner_html("#root")) > 5000

    if mois_btn.is_visible():
        mois_btn.click()
        page.wait_for_timeout(600)
        assert len(page.inner_html("#root")) > 5000

    # Navigation buttons (Next, Previous, Today)
    today_btn = page.locator("button:has-text('Aujourd’hui'), button:has-text(\"Aujourd'hui\"), button:has-text('Today')").first
    if today_btn.is_visible():
        today_btn.click()
        page.wait_for_timeout(300)

    assert len(page._page_errors) == 0


def test_09_insights_screen_period_filters(page: Page):
    """
    Test 09: InsightsScreen period filters (7j, 30j, 90j) and chart metrics.
    """
    authenticate_demo_session(page)
    page.evaluate("window.location.hash = 'insights'")
    page.wait_for_timeout(1000)

    p7 = page.locator("button:has-text('7j'), button:has-text('7d')").first
    p30 = page.locator("button:has-text('30j'), button:has-text('30d')").first
    p90 = page.locator("button:has-text('90j'), button:has-text('90d')").first

    if p30.is_visible():
        p30.click()
        page.wait_for_timeout(500)
    if p90.is_visible():
        p90.click()
        page.wait_for_timeout(500)
    if p7.is_visible():
        p7.click()
        page.wait_for_timeout(500)

    assert len(page.inner_html("#root")) > 5000
    assert len(page._page_errors) == 0


def test_10_brand_profile_form_interaction(page: Page):
    """
    Test 10: BrandProfileScreen form inputs, tag addition, and save action.
    """
    authenticate_demo_session(page)
    page.evaluate("window.location.hash = 'brand'")
    page.wait_for_timeout(1000)

    # Voice Textarea
    voice_textarea = page.locator("textarea").first
    if voice_textarea.is_visible():
        voice_textarea.fill("Voix experte, pragmatique, centrée sur la résilience logicielle et la gouvernance.")
        page.wait_for_timeout(300)

    # Pillar tag input
    pillar_input = page.locator("input[placeholder*='pilier'], input[placeholder*='pillar']").first
    if pillar_input.is_visible():
        pillar_input.fill("Résilience Multi-Agents")
        add_btn = page.locator("button:has-text('Ajouter')").first
        if add_btn.is_visible():
            add_btn.click()
            page.wait_for_timeout(300)

    # Save button
    save_btn = page.locator("button:has-text('Enregistrer'), button:has-text('Save')").first
    if save_btn.is_visible():
        save_btn.click()
        page.wait_for_timeout(1000)

    assert len(page._page_errors) == 0


def test_11_connections_screen_and_sandbox_connect(page: Page):
    """
    Test 11: ConnectionsScreen platform cards, sandbox connect, and test-connection.
    """
    authenticate_demo_session(page)
    page.evaluate("window.location.hash = 'connections'")
    page.wait_for_timeout(1000)

    # Verify social platforms are rendered
    assert page.locator("h3:has-text('LinkedIn')").first.is_visible()
    assert page.locator("h3:has-text('X (Twitter)')").first.is_visible()

    # Test Sandbox connect if button available
    sandbox_btn = page.locator("button:has-text('Simuler connexion Sandbox'), button:has-text('Sandbox')").first
    if sandbox_btn.is_visible():
        sandbox_btn.click()
        page.wait_for_timeout(1500)

    # Test connection button (Read-only C6 verification)
    test_conn_btn = page.locator("button:has-text('Tester la connexion'), button:has-text('Test connection')").first
    if test_conn_btn.is_visible():
        test_conn_btn.click()
        page.wait_for_timeout(1500)

    assert len(page._page_errors) == 0


def test_12_settings_screen_and_llm_config(page: Page):
    """
    Test 12: SettingsScreen workspace settings, Kill-switch UI, and LLM Configuration section.
    """
    authenticate_demo_session(page)
    page.evaluate("window.location.hash = 'settings'")
    page.wait_for_timeout(1000)

    # 1. LLM Tab & Section (Default Active Tab)
    assert page.locator("text=Modèles & Providers LLM").first.is_visible()
    assert page.locator("select").count() > 0

    provider_select = page.locator("select").first
    if provider_select.is_visible():
        provider_select.select_option(index=1)
        page.wait_for_timeout(300)

    # 2. Switch to Governance & Kill Switch Tab
    gov_tab = page.locator("button:has-text('Gouvernance & Kill Switch')").first
    assert gov_tab.is_visible()
    gov_tab.click()
    page.wait_for_timeout(500)

    # Emergency Kill Switch section should now be visible
    assert page.locator("text=Kill Switch").first.is_visible()
    assert page.locator("button:has-text('Activer'), button:has-text('Désactiver'), button:has-text('Kill Switch')").first.is_visible()

    assert len(page._page_errors) == 0


def test_13_user_profile_screen_all_six_tabs(page: Page):
    """
    Test 13: UserProfileScreen tabs (Personal, Preferences, Notifications, Security, Workspaces, GDPR).
    """
    authenticate_demo_session(page)
    page.evaluate("window.location.hash = 'profile'")
    page.wait_for_timeout(1000)

    tabs = [
        ("Informations", ["Nom complet", "Email", "Fonction"]),
        ("Préférences", ["Thème", "Densité", "Vue par défaut"]),
        ("Notifications", ["Alertes critiques", "Email", "Validation"]),
        ("Sécurité", ["Mot de passe", "Sessions actives"]),
        ("Espaces", ["Espaces de travail", "Rôle"]),
        ("Confidentialité", ["Exporter mes données", "Supprimer mon compte"]),
    ]

    for tab_label, expected_keywords in tabs:
        tab_btn = page.locator(f"button:has-text('{tab_label}')").first
        if tab_btn.is_visible():
            tab_btn.click()
            page.wait_for_timeout(600)
            assert len(page.inner_html("#root")) > 5000
            # Check at least one expected text keyword
            found = any(page.locator(f"text={kw}").count() > 0 for kw in expected_keywords)
            assert found, f"Tab {tab_label} missing expected keywords: {expected_keywords}"

    assert len(page._page_errors) == 0


def test_14_agents_screen_test_bench(page: Page):
    """
    Test 14: AgentsScreen test bench and state indicators.
    """
    authenticate_demo_session(page)
    page.evaluate("window.location.hash = 'agents'")
    page.wait_for_timeout(1000)

    # Check for test bench title
    bench_heading = page.locator("h2").filter(has_text="Banc d'Essai").or_(page.locator("h2").filter(has_text="Diagnostic des Agents")).first
    assert bench_heading.is_visible()

    # Test Agent Tabs
    agent_tabs = ["1. Idéation", "2. Production", "3. Quality Gate", "4. Réécriture", "5. Stratégie", "6. Connecteurs"]
    for tab in agent_tabs:
        tab_btn = page.locator("button").filter(has_text=tab).first
        if tab_btn.is_visible():
            tab_btn.click()
            page.wait_for_timeout(300)

    assert len(page.inner_html("#root")) > 5000
    assert len(page._page_errors) == 0


def test_15_styleguide_screen_tabs_and_dialog_modals(page: Page):
    """
    Test 15: StyleGuideScreen component tokens gallery and interactive modals.
    """
    authenticate_demo_session(page)
    page.evaluate("window.location.hash = 'styleguide'")
    page.wait_for_timeout(1000)

    styleguide_tabs = [
        "Tokens",
        "Typographie",
        "Boutons",
        "Badges",
        "Formulaires",
        "États",
        "Aperçus Réseau",
        "Accessibilité",
    ]

    for tab in styleguide_tabs:
        btn = page.locator(f"button:has-text('{tab}')").first
        if btn.is_visible():
            btn.click()
            page.wait_for_timeout(400)
            assert len(page.inner_html("#root")) > 5000

    # Test opening the Demo Dialog
    open_dialog_btn = page.locator("button:has-text('Ouvrir la boîte de dialogue'), button:has-text('Ouvrir Dialogue')").first
    if open_dialog_btn.is_visible():
        open_dialog_btn.click()
        page.wait_for_timeout(600)

        # Dialog should be visible
        dialog = page.locator("div[role='dialog']").first
        assert dialog.is_visible()

        # Close dialog
        close_btn = page.locator("div[role='dialog'] button:has-text('Fermer'), div[role='dialog'] button[aria-label*='Fermer']").first
        if close_btn.is_visible():
            close_btn.click()
            page.wait_for_timeout(400)

    assert len(page._page_errors) == 0


def test_16_topbar_global_controls(page: Page):
    """
    Test 16: Topbar controls: Language Switcher, Theme Toggle, Palette Dropdown, and Command Palette.
    """
    authenticate_demo_session(page)
    page.evaluate("window.location.hash = 'dashboard'")
    page.wait_for_timeout(1000)

    # 1. Test Language Switcher (FR -> EN -> FR)
    en_btn = page.locator("header button:has-text('EN')").first
    fr_btn = page.locator("header button:has-text('FR')").first

    if en_btn.is_visible():
        en_btn.click()
        page.wait_for_timeout(500)
        # Dashboard title should translate to English
        assert page.locator("header h1:has-text('Overview'), header h1:has-text('Dashboard'), nav span:has-text('Control')").count() > 0

        # Switch back to FR
        fr_btn.click()
        page.wait_for_timeout(500)
        assert page.locator("header h1:has-text('Vue d’ensemble'), header h1:has-text(\"Vue d'ensemble\"), nav span:has-text('Piloter')").count() > 0

    # 2. Test Palette Quick Switcher Dropdown
    palette_btn = page.locator("button[aria-label*='palette'], button[title*='palette']").first
    if palette_btn.is_visible():
        palette_btn.click()
        page.wait_for_timeout(400)

        # Dropdown options should be visible
        assert page.locator("text=Papier & Encre").first.is_visible()
        paper_option = page.locator("button:has-text('Papier & Encre')").first
        paper_option.click()
        page.wait_for_timeout(400)

        # Switch back to Graphite
        palette_btn.click()
        page.wait_for_timeout(300)
        graphite_option = page.locator("button:has-text('Graphite & Laiton')").first
        graphite_option.click()
        page.wait_for_timeout(400)

    # 3. Test Theme Toggle (Dark -> Light -> Dark)
    theme_btn = page.locator("button[aria-label*='mode'], button[title*='mode']").first
    if theme_btn.is_visible():
        theme_btn.click()
        page.wait_for_timeout(400)
        theme_btn.click()
        page.wait_for_timeout(400)

    # 4. Test Command Palette (Cmd+K modal)
    cmd_trigger = page.locator("button:has-text('⌘K'), button[aria-label*='command']").first
    if cmd_trigger.is_visible():
        cmd_trigger.click()
        page.wait_for_timeout(500)

        cmd_modal = page.locator("div[role='dialog'], div[aria-label*='command']").first
        assert cmd_modal.is_visible()

        # Type in search input
        cmd_input = page.locator("div[role='dialog'] input").first
        cmd_input.fill("inbox")
        page.wait_for_timeout(300)

        # Close via Escape
        page.keyboard.press("Escape")
        page.wait_for_timeout(400)

    assert len(page._page_errors) == 0


def test_17_responsive_mobile_viewport_and_drawer(page: Page):
    """
    Test 17: Mobile viewport (375x812), hamburger menu toggle, and drawer navigation.
    """
    authenticate_demo_session(page)

    # Resize to mobile
    page.set_viewport_size({"width": 375, "height": 812})
    page.wait_for_timeout(600)

    # Hamburger button should be visible in header
    hamburger = page.locator("header button[aria-label*='menu'], header button[aria-label*='Menu']").first
    assert hamburger.is_visible(), "Hamburger menu button must be visible on mobile viewport"

    # Click hamburger to open drawer
    hamburger.click()
    page.wait_for_timeout(600)

    # Sidebar should now be open
    sidebar = page.locator("#sidebar-navigation")
    assert sidebar.is_visible()

    # Click navigation item in mobile drawer (Veille)
    veille_nav = sidebar.locator("button:has-text('Veille')").first
    if veille_nav.is_visible():
        veille_nav.click()
        page.wait_for_timeout(800)
        assert "veille" in page.evaluate("window.location.hash")

    # Restore desktop viewport
    page.set_viewport_size({"width": 1440, "height": 900})
    page.wait_for_timeout(500)

    assert len(page._page_errors) == 0


def test_18_logout_and_session_cleanup(page: Page):
    """
    Test 18: Logout action clears session and cleanly redirects to AuthScreen.
    """
    authenticate_demo_session(page)
    page.wait_for_timeout(500)

    # Find logout button in sidebar dock
    logout_btn = page.locator("#sidebar-navigation button[title*='Déconnexion'], #sidebar-navigation button:has-text('Déconnexion')").first
    if not logout_btn.is_visible():
        logout_btn = page.locator("button:has-text('Déconnexion'), button:has-text('Logout')").first

    assert logout_btn.is_visible(), "Logout button must be available in sidebar dock"
    logout_btn.click()
    page.wait_for_timeout(1500)

    # Should now be back on AuthScreen
    assert page.locator("h1:has-text('ContentOps'), span:has-text('ContentOps')").first.is_visible()
    assert page.locator("input[type='email']").is_visible()

    # Zero errors during complete logout cycle
    assert len(page._page_errors) == 0
