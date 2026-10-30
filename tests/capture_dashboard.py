"""Browser QA: real MongoDB by default, or replay a saved snapshot in memory.

Never writes to the real database. Snapshot replay uses mongomock only.
"""
import argparse
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
import urllib.request

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--views', nargs='+', default=['baseline', 'workspace'], choices=['baseline', 'workspace'])
parser.add_argument('--snapshot-file', type=Path, help='Replay a saved pipeline JSON in memory, without MongoDB writes')
parser.add_argument('--port', type=int, default=8510)
parser.add_argument('--chrome', type=str, help='Optional path to an installed Chromium/Chrome executable')
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
report = []
navigation = {
    'baseline': ['📡 Live Control Room', '🎯 Metrics theo 10 tracks', '🛡️ Fraud & Business', '🔎 Dòng dữ liệu mới'],
    'workspace': ['Overview', 'Pipeline metrics', 'Fraud & business', 'Transactions'],
}
canonical = ['Source emitted', 'Spark processed', 'Fraud alerts', 'Current ingest', 'Processing throughput', 'End-to-end latency p95']
baseline_metric_labels = {
    'Nguồn đã phát': 'Source emitted', 'Spark đã xử lý': 'Spark processed', 'Ingest hiện tại': 'Current ingest',
}
content_markers = {
    'baseline': ['Tốc độ ingest và xử lý', '01. Ingestion', 'Rule baseline vs Spark MLlib', 'Giao dịch vừa đi qua Spark'],
    'workspace': ['Ingest and processing throughput', 'Metrics across 10 tracks', 'Rule baseline vs Spark MLlib', 'Latest transactions processed by Spark'],
}
source = 'saved real pipeline snapshot replayed in memory' if args.snapshot_file else 'MongoDB read-only live snapshot'
with tempfile.TemporaryDirectory(prefix='paysim-workspace-qa-') as tmp, sync_playwright() as playwright:
    options = dict(headless=True)
    if args.chrome:
        options['executable_path'] = args.chrome
    elif os.name == 'nt':
        options['channel'] = 'chrome'
    browser = playwright.chromium.launch(**options)
    for view in args.views:
        # Refuse an occupied port instead of accidentally testing another app.
        with socket.socket() as port_check:
            port_check.bind(('127.0.0.1', args.port))
        labels = navigation[view]
        first_metric = 'Nguồn đã phát' if view == 'baseline' else 'Source emitted'
        entry = Path(tmp) / f'{view}.py'
        code = f'import sys\nsys.path.insert(0, {str(ROOT / "dashboard")!r})\nimport dashboard_core\n'
        if args.snapshot_file:
            code += (
                'from pathlib import Path\nimport mongomock\nfrom bson import json_util\n'
                f'saved = json_util.loads(Path({str(args.snapshot_file.resolve())!r}).read_text(encoding="utf-8"))\n'
                'db = mongomock.MongoClient(tz_aware=True).paysim\n'
                'for collection, documents in saved["collections"].items():\n'
                '    if documents: db[collection].insert_many(documents)\n'
                'dashboard_core.get_database = lambda: db\n'
            )
        code += 'dashboard_core.render()\n' if view == 'baseline' else 'import view_workspace as view\ndashboard_core.render(view)\n'
        entry.write_text(code, encoding='utf-8')
        log = open(Path(tmp) / f'{view}.log', 'w', encoding='utf-8')
        process = subprocess.Popen(
            [os.sys.executable, '-m', 'streamlit', 'run', str(entry), f'--server.port={args.port}',
             '--server.address=127.0.0.1', '--server.headless=true', '--browser.gatherUsageStats=false', '--theme.base=light'],
            env={**os.environ, 'MONGO_URI': os.environ.get('MONGO_URI', 'mongodb://127.0.0.1:27017')},
            stdout=log, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
        )
        try:
            for attempt in range(100):
                try:
                    urllib.request.urlopen(f'http://127.0.0.1:{args.port}/_stcore/health', timeout=1)
                    break
                except Exception:
                    if process.poll() is not None:
                        raise RuntimeError('Streamlit stopped before health check passed')
                    time.sleep(.2)
            else:
                raise RuntimeError('Streamlit did not become healthy')
            page = browser.new_page(viewport={'width': 1600, 'height': 1100}, device_scale_factor=1)
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(f'http://127.0.0.1:{args.port}')
            page.get_by_text(first_metric, exact=True).first.wait_for(timeout=30000)
            for index, label in enumerate(labels):
                radio = page.get_by_role('radio', name=label, exact=True)
                radio.locator('xpath=ancestor::label').click()
                expect(radio).to_be_checked(timeout=15000)
                expected = content_markers[view][index]
                page.get_by_text(expected, exact=True).first.wait_for(timeout=15000)
                page.wait_for_timeout(600)
                assert page.locator('[data-testid="stException"]').count() == 0
                # One DOM read avoids racing the 2-second fragment refresh.
                rows = page.locator('[data-testid="stMetric"]').evaluate_all('elements => elements.map(el => ({name: el.querySelector("[data-testid=stMetricLabel]")?.innerText.trim(), value: el.querySelector("[data-testid=stMetricValue]")?.innerText.trim()}))')
                metrics = {}
                for row in rows:
                    name = baseline_metric_labels.get(row['name'], row['name'])
                    if name in canonical and name not in metrics:
                        metrics[name] = row['value']
                assert set(metrics) == set(canonical), metrics
                screenshot = f'{view}-{index + 1}-desktop.png'
                page.screenshot(path=str(args.output / screenshot), full_page=True)
                overflow = page.evaluate('document.documentElement.scrollWidth > window.innerWidth')
                report.append(dict(view=view, page=label, page_id=index, metrics=metrics, browser_errors=list(errors),
                                   horizontal_overflow=overflow, screenshot=screenshot))
            if view == 'workspace':
                search = page.get_by_role('textbox', name='Search Event ID', exact=True)
                search.fill('no-such-event-for-browser-qa')
                search.press('Enter')
                page.get_by_text('No matching records. Try broader criteria or reset the filters.', exact=True).wait_for()
                page.get_by_role('button', name='Reset filters', exact=False).click()
                expect(search).to_have_value('')
                assert page.locator('[data-testid="stException"]').count() == 0
            page.set_viewport_size({'width': 390, 'height': 844})
            page.reload()
            page.get_by_text(first_metric, exact=True).first.wait_for(timeout=20000)
            collapse = page.locator('[data-testid="stSidebar"][aria-expanded="true"] [data-testid="stSidebarCollapseButton"] button')
            if collapse.count() and collapse.is_visible():
                collapse.click()
            for index in (0, 3):
                radio = page.get_by_role('radio', name=labels[index], exact=True)
                radio.locator('xpath=ancestor::label').click()
                expect(radio).to_be_checked()
                page.wait_for_timeout(600)
                assert page.locator('[data-testid="stException"]').count() == 0
                overflow = page.evaluate('document.documentElement.scrollWidth > window.innerWidth')
                screenshot = f'{view}-{index + 1}-mobile.png'
                page.screenshot(path=str(args.output / screenshot), full_page=True)
                report.append(dict(view=view, page=labels[index], page_id=index, mobile=True, horizontal_overflow=overflow,
                                   browser_errors=list(errors), screenshot=screenshot))
            page.close()
        finally:
            try:
                if process.poll() is None:
                    if os.name == 'nt':
                        # A Windows venv launcher has a Python child. Stop this
                        # owned process tree so the child cannot retain the log
                        # or preview port after the launcher exits.
                        subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
                    else:
                        process.terminate()
                process.wait(timeout=15)
            finally:
                log.close()
    browser.close()
desktop = [row for row in report if not row.get('mobile')]
baseline = {row['page_id']: row['metrics'] for row in desktop if row['view'] == 'baseline'}
for row in desktop:
    if row['view'] == 'workspace' and row['page_id'] in baseline:
        assert row['metrics'] == baseline[row['page_id']], row
payload = dict(source=source, snapshot_file=str(args.snapshot_file) if args.snapshot_file else None,
               desktop_pages=len(desktop), results=report)
(args.output / 'browser-results.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'Captured {len(desktop)} desktop pages and {len(report) - len(desktop)} mobile views. Source: {source}')
