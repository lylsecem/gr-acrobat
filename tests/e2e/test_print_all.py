# 合并打印 from Explorer's right-click menu in the real program: the selected PDFs go to the print window together,
# in the order Explorer lists them by name (whatever order they arrive in), without opening tabs; a protected one asks
# for its password, a damaged one is left out and named afterwards. Windows' own print window is not opened: the
# step that would open it is replaced, and what it would print is recorded.
import shutil, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright
from helpers import App, FIX, Report, display, out_dir

D = out_dir('print-all-files')
shutil.copy(FIX / 'locked.pdf', D / 'scan 1.pdf')       # 3 pages, password 1234
shutil.copy(FIX / 'landscape.pdf', D / 'scan 2.pdf')    # 2 pages
shutil.copy(FIX / 'broken.pdf', D / 'scan 3.pdf')       # cannot be read
shutil.copy(FIX / 'doc1.pdf', D / 'scan 10.pdf')        # 10 pages
r = Report()
check = r.check

with display(), sync_playwright() as pw:
    app = App('print-all')
    app.start()
    try:
        b, pg = app.page(pw)
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        ev = pg.evaluate
        pg.wait_for_function('typeof state === "object" && settingsSeen', timeout=30000)
        ev('() => { localStorage.setItem("ocrOffered", "1"); ocrCard({ title: "" }); closeOcrCard(); }')
        ev('''() => { window.runPrint = async () => {
                window.__printed = { label: $('#pdFile').textContent, pages: selectedPrintPages().map(p => [p.doc.numPages, p.num]),
                                     quality: $('#pdQuality').value, turn: $('#pdAutoRot').checked };
                $('#printDlg').hidden = true; }; }''')
        app.start('--printall', D / 'scan 10.pdf', D / 'scan 3.pdf', D / 'scan 2.pdf', D / 'scan 1.pdf')
        pg.wait_for_selector('#pwDlg:not([hidden])', timeout=30000)
        check('protected_one_asks', 'scan 1.pdf' in pg.text_content('#pwFile'), pg.text_content('#pwFile'))
        pg.fill('#pwInput', '1234'); pg.keyboard.press('Enter')
        pg.wait_for_function('!!window.__printed', timeout=30000)
        got = ev('window.__printed')
        check('in_name_order', got['pages'] == [[3, 1], [3, 2], [3, 3], [2, 1], [2, 2]] + [[10, n] for n in range(1, 11)], got['pages'])
        check('print_window_says_what', [got['label'], got['quality'], got['turn']] == ['合并打印 3 个文件 · 共 15 页', '200', True], got)
        pg.wait_for_selector('#msgDlg:not([hidden])', timeout=10000)
        check('damaged_one_named', [pg.text_content('#msgTitle'), 'scan 3.pdf' in pg.text_content('#msgText')] == ['有 1 个文件没有打印', True],
              [pg.text_content('#msgTitle'), pg.text_content('#msgText')])
        pg.click('#msgOk')
        check('no_tabs_opened', ev('docs.length') == 0, ev('docs.map(d => d.fileName)'))
        check('no_page_errors', not errs, errs)
        b.close()
    finally:
        app.stop()
r.finish()
