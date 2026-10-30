"""Browser checks for the original Framer artwork and CSS motion.

Default / --preview: isolated Streamlit with an in-memory saved snapshot.
--url: inspect an already-running dashboard. --html: inspect a standalone hero.
Never rebuilds containers or writes to the project database.
"""
import argparse
from contextlib import contextmanager
from io import BytesIO
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import time
import urllib.request

from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
target = parser.add_mutually_exclusive_group()
target.add_argument('--url', help='An already-running dashboard URL')
target.add_argument('--html', type=Path, help='A standalone hero HTML file')
target.add_argument('--preview', action='store_true', help='Use an isolated in-memory preview (default)')
parser.add_argument('--snapshot-file', type=Path, default=ROOT / 'docs/evidence/dashboard-ui/snapshot.json')
parser.add_argument('--port', type=int, default=8511)
parser.add_argument('--output', type=Path, default=ROOT / 'docs/evidence/dashboard-motion')
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)


@contextmanager
def preview_url():
    if args.url or args.html:
        yield args.url or args.html.resolve().as_uri()
        return
    # Refuse to inspect an unrelated server when the requested QA port is busy.
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', args.port))
    with tempfile.TemporaryDirectory(prefix='paysim-motion-qa-') as temporary:
        entry = Path(temporary) / 'preview.py'
        entry.write_text(
            'import sys\nfrom pathlib import Path\nimport mongomock\nfrom bson import json_util\n'
            f'sys.path.insert(0, {str(ROOT / "dashboard")!r})\nimport dashboard_core\n'
            f'saved = json_util.loads(Path({str(args.snapshot_file.resolve())!r}).read_text(encoding="utf-8"))\n'
            'db = mongomock.MongoClient(tz_aware=True).paysim\n'
            'for collection, documents in saved["collections"].items():\n'
            '    if documents: db[collection].insert_many(documents)\n'
            'dashboard_core.get_database = lambda: db\n'
            'import view_workspace as view\ndashboard_core.render(view)\n', encoding='utf-8')
        with open(Path(temporary) / 'preview.log', 'w', encoding='utf-8') as log:
            process = subprocess.Popen(
                [os.sys.executable, '-m', 'streamlit', 'run', str(entry), f'--server.port={args.port}',
                 '--server.address=127.0.0.1', '--server.headless=true',
                 '--browser.gatherUsageStats=false', '--theme.base=light'],
                stdout=log, stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            try:
                url = f'http://127.0.0.1:{args.port}'
                for _ in range(100):
                    try:
                        urllib.request.urlopen(url + '/_stcore/health', timeout=1).close()
                        break
                    except Exception:
                        if process.poll() is not None:
                            raise RuntimeError('Isolated Streamlit preview stopped')
                        time.sleep(.2)
                else:
                    raise RuntimeError('Isolated preview did not become ready')
                yield url
            finally:
                if process.poll() is None:
                    if os.name == 'nt':
                        # The Windows venv redirector owns a Python child. Stop
                        # this preview's tree so it cannot retain the log/port.
                        subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
                    else:
                        process.terminate()
                process.wait(timeout=15)


def changed_pixels(first, second):
    a, b = Image.open(BytesIO(first)).convert('RGB'), Image.open(BytesIO(second)).convert('RGB')
    return sum(max(pixel) > 8 for pixel in ImageChops.difference(a, b).getdata())


def artwork(page):
    frame = page if args.html else page.frame_locator('iframe[title="st.iframe"]').first
    expect(frame.locator('#nova-workspace')).to_be_visible(timeout=30000)
    return frame


with preview_url() as url, sync_playwright() as playwright:
    # No WebGL is needed: this is the original PNG + CSS, not a 3D replacement.
    browser = playwright.chromium.launch(channel='chrome', headless=True, args=['--disable-webgl'])
    page = browser.new_page(viewport={'width':1600, 'height':1100}, reduced_motion='no-preference')
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(url)
    hero = artwork(page)
    root = hero.locator('#nova-workspace')
    expect(root).to_have_attribute('data-renderer', 'image')
    expect(root).to_have_attribute('data-asset', 'ready')
    expect(root).to_have_attribute('data-motion', 'running')
    parameters = root.evaluate("""root => {
        const style = selector => {
            const s = getComputedStyle(root.querySelector(selector));
            return {name:s.animationName, duration:s.animationDuration,
                    easing:s.animationTimingFunction, direction:s.animationDirection,
                    iterations:s.animationIterationCount};
        };
        return {image:style('.fluidImage'), glow:style('.fluidGlow'), wave:style('.wave i'),
            bars:[...root.querySelectorAll('.wave i')].map(el=>({
                height:parseFloat(getComputedStyle(el).height),
                delay:parseFloat(getComputedStyle(el).animationDelay)})),
            cardAnimation:getComputedStyle(root.querySelector('.analysisCard')).animationName,
            imageSize:[root.querySelector('.fluidImage').naturalWidth,root.querySelector('.fluidImage').naturalHeight],
            keyframes:[...document.styleSheets[0].cssRules].filter(rule=>rule.type===7).map(rule=>rule.cssText)};
    }""")
    for name, duration, direction in [('image','10s','normal'), ('glow','8s','alternate'), ('wave','0.95s','alternate')]:
        assert parameters[name]['duration'] == duration, parameters
        assert parameters[name]['easing'] == 'ease-in-out', parameters
        assert parameters[name]['direction'] == direction, parameters
        assert parameters[name]['iterations'] == 'infinite', parameters
    assert parameters['imageSize'] == [1536,1024], parameters
    assert parameters['cardAnimation'] == 'none', parameters
    assert [bar['height'] for bar in parameters['bars']] == [8,15,23,13,27,18,10], parameters
    assert [bar['delay'] for bar in parameters['bars']] == [0,-.13,-.26,-.39,-.52,-.65,-.78], parameters
    # Crop clear artwork between the headline and static glass card. Neither
    # equalizer animation nor hover effects can satisfy this pixel check.
    page.wait_for_timeout(1200)
    before = root.screenshot()
    page.wait_for_timeout(1150)
    after = root.screenshot()
    def crop(payload):
        img = Image.open(BytesIO(payload))
        output = BytesIO()
        img.crop((int(img.width*.58),int(img.height*.10),int(img.width*.78),int(img.height*.90))).save(output,format='PNG')
        return output.getvalue()
    motion_pixels = changed_pixels(crop(before), crop(after))
    assert motion_pixels > 250, f'Artwork is stationary: {motion_pixels} changed pixels'
    (args.output/'hero-before.png').write_bytes(before)
    (args.output/'hero-after.png').write_bytes(after)
    root.evaluate("el => { el.dataset.mountProbe = 'same-scene'; }")
    page.wait_for_timeout(4600)
    expect(root).to_have_attribute('data-mount-probe', 'same-scene')
    page.screenshot(path=str(args.output/'desktop.png'))
    if not args.html:
        main = page.locator('[data-testid="stMain"]')
        main.evaluate('el => el.scrollTo(0, 900)')
        expect(root).to_have_attribute('data-motion', 'paused')
        main.evaluate('el => el.scrollTo(0, 0)')
        expect(root).to_have_attribute('data-motion', 'running')
    page.emulate_media(reduced_motion='reduce')
    expect(root).to_have_attribute('data-motion', 'reduced')
    page.wait_for_timeout(500)
    reduced_first = root.screenshot()
    page.wait_for_timeout(650)
    reduced_second = root.screenshot()
    still_pixels = changed_pixels(reduced_first, reduced_second)
    assert still_pixels == 0, f'Reduced motion still animates: {still_pixels} pixels'
    page.emulate_media(reduced_motion='no-preference')
    page.set_viewport_size({'width':390, 'height':844})
    page.wait_for_timeout(800)
    expect(hero.locator('.analysisCard')).to_be_visible()
    expect(hero.locator('.fluidImage')).to_be_visible()
    assert hero.locator('.analysisCard').evaluate('el=>el.getBoundingClientRect().bottom <= innerHeight')
    if not args.html:
        frame_box = page.locator('iframe[title="st.iframe"]').first.bounding_box()
        navigation_box = page.locator('[data-testid="stRadio"]').first.bounding_box()
        assert frame_box['height'] >= 485, frame_box
        assert navigation_box['y'] >= frame_box['y'] + frame_box['height'] - 2, 'Mobile artwork overlaps navigation'
    page.screenshot(path=str(args.output/'mobile.png'))
    assert not page.evaluate('document.documentElement.scrollWidth > innerWidth')
    assert not errors, errors
    browser.close()

result = dict(source='isolated in-memory pipeline replay' if not (args.url or args.html) else url,
              idle_changed_pixels=motion_pixels, reduced_motion_changed_pixels=still_pixels,
              survives_data_refresh=not bool(args.html), mobile_artwork_visible=True,
              pauses_offscreen=not bool(args.html),
              webgl_required=False, browser_errors=errors, animation_parameters=parameters)
(args.output/'results.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result))
