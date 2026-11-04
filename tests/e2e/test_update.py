# Updates in the real program, with a local server standing in for GitHub: the offer and its notes, a download that
# fails its checks or isn't there, the same or an older version not offered. An installer that passes the checks is
# only started off Windows (where it is refused): on Windows it would really ask to install.
import base64, hashlib, http.server, json, os, sys, threading
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright
from helpers import App, FIX, Report, display

r = Report()
check = r.check
VERSION = json.loads((Path(__file__).resolve().parents[2] / 'package.json').read_text(encoding='utf-8'))['version']
SETUP = b'MZ' + os.urandom(200000)                    # what the server hands out as the installer
served = {'latest.json': b'{}', 'setup.exe': SETUP}


class Server(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = served.get(self.path.lstrip('/'))
        self.send_response(200 if body is not None else 404)
        self.send_header('Content-Length', str(len(body or b'')))
        self.end_headers()
        self.wfile.write(body or b'')

    def log_message(self, *a):
        pass


httpd = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Server)
threading.Thread(target=httpd.serve_forever, daemon=True).start()
BASE = f'http://127.0.0.1:{httpd.server_port}'


def offer(version, size=len(SETUP), sha=None, path='setup.exe'):
    sha = sha or base64.b64encode(hashlib.sha512(SETUP).digest()).decode()
    f = {'name': f'GR-Acrobat-Setup-{version}-x64.exe', 'url': f'{BASE}/{path}', 'size': size, 'sha512': sha}
    served['latest.json'] = json.dumps({'version': version, 'notes': '修复了一些问题', 'notes_en': 'Some fixes', 'notes_th': 'แก้ไขบางอย่าง',
                                        'files': {'x64': f, 'ia32': {**f, 'name': f['name'].replace('x64', 'ia32')}}}).encode()


def run(name, wait_offer=True):
    """Starts the program, waits for the update check (8 s after start) and gives (app, browser, page)."""
    app = App(f'update-{name}', env={'GR_UPDATE_URL': f'{BASE}/latest.json'})
    app.start(FIX / 'doc1.pdf')
    b, pg = app.page(pw)
    pg.wait_for_function('state.pdfDoc', timeout=30000)
    pg.evaluate('() => { localStorage.setItem("ocrOffered", "1"); document.querySelector("#ocrCard").hidden = true; }')
    if wait_offer:
        pg.wait_for_selector('#updateCard:not([hidden])', timeout=30000)
    else:
        pg.wait_for_timeout(11000)
    return app, b, pg


card = lambda pg: [pg.text_content('#ucTitle'), pg.text_content('#ucText')]

with display(), sync_playwright() as pw:
    # a newer version: offered with its notes; a download that fails its checks is not kept
    offer('9.9.9', sha='AAAA')
    app, b, pg = run('bad')
    try:
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        check('newer_version_offered', card(pg) == ['发现新版本 9.9.9', '修复了一些问题'] and pg.text_content('#ucGo') == '立即更新', card(pg))
        pg.click('.lang-seg button[data-lang=en]'); pg.wait_for_timeout(200)
        check('notes_follow_the_language', pg.text_content('#ucText') == 'Some fixes', pg.text_content('#ucText'))
        pg.click('.lang-seg button[data-lang=zh]'); pg.wait_for_timeout(200)
        pg.click('#ucGo')
        pg.wait_for_function('document.querySelector("#ucTitle").textContent === "更新没有完成"', timeout=30000)
        check('bad_download_refused', [*card(pg), pg.text_content('#ucGo')] == ['更新没有完成', '下载的文件不完整，请重试', '重试'], [*card(pg), pg.text_content('#ucGo')])
        check('no_page_errors_bad', not errs, errs)
        b.close()
    finally:
        app.stop()

    # the installer is not where latest.json says
    offer('9.9.9', path='gone.exe')
    app, b, pg = run('missing')
    try:
        pg.click('#ucGo')
        pg.wait_for_function('document.querySelector("#ucTitle").textContent === "更新没有完成"', timeout=30000)
        check('missing_download_explained', card(pg) == ['更新没有完成', '下载失败（404），请检查网络后重试'], card(pg))
        b.close()
    finally:
        app.stop()

    # the same version, or an older one: nothing offered
    for name, version in [('same', VERSION), ('older', '0.0.1')]:
        offer(version)
        app, b, pg = run(name, wait_offer=False)
        try:
            check(f'{name}_version_not_offered', pg.evaluate('document.querySelector("#updateCard").hidden'))
            b.close()
        finally:
            app.stop()

    # a download that passes its checks goes on to installing (refused off Windows)
    if os.name != 'nt':
        offer('9.9.9')
        app, b, pg = run('good')
        try:
            pg.click('#ucGo')
            pg.wait_for_function('document.querySelector("#ucTitle").textContent === "更新没有完成"', timeout=30000)
            check('good_download_goes_on_to_install', card(pg) == ['更新没有完成', '只能在 Windows 上安装'], card(pg))
            b.close()
        finally:
            app.stop()
httpd.shutdown()
r.finish()
