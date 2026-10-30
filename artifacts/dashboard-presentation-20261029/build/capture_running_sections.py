"""Capture the visible running dashboard in a separate read-only browser session."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent / 'running-dashboard-review'
OUT.mkdir(exist_ok=True)
captures = []
with sync_playwright() as p:
    browser = p.chromium.launch(channel='chrome', headless=True)
    page = browser.new_page(viewport={'width': 1600, 'height': 1100}, device_scale_factor=1)
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto('http://127.0.0.1:8501', wait_until='domcontentloaded')
    page.get_by_text('Source emitted', exact=True).first.wait_for(timeout=30000)
    page.wait_for_timeout(1200)
    page.screenshot(path=str(OUT / 'live-overview-top.png'))
    captures.append({'file': 'live-overview-top.png', 'section': 'Live Control Room', 'anchor': 'top'})
    sections = [
        (None, 'Ingest and processing throughput', 'live-overview-charts.png'),
        ('🎯 Metrics theo 10 tracks', 'Metrics across 10 tracks', 'live-metrics.png'),
        ('🛡️ Fraud & Business', 'Rule baseline vs Spark MLlib', 'live-business.png'),
        ('🔎 New data streams', 'Latest transactions processed by Spark', 'live-filters.png'),
    ]
    for nav, anchor, filename in sections:
        if nav:
            page.get_by_text(nav, exact=True).first.click(timeout=15000)
        target = page.get_by_text(anchor, exact=True).first
        target.wait_for(timeout=20000)
        if nav is None:
            page.get_by_text('Micro-batch duration & history', exact=True).first.wait_for(timeout=20000)
        page.wait_for_timeout(1000)
        target.evaluate('''el => {
          const scroller = document.querySelector('[data-testid="stMain"]');
          scroller.scrollTo({top: scroller.scrollTop + el.getBoundingClientRect().top - 125, behavior: 'instant'});
        }''')
        page.wait_for_timeout(500)
        page.screenshot(path=str(OUT / filename))
        captures.append({'file': filename, 'section': nav or 'Live Control Room',
                         'anchor': anchor, 'anchor_box': target.bounding_box()})
    (OUT / 'live-section-metadata.json').write_text(json.dumps({
        'source': 'Running dashboard at http://127.0.0.1:8501',
        'captured_local_date': '2026-10-29', 'viewport': [1600, 1100],
        'details': 'Each image is a momentary view of live values; screenshots were taken sequentially.',
        'captures': captures, 'browser_errors': errors,
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'captures': captures, 'browser_errors': errors}, ensure_ascii=True))
    browser.close()
