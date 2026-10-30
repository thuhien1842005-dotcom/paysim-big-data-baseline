from pathlib import Path
import json
from playwright.sync_api import sync_playwright
BUILD=Path(__file__).resolve().parent
OUT=BUILD.parent/'output'
QA=BUILD/'qa'
QA.mkdir(exist_ok=True)
errors=[]
with sync_playwright() as p:
    browser=p.chromium.launch(channel='chrome',headless=True)
    page=browser.new_page(viewport={'width':1500,'height':1050},device_scale_factor=1)
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto((OUT/'Thuyet_trinh_toi_uu_dashboard_PaySim.html').as_uri())
    page.wait_for_function('Array.from(document.images).every(i=>i.complete && i.naturalWidth>0)')
    report={'images':page.locator('img').count(),'slides':page.locator('article').count(),'views':[]}
    for i in range(8):
        stage=page.locator('article').nth(i).locator('.stage')
        stage.screenshot(path=str(QA/f'slide-{i+1}.png'))
        result=page.locator('article').nth(i).locator('.canvas').evaluate('''el=>{const c=el.getBoundingClientRect();const f=el.querySelector('.slidefoot').getBoundingClientRect();const text=[...el.querySelectorAll('.summary,.flow,.comparison-visual,.newvisual,.two-shots,.pair')].map(e=>({type:e.className,top:e.getBoundingClientRect().top-c.top,bottom:e.getBoundingClientRect().bottom-c.top}));return {scrollHeight:el.scrollHeight,height:el.clientHeight,footerTop:f.top-c.top,footerBottom:f.bottom-c.top,text}}''')
        report['views'].append({'slide':i+1,**result})
    page.get_by_role('button',name='Trình chiếu',exact=True).click()
    assert page.locator('body').evaluate("e=>e.classList.contains('deck')")
    assert page.locator('article:visible').count()==1
    page.keyboard.press('End')
    assert page.locator('.counter').inner_text()=='8 / 8'
    page.keyboard.press('ArrowLeft')
    assert page.locator('.counter').inner_text()=='7 / 8'
    page.keyboard.press('Home')
    assert page.locator('.counter').inner_text()=='1 / 8'
    page.locator('article.active .imageview').first.click()
    assert page.locator('.modal.open').count()==1
    page.keyboard.press('Escape')
    assert page.locator('.modal.open').count()==0
    page.keyboard.press('s')
    assert not page.locator('body').evaluate("e=>e.classList.contains('deck')")
    report['controls']='slide mode, Home/End, arrows, image zoom, Escape and S passed'
    page.set_viewport_size({'width':390,'height':844})
    report['mobile_horizontal_overflow']=page.evaluate('document.documentElement.scrollWidth>innerWidth')
    report['errors']=errors
    page.screenshot(path=str(QA/'script-mobile.png'))
    browser.close()
(QA/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
