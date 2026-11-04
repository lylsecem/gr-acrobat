# The language switch (中文 / English / ไทย) in the real program: in English and Thai no Chinese is left on any
# screen, dialog or menu; the choice is kept and the next start uses it; the main process's messages follow.
import json, os, shutil, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright
from helpers import App, FIX, Report, display, out_dir

D = out_dir('language-files')
SHOTS = out_dir('language-shots')                            # every screen in each language, for a look
shutil.copy(FIX / 'doc1.pdf', D / 'report.pdf')
shutil.copy(FIX / 'pw' / 'pw_aes256.pdf', D / 'locked.pdf')
r = Report()
check = r.check

SCAN = '''() => {
  const HAN = /[\\u4e00-\\u9fff]/, found = new Set();
  const clean = (s) => s.replace(/龙禹良|中文/g, '');
  const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let n; (n = walk.nextNode());) {
    if (n.parentElement.closest('script, style')) continue;
    const v = clean(n.nodeValue); if (HAN.test(v)) found.add(v.trim());
  }
  for (const el of document.querySelectorAll('[title], [placeholder], [aria-label]'))
    for (const a of ['title', 'placeholder', 'aria-label']) { const v = clean(el.getAttribute(a) || ''); if (HAN.test(v)) found.add(a + ': ' + v); }
  if (HAN.test(clean(document.querySelector('#orgName').value))) found.add('orgName value');
  return [...found];
}'''


with display(), sync_playwright() as pw:
    app = App('language', lang=None, env={'LANG': 'en_US.UTF-8', 'LANGUAGE': 'en_US'})   # a first start on English Windows
    app.start(D / 'report.pdf')
    errs = []
    try:
        b, pg = app.page(pw)
        pg.on('pageerror', lambda e: errs.append(str(e)))
        ev = pg.evaluate
        pg.wait_for_function('state.pdfDoc && document.querySelector("#pageCanvas").width > 0', timeout=30000)
        # (on Windows the program asks Windows itself, so it is whatever this computer uses)
        first = ev('[LANG, document.documentElement.lang]')
        check('first_start_follows_windows_language', first == ['en', 'en'] if os.name != 'nt' else first in (['zh', 'zh-CN'], ['en', 'en'], ['th', 'th']), first)
        pg.wait_for_function("settingsSeen", timeout=15000)              # the offer card comes with the settings
        ev('() => { localStorage.setItem("ocrOffered", "1"); ocrCard({ title: "" }); closeOcrCard(); }')

        def tour(lang):
            """Every screen, dialog and menu in this language; returns the Chinese still shown, per place."""
            left = {}
            def note(where):
                found = ev(SCAN)
                if found: left[where] = found
            pg.click(f'.lang-seg button[data-lang={lang}]'); pg.wait_for_timeout(300)
            pg.click('.tab-btn[data-mode=view]'); pg.wait_for_timeout(400)
            note('view'); pg.screenshot(path=f'{SHOTS}/{lang}-1-view.png')
            pg.click('#pageCanvas', button='right'); pg.wait_for_timeout(150); note('view menu'); pg.keyboard.press('Escape')
            pg.click('.doc-tab >> nth=0', button='right'); pg.wait_for_timeout(150); note('tab menu'); pg.keyboard.press('Escape')
            pg.click('.thumb >> nth=1', button='right'); pg.wait_for_timeout(150); note('thumb menu'); pg.keyboard.press('Escape')
            pg.keyboard.press('Control+P'); pg.wait_for_timeout(200); note('print dialog')
            pg.screenshot(path=f'{SHOTS}/{lang}-2-print.png'); pg.click('#pdCancel')
            ev('() => { exportPagesAsImages([1], { fmt: "png", scale: 1 }); }')
            pg.wait_for_selector('#askDlg:not([hidden])', timeout=30000); note('picture saved'); pg.click('#askActions button >> nth=1')
            pg.click('.tab-btn[data-mode=convert]'); pg.wait_for_timeout(300)
            note('convert'); pg.screenshot(path=f'{SHOTS}/{lang}-3-convert.png')
            app.start('--pdf2img', D / 'report.pdf'); pg.wait_for_selector('#cvDlg:not([hidden])', timeout=30000)
            note('pdf to images'); pg.screenshot(path=f'{SHOTS}/{lang}-3b-pdf-to-images.png'); pg.click('#cvCancel')
            pg.click('.tab-btn[data-mode=view]'); ev('setMode("ocr")'); pg.wait_for_timeout(300); ev('$("#selAll").click()')
            note('pick pages')
            pg.click('.thumb >> nth=0', button='right'); pg.wait_for_timeout(150); note('select menu'); pg.keyboard.press('Escape')
            pg.click('.tab-btn[data-mode=merge]'); pg.wait_for_timeout(300)
            if not ev('org.pages.length'):
                ev('() => { $("#orgAddCurrent").click(); }'); pg.wait_for_function('org.pages.length === 10', timeout=20000)
            ev('orgExpand([...org.collapsed])'); pg.wait_for_timeout(600)
            pg.click('.ptile:not(.pstack) >> nth=0'); pg.click('.ptile:not(.pstack) >> nth=2', modifiers=['Shift'])
            note('merge'); pg.screenshot(path=f'{SHOTS}/{lang}-4-merge.png')
            pg.click('.ptile:not(.pstack) >> nth=1', button='right'); pg.wait_for_timeout(150); note('page menu')
            pg.screenshot(path=f'{SHOTS}/{lang}-5-merge-menu.png'); pg.keyboard.press('Escape')
            pg.click('.org-doc >> nth=0', button='right'); pg.wait_for_timeout(150); note('document menu'); pg.keyboard.press('Escape')
            ev('orgCollapse([...new Set(org.pages.map(p => p.src))])'); pg.wait_for_timeout(300)
            pg.click('.pstack >> nth=0', button='right'); pg.wait_for_timeout(150); note('stack menu'); pg.keyboard.press('Escape')
            ev('orgExpand([...org.collapsed])'); pg.wait_for_timeout(300)
            ev('() => { org.selected = new Set([org.pages[1].uid]); renderOrgSel(); orgSplit(orgSelectedInOrder()); }')
            pg.wait_for_selector('#askDlg:not([hidden])', timeout=30000); note('split question')
            pg.screenshot(path=f'{SHOTS}/{lang}-6-split.png'); pg.keyboard.press('Escape'); pg.wait_for_timeout(300); note('after split')
            ev('() => { orgOpenPreview(org.pages[0].uid); }'); pg.wait_for_timeout(400); note('preview'); pg.keyboard.press('Escape')
            ev('() => showUpdate({ state: "available", version: "9.9.9", notes: { zh: "中文说明", en: "English notes", th: "บันทึกภาษาไทย" } })')
            note('update card'); check(f'update_notes_{lang}', pg.text_content('#ucText') == {'zh': '中文说明', 'en': 'English notes', 'th': 'บันทึกภาษาไทย'}[lang], pg.text_content('#ucText'))
            ev('() => { $("#updateCard").hidden = true; }')
            ev('() => ocrCard({ title: t("新功能：文字识别（OCR）"), text: t("把扫描版 PDF 变成能搜索、能复制文字的 PDF，或导出文字。支持简体中文、英文和泰文。\\n需要下载约 17 MB；只在识别时加载，不影响打开速度。"), actions: [[t("不用了"), closeOcrCard], [t("安装"), closeOcrCard, true]] })')
            note('ocr offer'); pg.screenshot(path=f'{SHOTS}/{lang}-8-ocr-offer.png'); ev('closeOcrCard()')
            pg.click('.tab-btn[data-mode=view]'); pg.wait_for_timeout(300)
            return left

        for lang in ('en', 'th'):
            left = tour(lang)
            check(f'no_chinese_left_{lang}', not left, left)
        # Chinese again: everything back as it was written
        pg.click('.lang-seg button[data-lang=zh]'); pg.wait_for_timeout(300)
        check('back_to_chinese', [pg.text_content('.tab-btn[data-mode=merge]').strip(), pg.text_content('#printBtn').strip(), ev('$("#orgName").value')] == ['合并拆分', '打印', '合并结果'],
              [pg.text_content('.tab-btn[data-mode=merge]').strip(), pg.text_content('#printBtn').strip(), ev('$("#orgName").value')])
        # the main process's messages follow the language
        pg.click('.lang-seg button[data-lang=th]'); pg.wait_for_timeout(300)
        msg = ev('window.electronAPI.saveBeside("relative.pdf", new Uint8Array([1]))')
        check('main_messages_in_thai', msg.get('error') == 'ไม่ทราบว่าเอกสารต้นฉบับอยู่ในโฟลเดอร์ใด', msg)
        settings = json.loads((app.profile / 'settings.json').read_text())
        check('choice_kept', settings.get('lang') == 'th', settings)
        check('no_page_errors', not errs, errs)
        b.close()
    finally:
        app.stop()

    # the next start comes up in Thai, a password question included
    app.start(D / 'locked.pdf')
    try:
        b, pg = app.page(pw)
        pg.wait_for_selector('#pwDlg:not([hidden])', timeout=30000)
        check('next_start_in_thai', [pg.evaluate('LANG'), pg.text_content('#pwTitle'), pg.get_attribute('#pwInput', 'placeholder')],
              [pg.evaluate('LANG'), pg.text_content('#pwTitle'), pg.get_attribute('#pwInput', 'placeholder')])
        pg.screenshot(path=f'{SHOTS}/th-9-password.png')
        check('password_dialog_no_chinese', not pg.evaluate(SCAN), pg.evaluate(SCAN))
        b.close()
    finally:
        app.stop()
r.finish()
