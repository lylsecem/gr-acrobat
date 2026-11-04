# The top bar's 打印 button, Ctrl+O and the print window in the real program (up to the system print window,
# which is not opened); screenshots in the light and the dark theme.
import shutil, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright
from helpers import App, FIX, Report, display, out_dir

D = out_dir('print-files')
SHOTS = out_dir('print-shots')
shutil.copy(FIX / 'doc1.pdf', D / 'report.pdf')
shutil.copy(FIX / 'img' / 'photo.jpg', D / 'photo.jpg')
r = Report()
check = r.check

with display(), sync_playwright() as pw:
    app = App('print')
    app.start()
    try:
        b, pg = app.page(pw)
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        ev = pg.evaluate
        pg.wait_for_function('typeof state === "object" && document.querySelector("#stageEmpty")', timeout=30000)
        pg.wait_for_timeout(500)
        ev('() => { localStorage.setItem("ocrOffered", "1"); document.querySelector("#ocrCard").hidden = true; }')
        check('nothing_to_print_yet', ev('[document.querySelector("#printBtn").disabled, document.querySelector("#docTabs").hidden, getComputedStyle(document.querySelector("#stageEmpty")).display]') == [True, True, 'flex'],
              ev('[document.querySelector("#printBtn").disabled, document.querySelector("#docTabs").hidden, getComputedStyle(document.querySelector("#stageEmpty")).display]'))
        pg.keyboard.press('Control+p'); pg.wait_for_timeout(200)
        check('ctrl_p_without_a_file_does_nothing', ev('document.querySelector("#printDlg").hidden'))
        for theme in ('light', 'dark'):
            pg.emulate_media(color_scheme=theme); pg.wait_for_timeout(200)
            pg.screenshot(path=str(SHOTS / f'{theme}-1-empty.png'))
        pg.emulate_media(color_scheme='light')

        # Ctrl+O and 打开文件 open the file picker (stood in for here: the system window is not opened)
        ev('() => { window.__picks = 0; document.querySelector("#openInput").click = () => { __picks++; }; }')
        pg.keyboard.press('Control+o'); pg.click('#emptyOpen')
        check('ctrl_o_and_button_open_the_picker', ev('__picks') == 2, ev('__picks'))

        app.start(D / 'report.pdf')
        pg.wait_for_function('state.pdfDoc && document.querySelector("#pageCanvas").width > 0', timeout=30000)
        pg.click('.doc-tab-add')
        check('plus_on_the_tab_bar_opens_the_picker', ev('__picks') == 3, ev('__picks'))
        check('print_button_ready', not ev('document.querySelector("#printBtn").disabled'))
        pg.click('#printBtn'); pg.wait_for_selector('#printDlg:not([hidden])')
        check('print_window_names_the_file', [pg.text_content('#pdFile'), pg.text_content('#pdSecond')] == ['report.pdf · 共 10 页', '当前页（第 1 页）'],
              [pg.text_content('#pdFile'), pg.text_content('#pdSecond')])
        for theme in ('light', 'dark'):
            pg.emulate_media(color_scheme=theme); pg.wait_for_timeout(200)
            pg.screenshot(path=str(SHOTS / f'{theme}-2-print.png'))
        pg.emulate_media(color_scheme='light')
        pg.check('input[name=pdRange][value=custom]'); pg.fill('#pdCustom', '0,99'); pg.click('#pdGo'); pg.wait_for_timeout(300)
        check('bad_range_explained', pg.text_content('#pdProgress') == '请输入有效的页码，例如 1-3,5', pg.text_content('#pdProgress'))
        pg.fill('#pdCustom', '7,2-4')
        check('range_in_order', ev('selectedPrintPages().map(p => p.num)') == [2, 3, 4, 7], ev('selectedPrintPages().map(p => p.num)'))
        pg.click('#pdCancel')
        check('cancel_closes', ev('document.querySelector("#printDlg").hidden'))
        ev('renderMainPage(4)'); pg.wait_for_timeout(300)
        pg.keyboard.press('Control+p'); pg.wait_for_selector('#printDlg:not([hidden])')
        pg.check('input[name=pdRange][value=second]')
        check('current_page', [pg.text_content('#pdSecond'), ev('selectedPrintPages().map(p => p.num)')] == ['当前页（第 4 页）', [4]],
              [pg.text_content('#pdSecond'), ev('selectedPrintPages().map(p => p.num)')])
        pg.click('#pdCancel')
        pg.click('.thumb >> nth=2', button='right'); pg.wait_for_timeout(150)
        pg.click('.ctx .ctx-item:has-text("打印第 3 页")'); pg.wait_for_selector('#printDlg:not([hidden])')
        check('thumb_menu_prints_that_page', ev('selectedPrintPages().map(p => p.num)') == [3], ev('selectedPrintPages().map(p => p.num)'))
        pg.click('#pdCancel')

        # a picture prints as one page
        app.start(D / 'photo.jpg')
        pg.wait_for_function('state.fileName === "photo.jpg" && document.querySelector("#pageCanvas").width > 0', timeout=30000)
        pg.keyboard.press('Control+p'); pg.wait_for_selector('#printDlg:not([hidden])')
        check('picture_prints_as_one_page', pg.text_content('#pdFile') == 'photo.jpg · 共 1 页', pg.text_content('#pdFile'))
        pg.click('#pdCancel')

        # 合并拆分 prints the board: nothing on it, nothing to print; the selected pages as the second choice
        pg.click('.tab-btn[data-mode=merge]'); pg.wait_for_timeout(300)
        check('empty_board_nothing_to_print', ev('document.querySelector("#printBtn").disabled'))
        pg.click('.tab-btn[data-mode=view]'); pg.click('.doc-tab >> nth=0'); pg.wait_for_function('state.fileName === "report.pdf"')
        pg.click('.tab-btn[data-mode=merge]'); pg.wait_for_timeout(300)
        ev('() => { $("#orgAddCurrent").click(); }'); pg.wait_for_function('org.pages.length === 10', timeout=20000)
        ev('orgExpand([...org.collapsed])'); pg.wait_for_timeout(400)
        pg.click('.ptile:not(.pstack) >> nth=1'); pg.click('.ptile:not(.pstack) >> nth=2', modifiers=['Shift'])
        check('board_can_print', not ev('document.querySelector("#printBtn").disabled'))
        pg.click('#printBtn'); pg.wait_for_selector('#printDlg:not([hidden])')
        pg.check('input[name=pdRange][value=second]')
        check('selected_pages_print', [pg.text_content('#pdSecond'), ev('selectedPrintPages().map(p => p.num)')] == ['所选页面（2 页）', [2, 3]],
              [pg.text_content('#pdSecond'), ev('selectedPrintPages().map(p => p.num)')])
        pg.screenshot(path=str(SHOTS / 'light-3-merge-print.png'))
        pg.click('#pdCancel')
        for theme in ('light', 'dark'):
            pg.emulate_media(color_scheme=theme); pg.wait_for_timeout(200)
            pg.screenshot(path=str(SHOTS / f'{theme}-4-merge.png'))
        check('no_page_errors', not errs, errs)
        b.close()
    finally:
        app.stop()
r.finish()
