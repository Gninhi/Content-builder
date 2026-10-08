import json
from pathlib import Path
from playwright.sync_api import sync_playwright

OUTPUT_DIR = Path("docs/ui/baseline")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

VIEWPORTS = [
    {"name": "375px", "width": 375, "height": 812},
    {"name": "768px", "width": 768, "height": 1024},
    {"name": "1440px", "width": 1440, "height": 900},
]

TABS = [
    ("dashboard", "nav-dashboard"),
    ("inbox", "nav-inbox"),
    ("calendar", "nav-calendar"),
    ("ideation", "nav-ideation"),
    ("insights", "nav-insights"),
    ("brand", "nav-brand"),
]

def run_preflight_capture():
    print("=== DEBUT DE LA CAPTURE BASELINE AVEC PLAYWRIGHT ===")
    results = {
        "console_errors": [],
        "console_warnings": [],
        "failed_requests": [],
        "csp_violations": [],
        "screenshots": [],
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            headless=True
        )

        for vp in VIEWPORTS:
            w = vp["width"]
            h = vp["height"]
            print(f"\n--- Capture pour viewport: {vp['name']} ({w}x{h}) ---")
            
            context = browser.new_context(viewport={"width": w, "height": h})
            page = context.new_page()

            # Listen to events
            def on_console(msg):
                text = msg.text
                if "Content-Security-Policy" in text or "violates" in text.lower() or "blocked" in text.lower():
                    results["csp_violations"].append({"viewport": vp["name"], "text": text})
                if msg.type == "error":
                    results["console_errors"].append({"viewport": vp["name"], "text": text})
                elif msg.type == "warning":
                    results["console_warnings"].append({"viewport": vp["name"], "text": text})

            def on_response(response):
                if response.status >= 400:
                    results["failed_requests"].append({
                        "viewport": vp["name"],
                        "url": response.url,
                        "status": response.status,
                        "status_text": response.status_text,
                    })

            page.on("console", on_console)
            page.on("response", on_response)

            page.goto("http://127.0.0.1:8000/ui/")
            page.wait_for_timeout(1500)

            # Capture each tab
            for tab_name, nav_id in TABS:
                try:
                    page.evaluate(f"window.switchTab && window.switchTab('{tab_name}')")
                    page.wait_for_timeout(500)
                except Exception as e:
                    print(f"Error switching to {tab_name}: {e}")

                screenshot_path = OUTPUT_DIR / f"{tab_name}_{w}px.png"
                page.screenshot(path=str(screenshot_path), full_page=True)
                results["screenshots"].append(str(screenshot_path))
                print(f"  Capture enregistrée : {screenshot_path}")

            # Capture research modal
            try:
                page.evaluate("window.triggerQuickResearchModal && window.triggerQuickResearchModal()")
                page.wait_for_timeout(500)
                modal_screenshot = OUTPUT_DIR / f"modal_research_{w}px.png"
                page.screenshot(path=str(modal_screenshot), full_page=False)
                results["screenshots"].append(str(modal_screenshot))
                print(f"  Capture modale enregistrée : {modal_screenshot}")
            except Exception as e:
                print(f"Error opening modal: {e}")

            context.close()

        browser.close()

    # Save summary report in JSON
    report_path = OUTPUT_DIR / "preflight_data.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nDonnées de capture brutes enregistrées dans {report_path}")
    print(f"Total erreurs console distinctes : {len(results['console_errors'])}")
    print(f"Total requêtes réseau en échec : {len(results['failed_requests'])}")
    print(f"Total violations CSP relevées : {len(results['csp_violations'])}")
    print(f"Total captures d'écran générées : {len(results['screenshots'])}")

if __name__ == "__main__":
    run_preflight_capture()
