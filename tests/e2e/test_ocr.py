# Text recognition in the real program: offered once, installed from a local mirror (each file checked, a spoiled
# one refused), searchable PDFs and text from scanned Chinese, English and Thai pages (turned, or with the page box
# away from 0,0), a protected PDF, and removing it again.
import shutil, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright
from pypdf import PdfReader
from helpers import App, CATCH_DOWNLOADS, FIX, Report, display, out_dir, pdf_info, pdf_text, take_download
from tools.ocr_mirror import serve

D = out_dir('ocr-files')
for name in ('scan_zh_en.pdf', 'scan_th.pdf', 'scan_rot.pdf', 'scan_offset.pdf', 'locked.pdf'):
    shutil.copy(FIX / name, D / name)
OUT = out_dir('ocr-saved')
r = Report()
check = r.check
flat = lambda s: ''.join(s.split())                    # Tesseract may put spaces between Chinese characters
SAMPLE = '识别测试'      # from 文字识别测试 on the scanned page; how 字 reads varies with the font it was printed in

with display(), sync_playwright() as pw:
    # ---- a spoiled file on the mirror: nothing installed
    spoiled, bad_server = serve(spoil={'eng.traineddata.gz'})
    app = App('ocr-spoiled', env={'GR_OCR_MIRROR': spoiled})
    app.start(D / 'scan_zh_en.pdf')
    try:
        b, pg = app.page(pw)
        pg.wait_for_selector('#ocrCard:not([hidden])', timeout=30000)
        pg.click('#ocrActions button:has-text("安装")')
        pg.wait_for_function('document.querySelector("#ocrTitle").textContent === "文字识别没有装好"', timeout=120000)
        check('spoiled_file_refused', [pg.text_content('#ocrText'), pg.evaluate('document.querySelector("#ocrTab").hidden'), (app.profile / 'ocr').exists()] == ['下载的文件不完整，请重试', True, False],
              [pg.text_content('#ocrText'), pg.evaluate('document.querySelector("#ocrTab").hidden'), (app.profile / 'ocr').exists()])
        b.close()
    finally:
        app.stop()
        bad_server.shutdown()

    mirror, server = serve()
    app = App('ocr', env={'GR_OCR_MIRROR': mirror})
    app.start(D / 'scan_zh_en.pdf')
    try:
        b, pg = app.page(pw)
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('dialog', lambda d: d.accept())
        ev = pg.evaluate
        # ---- offered once on a first start; 不用了 puts it away for good
        pg.wait_for_selector('#ocrCard:not([hidden])', timeout=30000)
        check('offered_on_first_start', [pg.text_content('#ocrTitle'), ev('document.querySelector("#ocrTab").hidden'), pg.text_content('#ocrState')] == ['新功能：文字识别（OCR）', True, '未安装'],
              [pg.text_content('#ocrTitle'), ev('document.querySelector("#ocrTab").hidden'), pg.text_content('#ocrState')])
        pg.click('#ocrActions button:has-text("不用了")')
        check('not_now_remembered', ev('[document.querySelector("#ocrCard").hidden, localStorage.getItem("ocrOffered")]') == [True, '1'])

        # ---- installed from the side bar
        pg.click('#ocrToggle')
        pg.wait_for_function('document.querySelector("#ocrTitle").textContent === "文字识别已安装"', timeout=180000)
        check('installed', [ev('document.querySelector("#ocrTab").hidden'), pg.text_content('#ocrState'), pg.text_content('#ocrToggle'), (app.profile / 'ocr' / 'installed').exists()] == [False, '已安装', '移除', True],
              [ev('document.querySelector("#ocrTab").hidden'), pg.text_content('#ocrState'), pg.text_content('#ocrToggle')])
        pg.wait_for_timeout(500)
        check('installed_card_stays', pg.text_content('#ocrTitle') == '文字识别已安装', pg.text_content('#ocrTitle'))
        late = []

        def dismiss(where):
            """Closes the card with its 知道了; anything else on it at this point is recorded as a failure."""
            buttons = ev('[...document.querySelectorAll("#ocrActions button")].map(b => b.textContent)')
            if '知道了' in buttons:
                pg.click('#ocrActions button:has-text("知道了")')
            else:
                check(f'card_after_{where}', False, [pg.text_content('#ocrTitle'), pg.text_content('#ocrText'), buttons])
                ev('closeOcrCard()')

        dismiss('install')

        def recognize(name, langs, out='pdf', fname=None):
            pg.click(f'.doc-tab:has-text("{name}") .doc-tab-name') if ev('docs.length > 1') else None
            pg.wait_for_function('state.fileName === %r' % name, timeout=30000)
            pg.click('.tab-btn[data-mode=ocr]'); pg.wait_for_timeout(300)
            ev('(langs) => { document.querySelectorAll("input[name=ocrLang]").forEach(b => { b.checked = langs.includes(b.value); }); }', langs)
            pg.select_option('#ocrOutSel', out)
            pg.click('#ocrRun')
            got = take_download(pg, OUT / (fname or f'{name}.{out}'), timeout=300000)
            pg.wait_for_function('document.querySelector("#ocrTitle").textContent === "识别完成"', timeout=30000)
            pg.wait_for_timeout(500)
            late.append([name, pg.text_content('#ocrTitle')])   # a late progress report must not cover it
            dismiss(name)
            return got

        ev(CATCH_DOWNLOADS)
        got = recognize('scan_zh_en.pdf', ['chi_sim', 'eng'])
        text = flat(pdf_text(OUT / 'scan_zh_en.pdf.pdf'))
        check('searchable_pdf', got == 'scan_zh_en_可搜索.pdf' and SAMPLE in text and 'Textrecognitiontest' in text, [got, text[:80]])
        src, res = PdfReader(str(D / 'scan_zh_en.pdf')), PdfReader(str(OUT / 'scan_zh_en.pdf.pdf'))
        check('pages_look_the_same', [list(p.mediabox) for p in src.pages] == [list(p.mediabox) for p in res.pages], [list(p.mediabox) for p in res.pages])
        got = recognize('scan_zh_en.pdf', ['chi_sim', 'eng'], 'txt')
        text = (OUT / 'scan_zh_en.pdf.txt').read_text(encoding='utf-8')
        check('text_file', got == 'scan_zh_en_文字.txt' and SAMPLE in flat(text) and '—— 第 2 页 ——' in text, [got, text[:80]])
        for name in ('scan_th.pdf', 'scan_rot.pdf', 'scan_offset.pdf', 'locked.pdf'):
            app.start(D / name)
            if name == 'locked.pdf':
                pg.wait_for_selector('#pwDlg:not([hidden])', timeout=30000)
                pg.fill('#pwInput', '1234'); pg.keyboard.press('Enter')
            pg.wait_for_function('state.fileName === %r' % name, timeout=30000)
        recognize('scan_th.pdf', ['tha'])
        check('thai', 'ทดสอบ' in flat(pdf_text(OUT / 'scan_th.pdf.pdf')), flat(pdf_text(OUT / 'scan_th.pdf.pdf'))[:60])
        recognize('scan_rot.pdf', ['chi_sim'])
        check('turned_page', SAMPLE in flat(pdf_text(OUT / 'scan_rot.pdf.pdf')), flat(pdf_text(OUT / 'scan_rot.pdf.pdf'))[:60])
        recognize('scan_offset.pdf', ['chi_sim', 'eng'])
        check('page_box_away_from_zero', SAMPLE in flat(pdf_text(OUT / 'scan_offset.pdf.pdf')), flat(pdf_text(OUT / 'scan_offset.pdf.pdf'))[:60])
        recognize('locked.pdf', ['chi_sim'])
        info = pdf_info(OUT / 'locked.pdf.pdf')
        check('protected_pdf_made_searchable', info[:2] == (False, 3) and '密码保护测试' in flat(info[2]), info)

        check('done_card_stays', all(t == '识别完成' for _, t in late), late)

        # ---- removed again: the screen and the files go
        pg.click('.tab-btn[data-mode=view]')
        pg.click('#ocrToggle'); pg.wait_for_timeout(1000)
        check('removed', [ev('document.querySelector("#ocrTab").hidden'), pg.text_content('#ocrState'), (app.profile / 'ocr').exists()] == [True, '未安装', False],
              [ev('document.querySelector("#ocrTab").hidden'), pg.text_content('#ocrState'), (app.profile / 'ocr').exists()])
        check('no_page_errors', not errs, errs)
        b.close()
    finally:
        app.stop()
        server.shutdown()
r.finish()
