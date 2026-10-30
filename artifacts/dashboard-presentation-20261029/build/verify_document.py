from pathlib import Path
import json
from playwright.sync_api import sync_playwright
B=Path(__file__).resolve().parent
path=B.parent/'output/Thuyet_trinh_toi_uu_dashboard_PaySim.html'
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    page=browser.new_page(viewport={'width':1400,'height':1100},device_scale_factor=1)
    page.goto(path.as_uri())
    page.wait_for_function('Array.from(document.images).every(i=>i.complete)')
    page.locator('article').nth(5).locator('.notes').screenshot(path=str(B/'qa/notes-slide-6.png'))
    page.locator('#comparison').screenshot(path=str(B/'qa/appendix.png'))
    assert page.locator('article .notes .spoken').count()==24
    assert page.locator('#comparison > table').nth(0).locator('tbody tr').count()==10
    assert page.locator('#questions ~ .qa').count()==5
    script_stats=page.evaluate('''()=>({externalImages:[...document.images].filter(i=>!i.src.startsWith('data:')).length,externalScripts:document.querySelectorAll('script[src]').length,brokenImages:[...document.images].filter(i=>!i.naturalWidth).length})''')
    browser.close()
print(json.dumps(script_stats))
