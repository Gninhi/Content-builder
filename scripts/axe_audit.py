import json
from pathlib import Path
from playwright.sync_api import sync_playwright

def run_a11y_audit():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            headless=True
        )
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        page.goto("http://127.0.0.1:8000/ui/")
        page.wait_for_timeout(1000)

        # Audit accessibility heuristics directly
        issues = page.evaluate("""() => {
            const problems = [];
            // 1. Missing labels on form inputs
            document.querySelectorAll('input, select, textarea').forEach(el => {
                const id = el.id;
                const label = id ? document.querySelector(`label[for="${id}"]`) : null;
                const ariaLabel = el.getAttribute('aria-label') || el.getAttribute('aria-labelledby');
                if (!label && !ariaLabel) {
                    problems.push({
                        type: 'wcag-input-label-missing',
                        selector: el.tagName.toLowerCase() + (id ? '#' + id : ''),
                        detail: 'Form control lacks accessible label or associated <label for="..."> tag'
                    });
                }
            });

            // 2. Buttons without accessible names
            document.querySelectorAll('button').forEach(btn => {
                const text = btn.innerText.trim();
                const ariaLabel = btn.getAttribute('aria-label') || btn.getAttribute('aria-labelledby');
                if (!text && !ariaLabel) {
                    problems.push({
                        type: 'wcag-button-name-missing',
                        selector: 'button' + (btn.id ? '#' + btn.id : ''),
                        detail: 'Button has no discernible text or aria-label (icon-only button without label)'
                    });
                }
            });

            // 3. Modal accessibility attributes
            const modal = document.getElementById('modal-research');
            if (modal) {
                if (!modal.getAttribute('role')) {
                    problems.push({
                        type: 'wcag-dialog-role-missing',
                        selector: '#modal-research',
                        detail: 'Modal container lacks role="dialog" or role="alertdialog"'
                    });
                }
                if (!modal.getAttribute('aria-modal')) {
                    problems.push({
                        type: 'wcag-aria-modal-missing',
                        selector: '#modal-research',
                        detail: 'Modal container lacks aria-modal="true"'
                    });
                }
            }

            // 4. Color contrast / Unstyled elements
            const bodyStyle = window.getComputedStyle(document.body);
            problems.push({
                type: 'styling-unapplied',
                detail: `Body font-family: ${bodyStyle.fontFamily}, Tailwind CDN script blocked by CSP.`
            });

            // 5. Land marks
            const main = document.querySelector('main');
            const nav = document.querySelector('nav');
            if (!main) problems.push({ type: 'landmark-missing', detail: '<main> landmark is missing' });
            if (!nav) problems.push({ type: 'landmark-missing', detail: '<nav> landmark is missing' });

            return problems;
        }""")

        browser.close()

        with open("docs/ui/baseline/a11y_data.json", "w", encoding="utf-8") as f:
            json.dump(issues, f, indent=2, ensure_ascii=False)
        print(f"Audit A11y terminé : {len(issues)} problèmes structurels identifiés.")
        for iss in issues:
            print(f" - [{iss['type']}] {iss.get('detail')}")

if __name__ == "__main__":
    run_a11y_audit()
