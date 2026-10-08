import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

OUTPUT_DIR = Path("docs/ui/production")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

VIEWPORTS = [
    {"name": "375px", "width": 375, "height": 812},
    {"name": "768px", "width": 768, "height": 1024},
    {"name": "1440px", "width": 1440, "height": 900},
]

SCREENS = [
    ("dashboard", "1_dashboard"),
    ("inbox", "2_inbox"),
    ("calendar", "3_calendar"),
    ("ideation", "4_ideation"),
    ("insights", "5_insights"),
    ("brand", "6_brand"),
    ("connections", "7_connections"),
    ("settings", "8_settings"),
]

def run_production_verification():
    print("=== DÉBUT DE LA VÉRIFICATION PRODUCTION READY AVEC PLAYWRIGHT ===")
    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "viewports_tested": [v["name"] for v in VIEWPORTS],
        "console_errors": [],
        "console_warnings": [],
        "failed_requests": [],
        "csp_violations": [],
        "screenshots": [],
        "interactions_tested": [],
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            headless=True
        )

        for vp in VIEWPORTS:
            w = vp["width"]
            h = vp["height"]
            vp_name = vp["name"]
            print(f"\n--- Vérification pour Viewport : {vp_name} ({w}x{h}) ---")

            context = browser.new_context(viewport={"width": w, "height": h})
            page = context.new_page()

            # Event listeners
            def on_console(msg):
                text = msg.text
                if "Content-Security-Policy" in text or "violates" in text.lower() or "blocked" in text.lower():
                    report["csp_violations"].append({"viewport": vp_name, "text": text})
                if msg.type == "error":
                    # Ignore favicon 404 or benign hydration if any
                    report["console_errors"].append({"viewport": vp_name, "text": text})
                elif msg.type == "warning":
                    report["console_warnings"].append({"viewport": vp_name, "text": text})

            def on_response(response):
                # Monitor failures (ignore intentional 404 test if any)
                if response.status >= 400:
                    report["failed_requests"].append({
                        "viewport": vp_name,
                        "url": response.url,
                        "status": response.status
                    })

            page.on("console", on_console)
            page.on("response", on_response)

            # 1. Screen 0: Auth
            print("1. Accès à /ui/ (Écran d'authentification)...")
            page.goto("http://127.0.0.1:8000/ui/", wait_until="networkidle")
            time.sleep(1)

            auth_shot = OUTPUT_DIR / f"0_auth_{vp_name}.png"
            page.screenshot(path=str(auth_shot), full_page=True)
            report["screenshots"].append(str(auth_shot))
            print(f"   -> Capture sauvegardée : {auth_shot}")

            # Submit Dev Login Form
            print("2. Connexion avec le rôle Owner...")
            page.click("button[type='submit']")
            page.wait_for_selector("#main-content", timeout=10000)
            time.sleep(1)

            # 2. Iterate through all screens
            for screen_id, file_prefix in SCREENS:
                print(f"3. Navigation vers #{screen_id}...")
                page.evaluate(f"window.location.hash = '{screen_id}'")
                time.sleep(1)

                shot_path = OUTPUT_DIR / f"{file_prefix}_{vp_name}.png"
                page.screenshot(path=str(shot_path), full_page=True)
                report["screenshots"].append(str(shot_path))
                print(f"   -> Capture sauvegardée : {shot_path}")

                # If on Ideation screen, open modal and capture
                if screen_id == "ideation":
                    print("   -> Ouverture de la vraie modale d'idéation...")
                    new_btn = page.query_selector("button:has-text('Lancer une Idéation')")
                    if new_btn:
                        new_btn.click()
                        time.sleep(0.5)
                        modal_shot = OUTPUT_DIR / f"4_ideation_modal_{vp_name}.png"
                        page.screenshot(path=str(modal_shot), full_page=True)
                        report["screenshots"].append(str(modal_shot))
                        # Close modal with Esc key (A11y test)
                        page.keyboard.press("Escape")
                        time.sleep(0.5)
                        report["interactions_tested"].append("Modal accessible closed via Escape key")

            # 3. Test responsive mobile drawer on 375px
            if w <= 768:
                print("4. Test du menu mobile responsive...", flush=True)
                menu_btn = page.query_selector("button[aria-label='Ouvrir le menu']")
                if menu_btn:
                    menu_btn.click()
                    time.sleep(0.5)
                    drawer_shot = OUTPUT_DIR / f"sidebar_mobile_open_{vp_name}.png"
                    page.screenshot(path=str(drawer_shot))
                    report["screenshots"].append(str(drawer_shot))
                    # Click on the right edge (w - 20px) which is outside the 288px sidebar
                    page.mouse.click(w - 20, 200)
                    time.sleep(0.5)
                    report["interactions_tested"].append("Mobile Drawer opened and closed via backdrop click")

            # 4. Test Theme Toggle
            print("5. Test de bascule de thème clair/sombre...")
            theme_btn = page.query_selector("button[aria-label*='mode']")
            if theme_btn:
                theme_btn.click()
                time.sleep(0.5)
                light_shot = OUTPUT_DIR / f"theme_light_{vp_name}.png"
                page.screenshot(path=str(light_shot))
                report["screenshots"].append(str(light_shot))
                theme_btn.click() # restore dark
                time.sleep(0.5)
                report["interactions_tested"].append("Dark/Light Theme toggle tested")

            # 5. Test Language Switch
            print("6. Test de bascule de langue FR/EN...")
            en_btn = page.query_selector("button[aria-label='Switch to English']")
            if en_btn:
                en_btn.click()
                time.sleep(0.5)
                en_shot = OUTPUT_DIR / f"lang_en_{vp_name}.png"
                page.screenshot(path=str(en_shot))
                report["screenshots"].append(str(en_shot))
                fr_btn = page.query_selector("button[aria-label='Passer en français']")
                if fr_btn:
                    fr_btn.click() # restore FR
                    time.sleep(0.5)
                report["interactions_tested"].append("Bilingual FR/EN toggle tested")

            context.close()

        browser.close()

    # Save summary report
    report_file = Path("docs/ui/production/verification_report.json")
    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print("\n=== RAPPORT DE VÉRIFICATION TERMINÉ ===")
    print(f"Total Captures : {len(report['screenshots'])}")
    print(f"Erreurs Console : {len(report['console_errors'])}")
    print(f"Violations CSP : {len(report['csp_violations'])}")
    print(f"Requêtes Échouées : {len(report['failed_requests'])}")
    print(f"Rapport sauvegardé dans {report_file}")

if __name__ == "__main__":
    run_production_verification()
