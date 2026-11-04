# 合并拆分 in the real program: pages dragged onto the document list become <name>_N.pdf beside the original (the
# first free N, nothing overwritten), the originals keep or lose those pages, turns are kept, a protected original,
# files added by a second launch, and the merged download.
import shutil, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright
from pypdf import PdfReader
from helpers import App, CATCH_DOWNLOADS, FIX, Report, display, out_dir, pdf_info, pdf_text, take_download

D = out_dir('merge-files')
shutil.copy(FIX / 'doc1.pdf', D / 'TRUCKOEM.pdf')
shutil.copy(FIX / 'doc2.pdf', D / 'notes.pdf')
shutil.copy(FIX / 'doc2.pdf', D / 'TRUCKOEM_1.pdf')             # taken: the first split becomes _2
shutil.copy(FIX / 'pw' / 'pw_aes256.pdf', D / 'locked.pdf')
r = Report()
check = r.check

with display(), sync_playwright() as pw:
    app = App('merge')
    app.start(D / 'TRUCKOEM.pdf')                                # also open in 查看: it follows the file
    try:
        b, pg = app.page(pw)
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        ev = pg.evaluate
        pg.wait_for_function('state.pdfDoc && document.querySelector("#pageCanvas").width > 0', timeout=30000)
        ev('() => { localStorage.setItem("ocrOffered", "1"); document.querySelector("#ocrCard").hidden = true; }')
        app.start('--merge', D / 'TRUCKOEM.pdf', D / 'notes.pdf')
        pg.wait_for_function('org.pages.length === 13', timeout=30000)
        check('screen_named', ev('document.querySelector("#screenTitle").textContent') == '合并拆分', ev('document.querySelector("#screenTitle").textContent'))
        check('documents_come_stacked', ev('document.querySelectorAll(".pstack").length') == 2, ev('document.querySelectorAll(".pstack").length'))
        ev('orgExpand([...org.collapsed])'); pg.wait_for_timeout(500)
        check('expanded', ev('document.querySelectorAll(".ptile:not(.pstack)").length') == 13, ev('document.querySelectorAll(".ptile:not(.pstack)").length'))

        # ---- pages 2 and 3, the first one turned, dragged onto the document list
        ev('orgRotate([org.pages[1].uid], 90)')
        pg.click('.ptile:not(.pstack) >> nth=1'); pg.click('.ptile:not(.pstack) >> nth=2', modifiers=['Shift'])
        check('two_selected', ev('org.selected.size') == 2, ev('org.selected.size'))
        pg.locator('.ptile:not(.pstack) >> nth=1').drag_to(pg.locator('#orgDocs'))
        pg.wait_for_selector('#askDlg:not([hidden])', timeout=30000)
        split = D / 'TRUCKOEM_2.pdf'
        check('split_takes_the_first_free_name', split.exists() and (D / 'TRUCKOEM_1.pdf').read_bytes() == (FIX / 'doc2.pdf').read_bytes(),
              sorted(p.name for p in D.iterdir()))
        reader = PdfReader(str(split)) if split.exists() else None
        check('split_has_those_pages', reader and len(reader.pages) == 2 and 'DOC1 PAGE 2' in (reader.pages[0].extract_text() or '') and 'DOC1 PAGE 3' in (reader.pages[1].extract_text() or ''))
        check('split_keeps_the_turn', reader and reader.pages[0].rotation == 90 and reader.pages[1].rotation == 0, reader and [p.rotation for p in reader.pages])
        check('question_names_the_new_file', pg.text_content('#askTitle') == '已拆分出「TRUCKOEM_2.pdf」', pg.text_content('#askTitle'))
        pg.click('#askActions button:has-text("保留")'); pg.wait_for_timeout(500)
        check('keep_leaves_the_original', (D / 'TRUCKOEM.pdf').read_bytes() == (FIX / 'doc1.pdf').read_bytes())
        check('new_document_joins_the_list', ev('[...new Set(org.pages.map(p => org.sources.get(p.src).name))]') == ['TRUCKOEM.pdf', 'TRUCKOEM_2.pdf', 'notes.pdf'],
              ev('[...new Set(org.pages.map(p => org.sources.get(p.src).name))]'))

        # ---- page 4 split off by its menu, and deleted from the original
        ev('orgExpand([...org.collapsed])'); pg.wait_for_timeout(400)
        uid = ev('org.pages.find(p => org.sources.get(p.src).name === "TRUCKOEM.pdf" && p.idx === 3).uid')
        pg.click(f'.ptile[data-uid="{uid}"]', button='right'); pg.wait_for_timeout(150)
        pg.click('.ctx .ctx-item:has-text("拆分成新文档")')
        pg.wait_for_selector('#askDlg:not([hidden])', timeout=30000)
        pg.click('#askActions button:has-text("删除")')
        pg.wait_for_function('[...org.sources.values()].find(s => s.name === "TRUCKOEM.pdf").pageCount === 9', timeout=30000)
        text = pdf_text(D / 'TRUCKOEM.pdf')
        check('delete_rewrites_the_original', pdf_info(D / 'TRUCKOEM.pdf')[1] == 9 and 'DOC1 PAGE 4' not in text and 'DOC1 PAGE 5' in text, pdf_info(D / 'TRUCKOEM.pdf'))
        check('third_split_named', (D / 'TRUCKOEM_3.pdf').exists() and 'DOC1 PAGE 4' in pdf_text(D / 'TRUCKOEM_3.pdf'))
        pg.wait_for_function('docs[0].doc.numPages === 9', timeout=15000)
        check('open_tab_shows_the_file_as_it_now_is', ev('[docs.length, docs[0].fileName, docs[0].doc.numPages]') == [1, 'TRUCKOEM.pdf', 9], ev('[docs.length, docs[0].fileName, docs[0].doc.numPages]'))

        # ---- all of one document is not a split
        uids = ev('org.pages.filter(p => org.sources.get(p.src).name === "notes.pdf").map(p => p.uid)')
        ev('(u) => { orgSplit(u); }', uids)
        pg.wait_for_selector('#msgDlg:not([hidden])', timeout=10000)
        check('whole_document_is_not_split', pg.text_content('#msgTitle') == '不用拆分', pg.text_content('#msgTitle'))
        pg.click('#msgOk')

        # ---- a protected original added by another launch: the split and the rewritten original carry no password
        app.start('--merge', D / 'locked.pdf')
        pg.wait_for_selector('#pwDlg:not([hidden])', timeout=30000)
        pg.fill('#pwInput', '1234'); pg.keyboard.press('Enter')
        pg.wait_for_function('[...org.sources.values()].some(s => s.name === "locked.pdf")', timeout=30000)
        ev('orgExpand([...org.collapsed])'); pg.wait_for_timeout(400)
        uid = ev('org.pages.find(p => org.sources.get(p.src).name === "locked.pdf" && p.idx === 0).uid')
        ev('(u) => { orgSplit([u]); }', uid)
        pg.wait_for_selector('#askDlg:not([hidden])', timeout=30000)
        check('protected_original_warned', '删除后，原文档不再有密码保护。' in pg.text_content('#askText'), pg.text_content('#askText'))
        pg.click('#askActions button:has-text("删除")')
        pg.wait_for_function('[...org.sources.values()].find(s => s.name === "locked.pdf").pageCount === 2', timeout=30000)
        check('protected_split', pdf_info(D / 'locked_1.pdf')[:2] == (False, 1) and '密码保护测试 1' in pdf_text(D / 'locked_1.pdf'), pdf_info(D / 'locked_1.pdf'))
        check('protected_original_rewritten', pdf_info(D / 'locked.pdf')[:2] == (False, 2) and '密码保护测试 1' not in pdf_text(D / 'locked.pdf'), pdf_info(D / 'locked.pdf'))

        # ---- delete and undo, then the merged file
        total = ev('org.pages.length')
        ev('() => { org.selected = new Set([org.pages[0].uid]); renderOrgSel(); }')
        pg.keyboard.press('Delete'); pg.wait_for_timeout(300)
        removed = ev('org.pages.length')
        pg.keyboard.press('Control+z'); pg.wait_for_timeout(300)
        check('delete_and_undo', [removed, ev('org.pages.length')] == [total - 1, total], [total, removed, ev('org.pages.length')])
        ev(CATCH_DOWNLOADS)
        ev('() => { orgExport(false); }')
        name = take_download(pg, D.parent / 'merged.pdf')
        info = pdf_info(D.parent / 'merged.pdf')
        check('merged_download', info[:2] == (False, total) and name == '合并结果.pdf', [name, *info])
        check('no_page_errors', not errs, errs)
        b.close()
    finally:
        app.stop()
r.finish()
