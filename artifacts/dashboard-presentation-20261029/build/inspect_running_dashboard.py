"""Read the dashboard through a separate browser session without modifying the pipeline."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright

output = Path(__file__).resolve().parent / 'running-dashboard-review'
output.mkdir(exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=True)
    page = browser.new_page(viewport={'width': 1600, 'height': 1100}, device_scale_factor=1)
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto('http://127.0.0.1:8501', wait_until='domcontentloaded', timeout=15000)
    page.locator('[data-testid="stAppViewContainer"]').wait_for(timeout=30000)
    page.get_by_role('radio').first.wait_for(state='attached', timeout=30000)
    page.wait_for_timeout(1500)
    radios = page.get_by_role('radio')
    names = radios.evaluate_all('(nodes) => nodes.map(e => e.closest("label")?.innerText.trim() || e.getAttribute("aria-label") || "")')
    results = []
    for i, name in enumerate(names):
        page.get_by_role('radio').nth(i).locator('xpath=ancestor::label').click()
        page.wait_for_timeout(1300)
        content = page.locator('body').inner_text(timeout=15000)
        page.screenshot(path=str(output / f'live-page-{i+1}.png'))
        results.append({'index': i + 1, 'label': name, 'text': content[:12000],
                        'exceptions': page.locator('[data-testid="stException"]').count()})
    summary = {'url': 'http://127.0.0.1:8501', 'pages': results, 'browser_errors': errors}
    (output / 'running-review.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=True, indent=2))
    browser.close()
