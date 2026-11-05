# 开机后台预加载 in the real program: closing the window hides it in the tray and the program forgets everything done
# in it (open documents, the 合并拆分 board), so the next files from Explorer start afresh: a second 合并所选文件 shows
# only its own documents. GR_TEST_RESIDENT stands in for the setting (Windows' startup list is left alone). The window
# is closed as its × does it (WM_CLOSE): Windows only, the setting is a Windows one; elsewhere the test is skipped.
import ctypes, os, shutil, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from playwright.sync_api import sync_playwright
from helpers import App, FIX, Report, display, out_dir

D = out_dir('resident-files')
for n in ('未命名1.pdf', '未命名1 - 副本.pdf'):
    shutil.copy(FIX / 'doc1.pdf', D / n)
for n in ('未命名1 (2).pdf', '未命名1 - 副本 (2).pdf'):
    shutil.copy(FIX / 'doc2.pdf', D / n)
r = Report()
check = r.check


def windows(pid):
    """The program's windows on screen."""
    u = ctypes.windll.user32                        # Electron's windows belong to its main process
    procs = {pid}
    found = []
    def each(hwnd, _):
        owner = ctypes.c_ulong()
        u.GetWindowThreadProcessId(hwnd, ctypes.byref(owner))
        if owner.value in procs and u.IsWindowVisible(hwnd):
            found.append(hwnd)
        return True
    u.EnumWindows(ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)(each), 0)
    return found


def close_window(pid):
    """Sends WM_CLOSE to the program's window, as clicking × does."""
    found = windows(pid)
    for h in found:
        ctypes.windll.user32.PostMessageW(h, 0x0010, 0, 0)   # WM_CLOSE
    return len(found)


if os.name != 'nt':
    print('skipped: the preload setting and closing by WM_CLOSE are Windows things')
    r.finish()
    sys.exit(0)

with display(), sync_playwright() as pw:
    app = App('resident', env={'GR_TEST_RESIDENT': '1'})
    app.start('--merge', D / '未命名1.pdf', D / '未命名1 - 副本.pdf')
    try:
        b, pg = app.page(pw)
        errs = []
        pg.on('pageerror', lambda e: errs.append(str(e)))
        ev = pg.evaluate
        pg.wait_for_function('typeof org === "object" && org.pages.length === 20', timeout=30000)
        app.start(D / '未命名1.pdf'); pg.wait_for_function('docs.length === 1', timeout=30000)
        board = lambda: ev('[...new Set(org.pages.map(p => org.sources.get(p.src).name))].sort()')
        check('first_merge', board() == ['未命名1 - 副本.pdf', '未命名1.pdf'], board())

        # ---- the window closed: hidden, the program still there, everything forgotten
        check('window_closed', close_window(app.proc.pid) >= 1)
        time.sleep(1.5)                              # Playwright sees the page go: it reloads
        b.close()
        b, pg = app.page(pw)                         # the page started afresh: connected to again
        pg.on('pageerror', lambda e: errs.append(str(e)))
        ev = pg.evaluate
        pg.wait_for_function('typeof org === "object" && settingsSeen', timeout=30000)
        check('still_running_hidden', [app.proc.poll() is None, len(windows(app.proc.pid))] == [True, 0], [app.proc.poll(), len(windows(app.proc.pid))])
        check('forgot_everything', [ev('docs.length'), ev('org.pages.length'), ev('state.mode')] == [0, 0, 'view'], [ev('docs.length'), ev('org.pages.length'), ev('state.mode')])

        # ---- the second 合并所选文件: only its own documents, and the window comes back
        app.start('--merge', D / '未命名1 (2).pdf', D / '未命名1 - 副本 (2).pdf')
        pg.wait_for_function('org.pages.length === 6', timeout=30000); pg.wait_for_timeout(500)
        check('second_merge_alone', board() == ['未命名1 (2).pdf', '未命名1 - 副本 (2).pdf'], board())
        check('window_shown_again', len(windows(app.proc.pid)) == 1, len(windows(app.proc.pid)))
        check('no_page_errors', not errs, errs)
        b.close()
    finally:
        app.stop()
r.finish()
