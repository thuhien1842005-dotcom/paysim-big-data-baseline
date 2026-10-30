"""Capture real dashboard UI using an isolated saved-snapshot replay only."""
from pathlib import Path
import json
import os
import socket
import subprocess
import sys
import time
import signal
import urllib.request
from bson import json_util
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[3]
BUILD = Path(__file__).resolve().parent
OUT = BUILD / 'captures'
OUT.mkdir(parents=True, exist_ok=True)
PORT = 8527
SNAPSHOT = ROOT / 'docs/evidence/dashboard-ui/snapshot.json'
saved = json_util.loads(SNAPSHOT.read_text(encoding='utf-8'))
rows = saved['collections']['recent_transactions']
chosen = next((r for r in rows if str(r.get('event_id','')).endswith('0000004201')), rows[0])
chosen_id = str(chosen['event_id'])
ENTRY = BUILD / 'snapshot_workspace.py'
ENTRY.write_text(
    f'import sys\nsys.path.insert(0, {str(ROOT / "dashboard")!r})\n'
    'import dashboard_core\nfrom pathlib import Path\nimport os\nimport mongomock\nfrom bson import json_util\n'
    f'Path({str(OUT / "owned-server.pid")!r}).write_text(str(os.getpid()))\n'
    f'saved=json_util.loads(Path({str(SNAPSHOT)!r}).read_text(encoding="utf-8"))\n'
    'db=mongomock.MongoClient(tz_aware=True).paysim\n'
    'for name, docs in saved["collections"].items():\n'
    '    if docs: db[name].insert_many(docs)\n'
    'dashboard_core.get_database=lambda:db\n'
    'import view_workspace as view\ndashboard_core.render(view)\n', encoding='utf-8')

with socket.socket() as sock:
    sock.bind(('127.0.0.1', PORT))
log = (OUT / 'streamlit.log').open('w', encoding='utf-8')
proc = subprocess.Popen(
    [sys.executable, '-m', 'streamlit', 'run', str(ENTRY), f'--server.port={PORT}',
     '--server.address=127.0.0.1', '--server.headless=true', '--browser.gatherUsageStats=false', '--theme.base=light'],
    stdout=log, stderr=subprocess.STDOUT,
    creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
report = {'source':'saved real pipeline snapshot replayed in isolated mongomock memory',
          'snapshot_file':str(SNAPSHOT.relative_to(ROOT)), 'snapshot_run_id':saved['run_id'],
          'captured_snapshot_at':str(saved['captured_at']),
          'viewport':{'width':1600,'height':1100}, 'port':PORT,
          'chosen_event_id':chosen_id, 'source_database_writes':False,
          'docker_restarts':False,
          'current_navigation_labels':['📡 Live Control Room','🎯 Metrics theo 10 tracks','🛡️ Fraud & Business','🔎 New data streams'],
          'evidence_note':'Current source navigation and hero wording differ from saved dashboard-english images; no source files modified.',
          'captures':[]}

try:
    for i in range(100):
        try:
            urllib.request.urlopen(f'http://127.0.0.1:{PORT}/_stcore/health',timeout=1)
            break
        except Exception:
            if proc.poll() is not None: raise RuntimeError('Streamlit exited before readiness')
            time.sleep(.2)
    else: raise RuntimeError('Streamlit not ready')
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel='chrome',headless=True)
        page = browser.new_page(viewport=report['viewport'],device_scale_factor=1)
        errors=[]
        page.on('pageerror',lambda err:errors.append(str(err)))
        page.goto(f'http://127.0.0.1:{PORT}')
        page.get_by_text('Source emitted',exact=True).first.wait_for(timeout=30000)

        def nav(label, marker):
            if label != 'Overview':
                actual={'Pipeline metrics':'🎯 Metrics theo 10 tracks','Fraud & business':'🛡️ Fraud & Business','Transactions':'🔎 New data streams'}[label]
                page.get_by_text(actual,exact=True).first.click()
            page.get_by_text(marker,exact=True).first.wait_for(timeout=15000)
            page.wait_for_timeout(300)

        def capture(filename, anchor, actions):
            target=page.get_by_text(anchor,exact=True).first
            target.evaluate('''(el)=>{
                const scroller=document.querySelector('[data-testid="stMain"]');
                scroller.style.scrollBehavior='auto';
                scroller.scrollTo({top:scroller.scrollTop+el.getBoundingClientRect().top-120,behavior:'instant'});
            }''')
            page.wait_for_timeout(400)
            assert page.locator('[data-testid="stException"]').count()==0
            path=OUT/filename
            page.screenshot(path=str(path),full_page=False)
            report['captures'].append({'file':filename,'anchor':anchor,'actions':actions,
                'anchor_box':target.bounding_box(),
                'main_scroll_top':page.locator('[data-testid="stMain"]').evaluate('(el)=>el.scrollTop'),
                'browser_errors':list(errors),'horizontal_page_overflow':page.evaluate('document.documentElement.scrollWidth>window.innerWidth')})

        nav('Overview','Ingest and processing throughput')
        page.get_by_text('Micro-batch duration & history',exact=True).first.wait_for(timeout=30000)
        page.wait_for_timeout(1200)
        capture('workspace-overview-charts.png','Ingest and processing throughput',['Overview','scroll below hero and run KPI cards','Chart window remains 60 micro-batches; snapshot contains 10 batches'])

        nav('Pipeline metrics','Metrics across 10 tracks')
        capture('workspace-metrics-default.png','Metrics across 10 tracks',['Pipeline metrics','scroll below hero and run KPI cards','default 01 and 06 groups open'])
        for label in ['Ingestion','Fraud Detection']:
            item=page.locator('[data-testid="stExpander"] summary').filter(has_text=label).first
            item.click()
            page.wait_for_timeout(300)
        capture('workspace-metrics-groups.png','Metrics across 10 tracks',['Pipeline metrics','collapse default-open groups 01 and 06','scroll to metrics heading'])

        nav('Fraud & business','Rule baseline vs Spark MLlib')
        capture('workspace-business-comparison.png','Rule baseline vs Spark MLlib',['Fraud & business','scroll below hero and KPI cards','existing saved model/rule evaluations unchanged'])

        nav('Transactions','Latest transactions processed by Spark')
        capture('workspace-transactions-filters.png','Latest transactions processed by Spark',['Transactions','scroll below decorative hero','all 60 loaded transactions, default filters'])
        search=page.get_by_role('textbox',name='Search Event ID',exact=True)
        search.fill(chosen_id)
        search.press('Enter')
        page.get_by_text('Showing 1/60 loaded transactions · up to 60 records · searches this snapshot only.',exact=True).wait_for(timeout=15000)
        select=page.get_by_role('combobox',name='Select transaction by Event ID',exact=True)
        select.click()
        page.get_by_role('option',name=chosen_id,exact=True).click()
        page.get_by_text('Transaction details',exact=True).first.wait_for(timeout=15000)
        capture('workspace-transaction-result-and-details.png','Showing 1/60 loaded transactions · up to 60 records · searches this snapshot only.',
                ['Transactions',f'search actual snapshot Event ID {chosen_id}','select matching existing Event ID from selector','scroll to result count, table, CSV button and selected inspector'])
        capture('workspace-transaction-inspector.png','Selected transaction',
                ['Transactions',f'actual selected Event ID {chosen_id}','scroll to selected transaction inspector','CSV button is earlier in the page; result-and-details capture shows it'])
        report['browser_errors']=errors
        browser.close()
finally:
    try:
        if proc.poll() is None:
            pid_file=OUT/'owned-server.pid'
            if pid_file.exists():
                try:os.kill(int(pid_file.read_text()),signal.SIGTERM)
                except ProcessLookupError:pass
            else:proc.terminate()
        proc.wait(timeout=15)
    finally:
        log.close()
        (OUT/'capture-metadata.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'captures':len(report['captures']),'chosen_event_id':chosen_id,'output':str(OUT),'browser_errors':report.get('browser_errors',[])},ensure_ascii=False))
