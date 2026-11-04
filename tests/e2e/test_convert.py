# 转换 in the real program: pictures to one PDF (Windows' save window at once, file name order, page sizes, opening
# the result, a cancelled window, a damaged picture) and a PDF to pictures (the window asking format, resolution,
# pages and folder; several pages in a new folder, one page directly; a password-protected PDF), both from the two
# boxes and from Explorer's right-click menu. Windows' save and folder windows are answered by GR_TEST_DIALOGS.
import json, shutil, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image
from playwright.sync_api import sync_playwright
from pypdf import PdfReader
from helpers import App, CATCH_DOWNLOADS, FIX, Report, display, out_dir, take_download

D = out_dir('convert-files')
OUT = D / 'out'
OUT.mkdir()
shutil.copy(FIX / 'doc1.pdf', D / 'report.pdf')
shutil.copy(FIX / 'locked.pdf', D / 'locked.pdf')
shutil.copy(FIX / 'img' / 'bad.png', D / 'bad.png')
# three pictures of different sizes, named so that only a number-aware order puts them right
Image.new('RGB', (300, 200), (200, 40, 40)).save(D / 'scan 1.jpg')
Image.new('RGB', (200, 300), (40, 160, 40)).save(D / 'scan 2.png')
Image.new('RGB', (250, 250), (40, 40, 200)).save(D / 'scan 10.png')
PICS = [D / 'scan 10.png', D / 'scan 1.jpg', D / 'scan 2.png']
ANSWERS = D / 'dialogs.json'
r = Report()
check = r.check


def answer(save=None, folder=None):
    """What Windows' save window (a PDF path) and folder window give next; None: the person cancelled."""
    ANSWERS.write_text(json.dumps({'save': str(save) if save else None, 'folder': str(folder) if folder else None}))


def page_sizes(path):
    return [(round(float(p.mediabox.width)), round(float(p.mediabox.height))) for p in PdfReader(str(path)).pages]


answer()
with display(), sync_playwright() as pw:
    app = App('convert', env={'GR_TEST_DIALOGS': str(ANSWERS)})
    app.start()
    try:
        b, pg = app.page(pw)
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        ev = pg.evaluate
        pg.wait_for_function('typeof state === "object" && settingsSeen', timeout=30000)
        ev('() => { localStorage.setItem("ocrOffered", "1"); ocrCard({ title: "" }); closeOcrCard(); }')
        ask = lambda: [pg.text_content('#askTitle'), pg.text_content('#askText'), ev('[...document.querySelectorAll("#askActions button")].map(b => b.textContent)')]
        press = lambda label: ev('(l) => { [...document.querySelectorAll("#askActions button")].find(b => b.textContent === l).click(); }', label)

        # ---- one 转换 in the side bar instead of 转图片 and 图片转 PDF
        nav = ev('[...document.querySelectorAll(".tab-btn:not([hidden])")].map(b => b.textContent.trim())')
        check('side_bar', nav == ['查看', '转换', '合并拆分'], nav)
        pg.click('.tab-btn[data-mode=convert]'); pg.wait_for_timeout(300)
        check('two_boxes', [pg.text_content('#screenTitle'), pg.text_content('#cvImgZone .cv-title'), pg.text_content('#cvPdfZone .cv-title')] == ['转换', '图片转 PDF', 'PDF 转图片'],
              [pg.text_content('#screenTitle'), pg.text_content('#cvImgZone .cv-title'), pg.text_content('#cvPdfZone .cv-title')])

        # ---- pictures to a PDF, from Explorer's 用 GR Acrobat 转为 PDF: the save window, then the PDF
        answer(save=OUT / 'scans.pdf')
        app.start('--img2pdf', *PICS)
        pg.wait_for_selector('#askDlg:not([hidden])', timeout=30000)
        info = ask()
        check('pdf_made_where_chosen', info == ['已生成 PDF', f'共 3 页，保存为：{OUT / "scans.pdf"}', ['打开', '打开文件夹', '知道了']], info)
        check('pictures_in_file_name_order', page_sizes(OUT / 'scans.pdf') == [(300, 200), (200, 300), (250, 250)], page_sizes(OUT / 'scans.pdf'))
        press('打开')
        pg.wait_for_function('state.fileName === "scans.pdf" && document.querySelector("#pageCanvas").width > 0', timeout=30000)
        check('result_opens', ev('[state.mode, state.numPages, docs.length]') == ['view', 3, 1], ev('[state.mode, state.numPages, docs.length]'))

        # A4 lying, chosen on the screen; and a file picked in the save window is replaced (the window asked)
        (OUT / 'old.pdf').write_text('an older file')
        pg.click('.tab-btn[data-mode=convert]'); pg.select_option('#pageSizeSel', 'a4l')
        answer(save=OUT / 'old.pdf')
        app.start('--img2pdf', D / 'scan 1.jpg')
        pg.wait_for_selector('#askDlg:not([hidden])', timeout=30000); press('知道了')
        check('a4_and_replaced_as_asked', page_sizes(OUT / 'old.pdf') == [(842, 595)], page_sizes(OUT / 'old.pdf'))
        pg.select_option('#pageSizeSel', 'auto')

        # the save window cancelled: nothing made
        answer(save=None)
        before = sorted(p.name for p in OUT.iterdir())
        app.start('--img2pdf', *PICS); pg.wait_for_timeout(2500)
        check('cancelled_makes_nothing', sorted(p.name for p in OUT.iterdir()) == before and ev('document.querySelector("#askDlg").hidden'), sorted(p.name for p in OUT.iterdir()))

        # a damaged picture: told, nothing made
        answer(save=OUT / 'bad.pdf')
        app.start('--img2pdf', D / 'scan 1.jpg', D / 'bad.png')
        pg.wait_for_selector('#msgDlg:not([hidden])', timeout=30000)
        check('damaged_picture_told', [pg.text_content('#msgTitle'), 'bad.png' in pg.text_content('#msgText'), (OUT / 'bad.pdf').exists()] == ['转换没有完成', True, False],
              [pg.text_content('#msgTitle'), pg.text_content('#msgText'), (OUT / 'bad.pdf').exists()])
        pg.click('#msgOk')
        bad = ev('window.electronAPI.writePdf(%r, new Uint8Array([1]))' % str(OUT / 'not-chosen.pdf'))
        check('writes_only_where_chosen', bool(bad.get('error')) and not (OUT / 'not-chosen.pdf').exists(), bad)

        # ---- a PDF to pictures, from Explorer's 转为图片: the window asks first
        app.start('--pdf2img', D / 'report.pdf')
        pg.wait_for_selector('#cvDlg:not([hidden])', timeout=30000)
        check('window_asks', [pg.text_content('#cvFile'), pg.text_content('#cvDir'), pg.text_content('#cvNote'), ev('document.querySelector("#cvDirGroup").hidden')] ==
              ['report.pdf · 共 10 页', str(D), '选了多页时，会在这里新建「report_图片」文件夹。', False],
              [pg.text_content('#cvFile'), pg.text_content('#cvDir'), pg.text_content('#cvNote')])
        pg.select_option('#cvFormat', 'jpeg'); pg.select_option('#cvScale', '1'); pg.fill('#cvCustom', '2-3')
        pg.click('#cvGo')
        pg.wait_for_selector('#askDlg:not([hidden])', timeout=60000)
        info = ask(); press('知道了')
        folder = D / 'report_图片'
        files = sorted(p.name for p in folder.iterdir()) if folder.exists() else []
        check('several_pages_in_a_new_folder', info[:2] == ['已导出 2 张图片', f'保存在新建的文件夹里：{folder}'] and files == ['report_第2页.jpg', 'report_第3页.jpg'], [info, files])
        size = Image.open(folder / 'report_第2页.jpg').size if files else None
        check('jpeg_at_1x', size in [(595, 841), (595, 842)], size)
        check('no_zip_made', not list(D.rglob('*.zip')))

        # one page, into a folder picked in the folder window
        picked = D / 'picked'
        picked.mkdir()
        app.start('--pdf2img', D / 'report.pdf')
        pg.wait_for_selector('#cvDlg:not([hidden])', timeout=30000)
        answer(folder=picked)
        pg.click('#cvDirPick'); pg.wait_for_function('document.querySelector("#cvDir").textContent === %r' % str(picked), timeout=10000)
        check('window_keeps_the_last_choices', [ev('$("#cvFormat").value'), ev('$("#cvScale").value')] == ['jpeg', '1'], [ev('$("#cvFormat").value'), ev('$("#cvScale").value')])
        pg.select_option('#cvFormat', 'png'); pg.select_option('#cvScale', '2')
        pg.fill('#cvCustom', '5'); pg.click('#cvGo')
        pg.wait_for_selector('#askDlg:not([hidden])', timeout=60000)
        info = ask(); press('知道了')
        check('one_page_straight_into_the_picked_folder', info[1] == f'保存为：{picked / "report_第5页.png"}' and Image.open(picked / 'report_第5页.png').size in [(1190, 1683), (1190, 1684)], info)

        # a bad range is explained; 取消 converts nothing
        app.start('--pdf2img', D / 'report.pdf')
        pg.wait_for_selector('#cvDlg:not([hidden])', timeout=30000)
        pg.fill('#cvCustom', '0,99'); pg.click('#cvGo'); pg.wait_for_timeout(300)
        check('bad_range_explained', pg.text_content('#cvProgress') == '请输入有效的页码，例如 1-3,5', pg.text_content('#cvProgress'))
        pg.click('#cvCancel'); pg.wait_for_timeout(300)
        check('cancel_converts_nothing', ev('document.querySelector("#cvDlg").hidden') and not (D / 'report_图片 (2)').exists())

        # a password-protected PDF: asked once, all pages saved
        app.start('--pdf2img', D / 'locked.pdf')
        pg.wait_for_selector('#pwDlg:not([hidden])', timeout=30000)
        pg.fill('#pwInput', '1234'); pg.keyboard.press('Enter')
        pg.wait_for_selector('#cvDlg:not([hidden])', timeout=30000)
        pg.select_option('#cvFormat', 'png'); pg.select_option('#cvScale', '1'); pg.click('#cvGo')
        pg.wait_for_selector('#askDlg:not([hidden])', timeout=60000); press('知道了')
        files = sorted(p.name for p in (D / 'locked_图片').iterdir()) if (D / 'locked_图片').exists() else []
        check('protected_pdf_to_pictures', files == ['locked_第1页.png', 'locked_第2页.png', 'locked_第3页.png'], files)

        # ---- the two boxes (files handed over without their place on disk: the results are downloaded)
        ev(CATCH_DOWNLOADS)
        pg.set_input_files('#cvImgInput', [str(p) for p in PICS])
        name = take_download(pg, D / 'boxed.pdf')
        check('left_box_makes_a_pdf', [name, page_sizes(D / 'boxed.pdf')] == ['scan 1.pdf', [(300, 200), (200, 300), (250, 250)]], [name, page_sizes(D / 'boxed.pdf')])
        pg.set_input_files('#cvPdfInput', str(D / 'report.pdf'))
        pg.wait_for_selector('#cvDlg:not([hidden])', timeout=30000)
        check('no_folder_to_pick_without_a_place', ev('document.querySelector("#cvDirGroup").hidden'))
        pg.select_option('#cvScale', '2'); pg.fill('#cvCustom', '1'); pg.click('#cvGo')
        name = take_download(pg, D / 'boxed.png')
        check('right_box_makes_pictures', [name, Image.open(D / 'boxed.png').size[0]] == ['report_第1页.png', 1190], name)
        # the wrong box says which one to use
        pg.set_input_files('#cvImgInput', str(D / 'report.pdf'))
        pg.wait_for_selector('#msgDlg:not([hidden])', timeout=10000)
        check('pdf_on_the_picture_box', [pg.text_content('#msgTitle'), pg.text_content('#msgText')] == ['这里放图片', 'PDF 请拖到右边的「PDF 转图片」。'], pg.text_content('#msgTitle'))
        pg.click('#msgOk')
        pg.set_input_files('#cvPdfInput', str(D / 'scan 1.jpg'))
        pg.wait_for_selector('#msgDlg:not([hidden])', timeout=10000)
        check('picture_on_the_pdf_box', [pg.text_content('#msgTitle'), pg.text_content('#msgText')] == ['这里放 PDF', '图片请拖到左边的「图片转 PDF」。'], pg.text_content('#msgTitle'))
        pg.click('#msgOk')
        pg.screenshot(path=str(D / 'convert.png'))
        check('originals_untouched', (D / 'report.pdf').read_bytes() == (FIX / 'doc1.pdf').read_bytes() and (D / 'locked.pdf').read_bytes() == (FIX / 'locked.pdf').read_bytes())
        check('no_page_errors', not errs, errs)
        b.close()
    finally:
        app.stop()
r.finish()
