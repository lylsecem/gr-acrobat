# Several documents open at once (a tab each), pictures opened like documents, and 导出为图片 saving a page as a
# picture file beside the document (no zip), in the real program. 转换 has its own test (test_convert.py).
import os, shutil, struct, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright
from helpers import App, CATCH_DOWNLOADS, FIX, Report, display, out_dir, take_download

D = out_dir('tabs-files')
for src, name in [('doc1.pdf', 'report.pdf'), ('doc2.pdf', 'notes.pdf'), ('landscape.pdf', 'wide.pdf'),
                  ('img/photo.jpg', 'photo.jpg'), ('img/diagram.png', 'diagram.png'), ('img/bad.png', 'bad.png'),
                  ('img/pic.webp', 'pic.webp'), ('img/small.gif', 'small.gif'), ('img/pic.bmp', 'pic.bmp')]:
    shutil.copy(FIX / src, D / name)
r = Report()
check = r.check


def png_size(path):
    b = Path(path).read_bytes()[:24]
    return struct.unpack('>II', b[16:24]) if b[:8] == b'\x89PNG\r\n\x1a\n' else None


with display(), sync_playwright() as pw:
    app = App('tabs')
    app.start(D / 'report.pdf')
    try:
        b, pg = app.page(pw)
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        ev = pg.evaluate
        tabs = lambda: ev('[...document.querySelectorAll(".doc-tab")].map(t => t.querySelector(".doc-tab-name").textContent + (t.classList.contains("active") ? "*" : ""))')
        drawn = lambda: ev('state.pdfDoc && document.querySelector("#pageCanvas").width > 0')
        pg.wait_for_function('state.pdfDoc && document.querySelector("#pageCanvas").width > 0', timeout=30000)
        ev('() => { localStorage.setItem("ocrOffered", "1"); document.querySelector("#ocrCard").hidden = true; }')
        check('one_tab', tabs() == ['report.pdf*'] and ev('!document.querySelector("#docTabs").hidden'), tabs())

        # ---- a second file opened keeps the first one open
        app.start(D / 'notes.pdf')
        pg.wait_for_function('docs.length === 2 && state.fileName === "notes.pdf" && document.querySelector("#pageCanvas").width > 0', timeout=30000)
        check('second_file_adds_a_tab', tabs() == ['report.pdf', 'notes.pdf*'], tabs())
        check('title_is_the_front_document', [pg.text_content('#screenTitle'), pg.text_content('#screenMeta')] == ['notes.pdf', '共 3 页'],
              [pg.text_content('#screenTitle'), pg.text_content('#screenMeta')])
        ev('renderMainPage(3)'); pg.wait_for_timeout(300)
        pg.click('.doc-tab >> nth=0'); pg.wait_for_function('state.fileName === "report.pdf"')
        pg.wait_for_timeout(300)
        check('switching_shows_the_other_document', [ev('state.numPages'), ev('state.currentPage'), ev('document.querySelectorAll(".thumb").length')] == [10, 1, 10],
              [ev('state.numPages'), ev('state.currentPage'), ev('document.querySelectorAll(".thumb").length')])
        ev('renderMainPage(5)'); pg.click('#zoomIn'); pg.wait_for_timeout(400)
        zoomed = ev('state.scale')
        pg.click('.doc-tab >> nth=1'); pg.wait_for_function('state.fileName === "notes.pdf"'); pg.wait_for_timeout(300)
        check('each_tab_keeps_its_page', ev('[state.currentPage, document.querySelector("#pageNumInput").value]') == [3, '3'], ev('[state.currentPage, document.querySelector("#pageNumInput").value]'))
        pg.click('.doc-tab >> nth=0'); pg.wait_for_function('state.fileName === "report.pdf"'); pg.wait_for_timeout(400)
        check('each_tab_keeps_its_zoom', ev('state.currentPage') == 5 and abs(ev('state.scale') - zoomed) < 1e-6, [ev('state.currentPage'), ev('state.scale'), zoomed])

        # ---- a file that is already open comes to the front instead of opening twice
        pg.click('.doc-tab >> nth=1'); pg.wait_for_function('state.fileName === "notes.pdf"')
        again = str(D / 'report.pdf')
        if os.name == 'nt':
            again = again.upper()                     # the same file, written differently
        app.start(again)
        pg.wait_for_function('state.fileName === "report.pdf"', timeout=30000); pg.wait_for_timeout(500)
        check('same_file_not_opened_twice', tabs() == ['report.pdf*', 'notes.pdf'], tabs())

        # ---- pictures: several at once from one launch, shown like a one-page document
        app.start(D / 'photo.jpg', D / 'diagram.png')
        pg.wait_for_function('docs.length === 4 && state.fileName === "diagram.png" && document.querySelector("#pageCanvas").width > 0', timeout=30000)
        check('pictures_open_in_tabs', tabs() == ['report.pdf', 'notes.pdf', 'photo.jpg', 'diagram.png*'], tabs())
        check('picture_shows_its_size', [pg.text_content('#screenTitle'), pg.text_content('#screenMeta'), ev('state.numPages')] == ['diagram.png', '640 × 480', 1],
              [pg.text_content('#screenTitle'), pg.text_content('#screenMeta'), ev('state.numPages')])
        check('picture_has_no_page_list', ev('document.querySelector("#rail").hidden'))
        ink = ev('''() => { const c = document.querySelector('#pageCanvas'); const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
          let red = 0; for (let i = 0; i < d.length; i += 4) if (d[i] > 150 && d[i + 1] < 90 && d[i + 2] < 90) red++; return red; }''')
        check('picture_is_drawn', ink > 500, ink)
        for _ in range(12):
            pg.click('#zoomIn')
        pg.wait_for_timeout(600)
        size = ev('(() => { const c = document.querySelector("#pageCanvas"); return [c.width, parseFloat(c.style.width)]; })()')
        check('zoomed_picture_not_drawn_beyond_its_pixels', size[0] <= 641 and size[1] > 1000, size)
        pg.click('.doc-tab >> nth=2'); pg.wait_for_function('state.fileName === "photo.jpg"')
        check('photo_size', pg.text_content('#screenMeta') == '1200 × 800', pg.text_content('#screenMeta'))

        # ---- a file that is not a picture says so and opens nothing
        app.start(D / 'bad.png')
        pg.wait_for_selector('#msgDlg:not([hidden])', timeout=30000)
        check('bad_picture_message', 'bad.png' in pg.text_content('#msgText') and len(tabs()) == 4, [pg.text_content('#msgText'), tabs()])
        pg.click('#msgOk')

        # ---- several files from 打开文件 (Ctrl+O), PDFs and pictures together
        pg.set_input_files('#openInput', [str(D / 'wide.pdf'), str(D / 'pic.webp'), str(D / 'small.gif'), str(D / 'pic.bmp')])
        pg.wait_for_function('docs.length === 8 && state.fileName === "pic.bmp"', timeout=30000)
        check('open_dialog_takes_several', tabs()[4:] == ['wide.pdf', 'pic.webp', 'small.gif', 'pic.bmp*'], tabs())
        # (Playwright hands these over as contents, without their place on disk, as a web page would get them:
        # 导出为图片 then downloads the picture instead of saving it beside the file.)
        ev(CATCH_DOWNLOADS)
        pg.click('#pageCanvas', button='right'); pg.wait_for_timeout(150)
        pg.click('.ctx .ctx-item:has-text("导出为图片")')
        name = take_download(pg, D / 'downloaded.png')
        check('picture_without_a_place_is_downloaded', [name, png_size(D / 'downloaded.png')] == ['pic_第1页.png', (180, 135)], [name, png_size(D / 'downloaded.png')])

        # ---- closing: ×, middle click, Ctrl+W, the tab's menu
        pg.click('.doc-tab.active .doc-tab-x'); pg.wait_for_function('docs.length === 7')
        check('x_closes_and_shows_the_neighbour', tabs()[-1] == 'small.gif*', tabs())
        pg.click('.doc-tab >> nth=5', button='middle'); pg.wait_for_function('docs.length === 6')
        check('middle_click_closes', 'pic.webp' not in tabs() and tabs()[-1] == 'small.gif*', tabs())
        pg.keyboard.press('Control+w'); pg.wait_for_function('docs.length === 5'); pg.wait_for_timeout(300)
        check('ctrl_w_closes', tabs()[-1] == 'wide.pdf*' and b.contexts[0].pages, tabs())
        pg.keyboard.press('Control+Tab'); pg.wait_for_timeout(300)
        check('ctrl_tab_goes_round', tabs()[0] == 'report.pdf*', tabs())
        pg.keyboard.press('Control+Shift+Tab'); pg.wait_for_timeout(300)
        check('ctrl_shift_tab_goes_back', tabs()[-1] == 'wide.pdf*', tabs())
        pg.click('.doc-tab >> nth=1', button='right'); pg.wait_for_timeout(150)
        items = ev('[...document.querySelectorAll(".ctx .ctx-item span")].map(b => b.textContent)')
        check('tab_menu', items == ['关闭', '关闭其他文档', '全部关闭'], items)
        pg.keyboard.press('Escape')

        # ---- 把第 n 页导出为图片 (the thumbnail menu): a picture beside the document, never over another
        pg.click('.doc-tab >> nth=0'); pg.wait_for_function('state.fileName === "report.pdf"')
        def export(n):
            pg.click(f'.thumb >> nth={n - 1}', button='right'); pg.wait_for_timeout(150)
            pg.click(f'.ctx .ctx-item:has-text("把第 {n} 页导出为图片")')
            pg.wait_for_selector('#askDlg:not([hidden])', timeout=60000)
            info = [pg.text_content('#askTitle'), pg.text_content('#askText'), ev('[...document.querySelectorAll("#askActions button")].map(b => b.textContent)')]
            pg.click('#askActions button:has-text("知道了")')
            return info
        info = export(2)
        check('page_saved_beside_the_document', info == ['已导出 1 张图片', f'保存为：{D / "report_第2页.png"}', ['打开文件夹', '知道了']], info)
        check('picture_is_twice_the_page_size', png_size(D / 'report_第2页.png') in [(1190, 1683), (1190, 1684)], png_size(D / 'report_第2页.png'))
        info = export(2)
        check('same_name_gets_a_number', (D / 'report_第2页 (2).png').exists() and info[1].endswith('report_第2页 (2).png'), info)
        check('no_zip_made', not list(D.glob('*.zip')), [p.name for p in D.glob('*.zip')])
        check('original_untouched', (D / 'report.pdf').read_bytes() == (FIX / 'doc1.pdf').read_bytes())
        # the page may only write pictures where its documents are
        bad = [ev('window.electronAPI.saveImage(%r, null, "..\\\\x.png", new Uint8Array([1]))' % str(D / 'report.pdf')),
               ev('window.electronAPI.saveImage(%r, %r, "x.png", new Uint8Array([1]))' % (str(D / 'report.pdf'), str(D))),
               ev('window.electronAPI.saveImage("report.pdf", null, "x.png", new Uint8Array([1]))'),
               ev('window.electronAPI.saveImage(%r, null, "x.exe", new Uint8Array([1]))' % str(D / 'report.pdf')),
               ev('window.electronAPI.makeFolder(%r, "../out")' % str(D / 'report.pdf'))]
        check('writes_only_pictures_beside_documents', all(x.get('error') for x in bad) and not (D / 'x.exe').exists() and not (D.parent / 'x.png').exists(), bad)

        # ---- a picture joins 合并拆分 as a one-page PDF
        pg.click('.tab-btn[data-mode=view]')
        pg.click('.doc-tab:has-text("photo.jpg") .doc-tab-name'); pg.wait_for_function('state.fileName === "photo.jpg"')
        pg.click('.tab-btn[data-mode=merge]'); pg.wait_for_timeout(300)
        ev('() => { $("#orgAddCurrent").click(); }')
        pg.wait_for_function('org.pages.length === 1', timeout=20000)
        check('picture_joins_merge', ev('[...org.sources.values()].map(s => [s.name, s.pageCount, s.path || null])') == [['photo.pdf', 1, None]],
              ev('[...org.sources.values()].map(s => [s.name, s.pageCount, s.path || null])'))

        # ---- 全部关闭: back to the empty page
        pg.click('.tab-btn[data-mode=view]'); pg.wait_for_timeout(200)
        pg.click('.doc-tab >> nth=0', button='right'); pg.wait_for_timeout(150)
        pg.click('.ctx .ctx-item:has-text("全部关闭")')
        pg.wait_for_function('docs.length === 0', timeout=10000)
        check('close_all_shows_empty_page', ev('[document.querySelector("#docTabs").hidden, getComputedStyle(document.querySelector("#stageEmpty")).display !== "none", document.querySelector("#printBtn").disabled, document.querySelector("#screenTitle").textContent]') == [True, True, True, '查看'],
              ev('[document.querySelector("#docTabs").hidden, getComputedStyle(document.querySelector("#stageEmpty")).display, document.querySelector("#printBtn").disabled, document.querySelector("#screenTitle").textContent]'))
        app.start(D / 'notes.pdf')
        pg.wait_for_function('docs.length === 1 && document.querySelector("#pageCanvas").width > 0', timeout=30000)
        check('opens_again_after_closing_all', tabs() == ['notes.pdf*'], tabs())
        pg.screenshot(path=str(D / 'tabs.png'))
        check('no_page_errors', not errs, errs)
        b.close()
    finally:
        app.stop()
r.finish()
