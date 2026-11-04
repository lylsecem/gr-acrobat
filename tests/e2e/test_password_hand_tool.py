# Password-protected PDFs in the real program: a wrong password asked again, cancelling, Chinese / Thai passwords,
# a PDF that only limits printing, pages saved from them without the password (through GRAcrobatUnlock.exe or its
# stand-in), a large one read in pieces asking once; and the hand tool: dragging a zoomed page with the left button.
import shutil, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright
from helpers import App, CATCH_DOWNLOADS, FIX, Report, display, out_dir, pdf_info, take_download

D = out_dir('password-files')
for f in (FIX / 'pw').glob('*.pdf'):
    shutil.copy(f, D / f.name)
shutil.copy(FIX / 'doc1.pdf', D / 'doc1.pdf')
OUT = out_dir('password-saved')
r = Report()
check = r.check

with display(), sync_playwright() as pw:
    app = App('password')
    app.start(D / 'pw_aes256.pdf')
    try:
        b, pg = app.page(pw)
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        ev = pg.evaluate
        ev('() => { localStorage.setItem("ocrOffered", "1"); }')
        ev('() => { window.__asks = 0; const ask = askPassword; askPassword = (...a) => { __asks++; return ask(...a); }; }')
        pg.wait_for_selector('#pwDlg:not([hidden])', timeout=30000)
        check('asks_for_the_password', pg.text_content('#pwFile') == 'pw_aes256.pdf', pg.text_content('#pwFile'))
        pg.fill('#pwInput', 'wrong'); pg.keyboard.press('Enter')
        pg.wait_for_function('document.querySelector("#pwMsg").textContent !== ""', timeout=15000)
        check('wrong_password_asked_again', [ev('!document.querySelector("#pwDlg").hidden'), pg.text_content('#pwMsg')] == [True, '密码不对，请重新输入。'],
              [ev('!document.querySelector("#pwDlg").hidden'), pg.text_content('#pwMsg')])
        pg.fill('#pwInput', '1234'); pg.keyboard.press('Enter')
        pg.wait_for_function('state.fileName === "pw_aes256.pdf" && document.querySelector("#pageCanvas").width > 0', timeout=30000)
        check('opens_with_the_right_password', ev('[state.numPages, document.querySelector("#pwDlg").hidden]') == [3, True], ev('[state.numPages, document.querySelector("#pwDlg").hidden]'))

        # cancelling the question opens nothing and leaves the open documents as they were
        app.start(D / 'pw_aes128.pdf')
        pg.wait_for_selector('#pwDlg:not([hidden])', timeout=30000)
        pg.click('#pwCancel'); pg.wait_for_timeout(500)
        check('cancel_keeps_document', ev('[state.fileName, docs.length, document.querySelector("#msgDlg").hidden]') == ['pw_aes256.pdf', 1, True],
              ev('[state.fileName, docs.length, document.querySelector("#msgDlg").hidden]'))

        for name, password in [('pw_utf8.pdf', '密码ไทย1'), ('pw_rc4_40.pdf', '1234'), ('pw_rc4_128.pdf', '1234')]:
            app.start(D / name)
            pg.wait_for_selector('#pwDlg:not([hidden])', timeout=30000)
            pg.fill('#pwInput', password); pg.keyboard.press('Enter')
            pg.wait_for_function('state.fileName === %r && document.querySelector("#pageCanvas").width > 0' % name, timeout=30000)
            check(f'opens_{name[:-4]}', ev('state.numPages') == 3, ev('state.numPages'))

        # only printing and copying limited: no password asked
        asks = ev('__asks')
        app.start(D / 'pw_owner_only.pdf')
        pg.wait_for_function('state.fileName === "pw_owner_only.pdf" && document.querySelector("#pageCanvas").width > 0', timeout=30000)
        check('owner_only_needs_no_password', ev('__asks') == asks, ev('__asks'))

        # pages saved from protected PDFs carry no password
        ev(CATCH_DOWNLOADS)
        for name in ('pw_owner_only.pdf', 'pw_utf8.pdf', 'pw_aes256.pdf'):
            pg.click(f'.doc-tab:has-text("{name}") .doc-tab-name'); pg.wait_for_function('state.fileName === %r' % name)
            ev('() => { exportPagesAsPdf([2]); }')
            saved = take_download(pg, OUT / f'{name}-page2.pdf')
            info = pdf_info(OUT / f'{name}-page2.pdf')
            check(f'page_export_unprotected_{name[:-4]}', info[:2] == (False, 1) and '密码保护测试 2' in info[2], [saved, *info])
        ev('() => { exportPagesAsImages([1], { fmt: "png", scale: 1 }); }')
        pg.wait_for_selector('#askDlg:not([hidden])', timeout=30000); pg.click('#askActions button:has-text("知道了")')
        check('picture_from_protected_pdf', (D / 'pw_aes256_第1页.png').stat().st_size > 5000 if (D / 'pw_aes256_第1页.png').exists() else False)
        pg.click('.tab-btn[data-mode=merge]'); pg.wait_for_timeout(300)
        ev('() => { $("#orgAddCurrent").click(); }')
        pg.wait_for_function('org.pages.length === 3', timeout=20000)
        pg.click('.tab-btn[data-mode=view]')
        pg.click('.doc-tab:has-text("pw_rc4_40.pdf") .doc-tab-name'); pg.wait_for_function('state.fileName === "pw_rc4_40.pdf"')
        pg.click('.tab-btn[data-mode=merge]'); pg.wait_for_timeout(300)
        ev('() => { $("#orgAddCurrent").click(); }')
        pg.wait_for_function('org.pages.length === 6', timeout=20000)
        ev('() => { orgExport(false); }')
        saved = take_download(pg, OUT / 'merge.pdf')
        info = pdf_info(OUT / 'merge.pdf')
        check('merge_export_unprotected', info[:2] == (False, 6) and (OUT / 'merge.pdf').read_bytes().count(b'/Encrypt') == 0, [saved, *info])
        pg.click('.tab-btn[data-mode=view]'); pg.wait_for_timeout(300)

        # a large protected file is read in pieces, and its password asked once
        asks = ev('__asks')
        app.start(D / 'pw_big.pdf')
        pg.wait_for_selector('#pwDlg:not([hidden])', timeout=30000)
        pg.fill('#pwInput', '1234'); pg.keyboard.press('Enter')
        pg.wait_for_function('state.fileName === "pw_big.pdf" && document.querySelector("#pageCanvas").width > 0', timeout=60000)
        pg.wait_for_timeout(1000)
        check('big_file_asks_once', [ev('__asks') - asks, ev('state.numPages')] == [1, 8], [ev('__asks') - asks, ev('state.numPages')])

        # ---- hand tool: a page larger than the view follows the left button
        pg.click('.doc-tab >> nth=0'); pg.wait_for_function('state.fileName === "pw_aes256.pdf"')
        for _ in range(8):
            pg.click('#zoomIn')
        pg.wait_for_timeout(800)
        box = pg.locator('#stage').bounding_box()
        cx, cy = box['x'] + box['width'] / 2, box['y'] + box['height'] / 2
        ev('document.querySelector("#stage").scrollTo(300, 300)'); pg.wait_for_timeout(100)
        pg.mouse.move(cx, cy); pg.mouse.move(cx + 2, cy + 2)
        check('hand_cursor_over_a_large_page', ev('document.querySelector("#stage").classList.contains("can-pan")'))
        before = ev('[document.querySelector("#stage").scrollLeft, document.querySelector("#stage").scrollTop]')
        pg.mouse.down(); pg.mouse.move(cx - 150, cy - 100, steps=8)
        grabbing = ev('document.querySelector("#stage").classList.contains("panning")')
        pg.mouse.up()
        after = ev('[document.querySelector("#stage").scrollLeft, document.querySelector("#stage").scrollTop]')
        check('drag_moves_the_page', grabbing and abs(after[0] - before[0] - 152) <= 3 and abs(after[1] - before[1] - 102) <= 3, [before, after, grabbing])
        pg.click('#zoomPage'); pg.wait_for_timeout(500)
        pg.mouse.move(cx, cy); pg.mouse.move(cx + 3, cy + 3)
        check('no_hand_when_the_page_fits', not ev('document.querySelector("#stage").classList.contains("can-pan")'))
        check('no_page_errors', not errs, errs)
        b.close()
    finally:
        app.stop()
r.finish()
