import asyncio
from playwright.async_api import async_playwright

async def audit_all_buttons():
    print("=== DÉBUT DE L'AUDIT COMPLET DES BOUTONS ET COMPOSANTS ===")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            headless=True
        )
        context = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await context.new_page()

        console_logs = []
        network_errors = []

        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
        page.on("requestfailed", lambda req: network_errors.append(f"FAILED: {req.method} {req.url} - {req.failure}"))
        page.on("response", lambda res: network_errors.append(f"HTTP {res.status}: {res.request.method} {res.url}") if res.status >= 400 else None)

        # 1. Login
        print("\n--- 1. Écran 0 : Authentification ---")
        await page.goto("http://127.0.0.1:8000/ui/")
        await page.wait_for_selector("text=ContentOps Harness")
        
        # Test Role buttons
        role_buttons = await page.locator("button[role='radio']").all()
        print(f"Boutons de rôle trouvés : {len(role_buttons)}")
        for r_btn in role_buttons:
            txt = await r_btn.inner_text()
            print(f"  -> Clic sur le rôle : {txt}")
            await r_btn.click()
            await page.wait_for_timeout(200)

        # Click Owner and Submit
        owner_btn = page.locator("button[role='radio']:has-text('Owner')")
        await owner_btn.click()
        submit_btn = page.locator("button[type='submit']")
        await submit_btn.click()
        await page.wait_for_selector("text=Vue d'ensemble", timeout=5000)
        print("  -> Connexion Owner réussie !")

        screens = [
            ("dashboard", "#dashboard"),
            ("inbox", "#inbox"),
            ("calendar", "#calendar"),
            ("ideation", "#ideation"),
            ("insights", "#insights"),
            ("brand", "#brand"),
            ("connections", "#connections"),
            ("settings", "#settings"),
        ]

        button_audit_results = {}

        for screen_name, screen_hash in screens:
            print(f"\n--- Audit de l'écran : {screen_name} ({screen_hash}) ---")
            await page.goto(f"http://127.0.0.1:8000/ui/{screen_hash}")
            await page.wait_for_timeout(1000)

            buttons = await page.locator("button").all()
            print(f"Boutons trouvés sur {screen_name} : {len(buttons)}")
            
            screen_btns = []
            for idx, btn in enumerate(buttons):
                is_visible = await btn.is_visible()
                is_enabled = await btn.is_enabled()
                btn_text = (await btn.inner_text()).strip().replace("\n", " ")
                aria_label = await btn.get_attribute("aria-label") or ""
                btn_desc = btn_text or aria_label or f"IconBtn_{idx}"
                
                screen_btns.append({
                    "index": idx,
                    "description": btn_desc,
                    "visible": is_visible,
                    "enabled": is_enabled
                })
                print(f"  [{idx}] '{btn_desc}' - Visible: {is_visible}, Enabled: {is_enabled}")

            button_audit_results[screen_name] = screen_btns

        print("\n=== SYNTHÈSE DES ERREURS CONSOLE / RÉSEAU DÉTECTÉES ===")
        print(f"Erreurs console : {len(console_logs)}")
        for log in console_logs:
            if "error" in log.lower() or "warn" in log.lower():
                print("  Console:", log)

        print(f"Requêtes réseau en échec : {len(network_errors)}")
        for err in network_errors:
            print("  Network:", err)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(audit_all_buttons())
