# The text recognition files on a local server (the program's GR_OCR_MIRROR), so the tests install them without
# going out after the first time: each file in main.js's OCR_FILES is downloaded once from jsDelivr (or unpkg) into
# tests/.cache/ocr-mirror/<its npm path>, and checked against the size and checksum main.js expects.
import base64, hashlib, http.server, re, threading, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / 'tests' / '.cache' / 'ocr-mirror'
MIRRORS = ['https://cdn.jsdelivr.net/npm/', 'https://unpkg.com/']


def ocr_files():
    """[(file name, npm path, size, sha512)] as main.js lists them."""
    src = (ROOT / 'main.js').read_text(encoding='utf-8')
    return [(a, b, int(c), d) for a, b, c, d in re.findall(r"\['([^']+)', '([^']+)', (\d+), '([^']+)'\]", src)]


def good(path, size, sha512):
    if not path.exists() or path.stat().st_size != size:
        return False
    return base64.b64encode(hashlib.sha512(path.read_bytes()).digest()).decode() == sha512


def fill():
    for _, npm_path, size, sha512 in ocr_files():
        target = CACHE / npm_path
        if good(target, size, sha512):
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        for mirror in MIRRORS:
            try:
                with urllib.request.urlopen(mirror + npm_path, timeout=120) as res:
                    target.write_bytes(res.read())
                if good(target, size, sha512):
                    break
            except OSError:
                pass
        else:
            raise SystemExit(f'could not download {npm_path}')


def serve(spoil=()):
    """Serves the cache; the files named in spoil come with one byte changed. Gives (base URL, server)."""
    fill()

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            path = CACHE / self.path.lstrip('/')
            if not path.resolve().is_relative_to(CACHE.resolve()) or not path.is_file():
                self.send_response(404); self.end_headers(); return
            body = bytearray(path.read_bytes())
            if path.name in spoil:
                body[len(body) // 2] ^= 1
            self.send_response(200)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):
            pass

    httpd = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return f'http://127.0.0.1:{httpd.server_port}/', httpd


if __name__ == '__main__':
    fill()
    print('ok', CACHE)
