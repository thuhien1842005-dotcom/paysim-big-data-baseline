"""Exercise editing, reload persistence, export and presentation controls in isolation."""
from pathlib import Path
import sys
from playwright.sync_api import sync_playwright

BUILD = Path(__file__).resolve().parent
PRESENTATION = BUILD.parent / 'output' / 'Thuyet_trinh_toi_uu_dashboard_PaySim.html'
QA = BUILD / 'qa'
QA.mkdir(exist_ok=True)

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(channel=sys.argv[1] if len(sys.argv) > 1 else 'chrome', headless=True)
    context = browser.new_context(viewport={'width': 1400, 'height': 1100}, accept_downloads=True)
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(PRESENTATION.as_uri())
    assert page.locator('article').count() == 8
    assert page.locator('article img').count() == 11
    # Simulate notes saved by the previous HTML before the new paragraphs were added.
    old_groups = page.evaluate('''() => [...document.querySelectorAll('article .notes')].map(section =>
        [...section.querySelectorAll('.spoken:not(.running-comparison-extra)')].map(p => p.innerHTML))''')
    old_groups[0][1] += ' [existing-user-edit]'
    page.evaluate('''groups => localStorage.setItem('paysim-presenter-notes-v1:' + location.pathname,
        JSON.stringify({version: 1, groups}))''', old_groups)
    page.reload()
    assert '[existing-user-edit]' in page.locator('article').first.locator('.spoken').nth(1).inner_text()
    assert page.locator('.running-comparison-extra').count() == 8
    first = page.locator('article').first
    first.get_by_role('button', name='Sửa lời thoại').click()
    paragraph = first.locator('.spoken').nth(1)
    assert paragraph.get_attribute('contenteditable') == 'true'
    paragraph.click()
    page.keyboard.type('sf')
    edited = paragraph.inner_text()
    assert 'sf' in edited
    assert not page.locator('body').evaluate("e => e.classList.contains('deck')")
    assert 'Đã tự lưu' in first.locator('.save-state').inner_text()
    page.reload()
    first = page.locator('article').first
    assert first.locator('.spoken').nth(1).inner_text() == edited
    assert 'Đã khôi phục' in first.locator('.save-state').inner_text()
    first.get_by_role('button', name='Sửa lời thoại').click()
    first.get_by_role('button', name='Xong', exact=True).click()
    assert first.locator('.spoken').nth(1).get_attribute('contenteditable') is None
    with page.expect_download() as download_info:
        first.get_by_role('button', name='Tải bản HTML đã sửa').click()
    downloaded = QA / 'downloaded-presentation.html'
    download_info.value.save_as(downloaded)
    page.get_by_role('button', name='Trình chiếu', exact=True).click()
    page.keyboard.press('End')
    assert page.locator('.counter').inner_text() == '8 / 8'
    page.keyboard.press('s')
    assert not page.locator('body').evaluate("e => e.classList.contains('deck')")
    page.locator('article').first.locator('.notes').screenshot(path=str(QA / 'inline-edit-notes.png'))
    new_context = browser.new_context(viewport={'width': 1400, 'height': 1100})
    exported = new_context.new_page()
    exported.goto(downloaded.as_uri())
    assert exported.locator('article img').count() == 11
    assert exported.locator('article').first.locator('.spoken').nth(1).inner_text() == edited
    assert exported.get_by_role('button', name='Sửa lời thoại').count() == 8
    assert not errors, errors
    print('Previous edits preserved; direct editing, restore, shortcuts and downloaded copy: passed.')
    new_context.close()
    context.close()
    browser.close()
