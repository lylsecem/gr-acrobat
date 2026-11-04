# Shared by the end-to-end tests: paths, an X display, and the real program (Electron) started with a
# debugging port so Playwright can drive its window.
import base64, json, os, shutil, signal, socket, subprocess, sys, time
from contextlib import contextmanager
from pathlib import Path
from pypdf import PdfReader

sys.stdout.reconfigure(encoding='utf-8', errors='replace')   # Thai and Chinese in the report, whatever the console
ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / 'tests'
FIX = TESTS / '.fixtures'                 # test PDFs, made by make_fixtures.py
OUT = TESTS / '.out'                      # profiles, saved files, screenshots
ELECTRON = ROOT / 'node_modules' / 'electron' / 'dist' / ('electron.exe' if os.name == 'nt' else 'electron')
DEAD_URL = 'http://127.0.0.1:9/none.json'  # update checks go nowhere unless a test serves one


def out_dir(name):
    d = OUT / name
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True)
    return d


def free_port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


@contextmanager
def display():
    """An X display for Electron: the current one, or a private Xvfb."""
    if os.environ.get('DISPLAY') or sys.platform in ('win32', 'darwin'):
        yield
        return
    num = 90 + os.getpid() % 9
    xv = subprocess.Popen(['Xvfb', f':{num}', '-screen', '0', '1440x900x24'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.environ['DISPLAY'] = f':{num}'
    time.sleep(1)
    try:
        yield
    finally:
        xv.terminate()
        os.environ.pop('DISPLAY', None)


def unlock_stand_in():
    """GR_UNLOCK for the tests: the real GRAcrobatUnlock.exe on Windows, or under Wine when Wine is there;
    otherwise tools/unlock_stand_in.py doing the same job with the same exit codes. A small launcher script is
    written for the last two, since the program starts GR_UNLOCK directly."""
    exe = ROOT / 'build' / 'thumbs' / 'x64' / 'GRAcrobatUnlock.exe'
    if os.name == 'nt':
        return str(exe)
    wine = shutil.which('wine64') or ('/usr/lib/wine/wine64' if Path('/usr/lib/wine/wine64').exists() else None)
    if wine and exe.exists():
        body = f'exec "{wine}" "{exe}" "$(winepath -w "$1")" "$(winepath -w "$2")" 2>/dev/null'
    else:
        body = f'exec "{sys.executable}" "{TESTS / "tools" / "unlock_stand_in.py"}" "$@"'
    OUT.mkdir(parents=True, exist_ok=True)
    launcher = OUT / 'unlock-stand-in.sh'
    launcher.write_text('#!/bin/sh\n' + body + '\n')
    launcher.chmod(0o755)
    return str(launcher)


class Report:
    """Named checks; prints them as they come and a JSON summary at the end ({"fails": [...]})."""
    def __init__(self):
        self.results, self.fails = {}, []

    def check(self, name, ok, info=None):
        self.results[name] = info if info is not None else bool(ok)
        print('PASS' if ok else 'FAIL', name, json.dumps(self.results[name], ensure_ascii=False)[:300], flush=True)
        if not ok:
            self.fails.append(name)

    def finish(self):
        print(json.dumps({'fails': self.fails}, ensure_ascii=False))
        sys.exit(1 if self.fails else 0)


class App:
    """The program in a fresh profile. lang: written to its settings ('zh' keeps the tests' Chinese texts
    stable); None leaves it unset, so it follows the system language like a first start."""
    def __init__(self, name, lang='zh', env=None):
        self.profile = OUT / f'profile-{name}'
        shutil.rmtree(self.profile, ignore_errors=True)
        self.profile.mkdir(parents=True)
        if lang:
            (self.profile / 'settings.json').write_text(json.dumps({'lang': lang}))
        self.env = {**os.environ, 'ELECTRON_DISABLE_SECURITY_WARNINGS': '1', 'GR_UPDATE_URL': DEAD_URL,
                    'GR_UNLOCK': unlock_stand_in(), **(env or {})}
        self.proc = None
        self.port = None

    def start(self, *args):
        """Starts the program (args as from Explorer: files, --merge, --split…) or, when it is already
        running, hands the args to it the way a second launch does."""
        port = self.port or free_port()
        p = subprocess.Popen([str(ELECTRON), str(ROOT), '--no-sandbox', f'--remote-debugging-port={port}',
                              f'--user-data-dir={self.profile}', *map(str, args)],
                             env=self.env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if self.proc is None:
            self.proc, self.port = p, port
        return p

    def page(self, pw):
        """Connects Playwright to the program's window: (browser, page)."""
        deadline = time.time() + 40
        while time.time() < deadline:
            try:
                b = pw.chromium.connect_over_cdp(f'http://127.0.0.1:{self.port}', timeout=5000)
                pg = next((x for c in b.contexts for x in c.pages if 'index.html' in x.url), None)
                if pg:
                    return b, pg
                b.close()
            except Exception:
                pass
            time.sleep(0.2)
        raise RuntimeError('the program window did not appear')

    def stop(self):
        if self.proc and os.name == 'nt':
            # the whole tree: a helper process left behind would keep the profile locked for the next start
            subprocess.run(['taskkill', '/T', '/F', '/PID', str(self.proc.pid)], capture_output=True)
        if self.proc:
            self.proc.send_signal(signal.SIGTERM)
            try:
                self.proc.wait(8)
            except Exception:
                self.proc.kill()
            self.proc = None


# Saving in the page goes through downloadBlob(); the tests catch it to read what would be saved.
CATCH_DOWNLOADS = '() => { window.__dl = []; window.downloadBlob = (blob, name) => { __dl.push({ name, blob }); }; }'


def take_download(pg, path, timeout=30000):
    """Waits for the next caught download, writes it to path and returns its file name."""
    pg.wait_for_function('__dl.length > 0', timeout=timeout)
    name, b64 = pg.evaluate('''async () => { const d = __dl.shift(); const u = new Uint8Array(await d.blob.arrayBuffer());
      let s = ''; for (let i = 0; i < u.length; i += 0x8000) s += String.fromCharCode(...u.subarray(i, i + 0x8000));
      return [d.name, btoa(s)]; }''')
    Path(path).write_bytes(base64.b64decode(b64))
    return name


def pdf_info(path):
    """(protected?, page count, the first 60 characters of the text)."""
    r = PdfReader(str(path))
    return r.is_encrypted, len(r.pages), ' '.join(pdf_text(path).split())[:60]


def pdf_text(path):
    r = PdfReader(str(path))
    if r.is_encrypted:
        r.decrypt('')
    return '\n'.join(page.extract_text() or '' for page in r.pages)
