# The two PDFium components in build/thumbs/<arch>, on Windows (they are Windows programs; run it there):
#   python tests/windows/test_components.py
# GRAcrobatThumbs.dll is called the way File Explorer calls it: the 64-bit one from this (64-bit) Python, on several
# threads at once too; the 32-bit one through thumbtest.c, built with MinGW-w64 when i686-w64-mingw32-gcc is on PATH.
# GRAcrobatUnlock.exe (both) is run as the program runs it: in.pdf out.pdf, the password on standard input.
import os, shutil, struct, subprocess, sys, tempfile, threading
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from helpers import FIX, Report, out_dir, pdf_info, pdf_text
from windows.thumbs import Thumbs

if os.name != 'nt':
    sys.exit('test_components.py runs on Windows')
ROOT = Path(__file__).resolve().parents[2]
COMP = ROOT / 'build' / 'thumbs'
OUT = out_dir('components')
r = Report()
check = r.check
if not (FIX / 'doc1.pdf').exists():
    subprocess.run([sys.executable, str(ROOT / 'tests' / 'make_fixtures.py')], check=True)
E_FAIL = -2147467259


def px(data, w, x, y):
    i = (y * w + x) * 4
    return tuple(data[i:i + 3][::-1])                 # (r, g, b)


TEAL = (31, 122, 108)                                 # the mark's square


def teal_in(data, w, box):
    """How close the colour nearest to the mark's teal is, inside box (x0, y0, x1, y1)."""
    x0, y0, x1, y1 = box
    return min(sum(abs(a - b) for a, b in zip(px(data, w, x, y), TEAL)) for x in range(x0, x1) for y in range(y0, y1))


def looks_right(name, result, size, landscape=False):
    hr, w, h, alpha, data = result
    want = (size, round(size * 595.28 / 841.89)) if landscape else (round(size * 595.28 / 841.89), size)
    check(f'{name}_size', hr == 0 and (w, h) == want and alpha == 1, [hr, w, h, alpha])
    if hr or not data:
        return
    check(f'{name}_grey_edge', {px(data, w, 0, h // 2), px(data, w, w - 1, h // 2), px(data, w, w // 2, 0), px(data, w, w // 2, h - 1)} == {(196, 196, 196)},
          [px(data, w, 0, h // 2), px(data, w, w // 2, 0)])
    band = px(data, w, w // 2, max(2, size // 50))
    check(f'{name}_page_drawn', min(band) < 200, band)          # the coloured band at the top of the test pages
    badge = size * 3 // 16
    if badge >= 8:
        m = 1 + badge // 8
        near = teal_in(data, w, (m, h - m - badge, m + badge, h - m))
        check(f'{name}_badge', near < (40 if badge >= 16 else 90), near)
    opaque = all(data[i] == 255 for i in range(3, len(data), 4))
    check(f'{name}_opaque', opaque)


# ---- thumbnails, 64-bit
dll = COMP / 'x64' / 'GRAcrobatThumbs.dll'
t = Thumbs(dll)
for size in (256, 96, 48):
    looks_right(f'x64_doc1_{size}', t.thumbnail(FIX / 'doc1.pdf', size), size)
looks_right('x64_landscape_256', t.thumbnail(FIX / 'landscape.pdf', 256), 256, landscape=True)
small = t.thumbnail(FIX / 'doc1.pdf', 32)
check('x64_no_badge_at_32', small[0] == 0 and teal_in(small[4], small[1], (1, small[2] // 2, small[1] // 2, small[2] - 1)) > 120, small[:4])
for name in ('locked.pdf', 'broken.pdf', 'notpdf.pdf', 'pw/pw_big.pdf'):
    check(f'x64_no_thumbnail_{Path(name).stem}', t.thumbnail(FIX / name, 256)[0] == E_FAIL, t.thumbnail(FIX / name, 256)[:4])
check('x64_owner_only_has_one', t.thumbnail(FIX / 'pw' / 'pw_owner_only.pdf', 256)[0] == 0)
# several threads at once, as Explorer does: every picture the same as on its own
alone = {n: t.thumbnail(FIX / n, 200)[4] for n in ('doc1.pdf', 'landscape.pdf', 'scan_zh_en.pdf')}
bad = []
def worker(k):
    for i in range(6):
        n = list(alone)[(k + i) % 3]
        res = t.thumbnail(FIX / n, 200)
        if res[0] or res[4] != alone[n]:
            bad.append([k, i, n, res[0]])
threads = [threading.Thread(target=worker, args=(k,)) for k in range(8)]
for th in threads:
    th.start()
for th in threads:
    th.join()
check('x64_threads', not bad, bad[:5])
check('x64_can_unload', t.can_unload())

# ---- thumbnails, 32-bit (needs a 32-bit caller)
gcc = shutil.which('i686-w64-mingw32-gcc')
if gcc:
    exe = OUT / 'thumbtest32.exe'
    subprocess.run([gcc, '-O2', '-municode', '-o', str(exe), str(ROOT / 'tests' / 'windows' / 'thumbtest.c'), '-lshlwapi', '-lole32', '-lgdi32'], check=True)

    def thumb32(path, size):
        raw = OUT / 'thumb32.raw'
        subprocess.run([str(exe), str(COMP / 'ia32' / 'GRAcrobatThumbs.dll'), str(path), str(size), str(raw)], check=True)
        head, data = raw.read_bytes().split(b'\n', 1)
        hr, w, h, alpha = map(int, head.split())
        return hr, w, h, alpha, data
    res = thumb32(FIX / 'doc1.pdf', 256)
    looks_right('ia32_doc1_256', res, 256)
    check('ia32_same_as_x64', res[4] == t.thumbnail(FIX / 'doc1.pdf', 256)[4])
    check('ia32_no_thumbnail_locked', thumb32(FIX / 'locked.pdf', 256)[0] == E_FAIL)
else:
    print('SKIP 32-bit thumbnails: i686-w64-mingw32-gcc is not on PATH', flush=True)

# ---- GRAcrobatUnlock.exe, both
for arch in ('x64', 'ia32'):
    exe = COMP / arch / 'GRAcrobatUnlock.exe'
    have = [f for f in ('GRAcrobatThumbs.dll', 'GRAcrobatUnlock.exe', 'pdfium.dll') if (COMP / arch / f).exists()]
    check(f'{arch}_components_present', len(have) == 3, have)
    if not exe.exists():
        continue
    def unlock(src, password, out=None):
        out = out or OUT / f'{arch}-out.pdf'
        Path(out).unlink(missing_ok=True) if not str(out).startswith('Z:') else None
        p = subprocess.run([str(exe), str(src), str(out)], input=password.encode('utf-8'), capture_output=True, timeout=120)
        return p.returncode
    code = unlock(FIX / 'pw' / 'pw_aes256.pdf', '1234')
    info = pdf_info(OUT / f'{arch}-out.pdf') if code == 0 else None
    check(f'{arch}_unlock', code == 0 and info[:2] == (False, 3) and '密码保护测试 1' in pdf_text(OUT / f'{arch}-out.pdf'), [code, info])
    check(f'{arch}_wrong_password', unlock(FIX / 'pw' / 'pw_aes256.pdf', 'wrong') == 2)
    check(f'{arch}_thai_password', unlock(FIX / 'pw' / 'pw_utf8.pdf', '密码ไทย1') == 0)
    for name in ('pw_rc4_40', 'pw_rc4_128', 'pw_aes128'):
        check(f'{arch}_{name}', unlock(FIX / 'pw' / f'{name}.pdf', '1234') == 0)
    code = unlock(FIX / 'pw' / 'pw_owner_only.pdf', '')
    check(f'{arch}_owner_only', code == 0 and pdf_info(OUT / f'{arch}-out.pdf')[0] is False, code)
    code = unlock(FIX / 'pw' / 'pw_big.pdf', '1234')
    check(f'{arch}_big_file', code == 0 and pdf_info(OUT / f'{arch}-out.pdf')[:2] == (False, 8), code)
    check(f'{arch}_damaged', unlock(FIX / 'broken.pdf', '') == 3)
    check(f'{arch}_not_there', unlock(FIX / 'nothing-here.pdf', '') == 1)
    check(f'{arch}_cannot_write', unlock(FIX / 'pw' / 'pw_aes256.pdf', '1234', OUT / 'no-such-folder' / 'out.pdf') == 4)
    check(f'{arch}_wrong_arguments', subprocess.run([str(exe)], capture_output=True).returncode == 1)
r.finish()
