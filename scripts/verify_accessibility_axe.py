import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

AXE_SCRIPT_PATH = Path("apps/web/node_modules/axe-core/axe.min.js")
REPORT_PATH = Path("docs/ui/production/axe_report.json")

SCREENS = [
    ("auth", "0_auth"),
    ("dashboard", "1_dashboard"),
    ("inbox", "2_inbox"),
    ("calendar", "3_calendar"),
    ("ideation", "4_ideation"),
    ("insights", "5_insights"),
    ("brand", "6_brand"),
    ("connections", "7_connections"),
    ("settings", "8_settings"),
]

def run_axe_audit():
    print("=== DÉBUT DE L'AUDIT D'ACCESSIBILITÉ AVEC AXE-CORE (WCAG 2.2 AA) ===", flush=True)

    if not AXE_SCRIPT_PATH.exists():
        raise FileNotFoundError(f"axe.min.js introuvable à {AXE_SCRIPT_PATH}")

    with open(AXE_SCRIPT_PATH, "r", encoding="utf-8") as f:
        axe_script = f.read()

    audit_results = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "standard": "WCAG 2.2 AA",
        "screens_tested": [],
        "total_critical": 0,
        "total_serious": 0,
        "total_moderate": 0,
        "total_minor": 0,
        "details_by_screen": {},
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            headless=True
        )
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # 1. Screen: Auth
        print("\n--- Test d'accessibilité: Écran 0 (Auth) ---", flush=True)
        page.goto("http://127.0.0.1:8000/ui/", wait_until="networkidle")
        time.sleep(1)

        # Inject and run axe
        page.evaluate(axe_script)
        axe_res = page.evaluate("axe.run()")
        violations = axe_res.get("violations", [])

        crit = [v for v in violations if v["impact"] == "critical"]
        ser = [v for v in violations if v["impact"] == "serious"]
        mod = [v for v in violations if v["impact"] == "moderate"]
        minr = [v for v in violations if v["impact"] == "minor"]

        audit_results["screens_tested"].append("0_auth")
        audit_results["details_by_screen"]["0_auth"] = {
            "violations_count": len(violations),
            "critical": len(crit),
            "serious": len(ser),
            "moderate": len(mod),
            "minor": len(minr),
            "violations": violations,
        }
        print(f"   Résultat 0_auth : Critical={len(crit)}, Serious={len(ser)}, Moderate={len(mod)}, Minor={len(minr)}", flush=True)

        # Login to test application screens
        print("\nConnexion avec le rôle Owner...", flush=True)
        page.click("button[type='submit']")
        page.wait_for_selector("#main-content", timeout=10000)
        time.sleep(1)

        # 2. Test Remaining Screens
        for screen_id, file_prefix in SCREENS[1:]:
            print(f"\n--- Test d'accessibilité: #{screen_id} ({file_prefix}) ---", flush=True)
            page.evaluate(f"window.location.hash = '{screen_id}'")
            time.sleep(1)

            page.evaluate(axe_script)
            axe_res = page.evaluate("axe.run()")
            violations = axe_res.get("violations", [])

            crit = [v for v in violations if v["impact"] == "critical"]
            ser = [v for v in violations if v["impact"] == "serious"]
            mod = [v for v in violations if v["impact"] == "moderate"]
            minr = [v for v in violations if v["impact"] == "minor"]

            audit_results["screens_tested"].append(file_prefix)
            audit_results["total_critical"] += len(crit)
            audit_results["total_serious"] += len(ser)
            audit_results["total_moderate"] += len(mod)
            audit_results["total_minor"] += len(minr)

            audit_results["details_by_screen"][file_prefix] = {
                "violations_count": len(violations),
                "critical": len(crit),
                "serious": len(ser),
                "moderate": len(mod),
                "minor": len(minr),
                "violations": violations,
            }
            print(f"   Résultat {file_prefix} : Critical={len(crit)}, Serious={len(ser)}, Moderate={len(mod)}, Minor={len(minr)}", flush=True)

        context.close()
        browser.close()

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(audit_results, f, indent=2, ensure_ascii=False)

    print("\n=== SYNTHÈSE DE L'AUDIT AXE-CORE ===", flush=True)
    print(f"Écrans testés : {len(audit_results['screens_tested'])}", flush=True)
    print(f"Violations Critical : {audit_results['total_critical']}", flush=True)
    print(f"Violations Serious : {audit_results['total_serious']}", flush=True)
    print(f"Violations Moderate : {audit_results['total_moderate']}", flush=True)
    print(f"Violations Minor : {audit_results['total_minor']}", flush=True)
    print(f"Rapport sauvegardé dans {REPORT_PATH}", flush=True)

if __name__ == "__main__":
    run_axe_audit()
