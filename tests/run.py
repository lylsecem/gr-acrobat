# Runs the end-to-end tests (tests/e2e/test_*.py) one after another against the real program, after making the
# test files if they are missing. Usage:
#   python3 tests/run.py                 all of them
#   python3 tests/run.py split language  only those whose file name contains one of the words
#   python3 tests/run.py --skip ocr      all but those
# Exit code 0 when every check passed. The Windows components are tested separately: tests/windows/test_components.py.
# On GitHub Actions each failure is also written as an error note on the run's page, which anyone can read there
# (the full log needs a sign-in).
import os, subprocess, sys, threading, time
from pathlib import Path

TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS))
from helpers import ELECTRON, FIX, display  # noqa: E402


def note_error(title, lines):
    if os.environ.get('GITHUB_ACTIONS') == 'true':
        text = '\n'.join(lines)[-3000:].replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
        print(f'::error title={title}::{text}', flush=True)


def run(cmd, timeout):
    """Runs cmd with its output passed through: (exit code or 'timeout', the output lines)."""
    lines, expired = [], []
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
    timer = threading.Timer(timeout, lambda: (expired.append(1), p.kill()))
    timer.start()
    try:
        for line in p.stdout:
            print(line, end='', flush=True)
            lines.append(line.rstrip('\n'))
        code = p.wait()
    finally:
        timer.cancel()
    return ('timeout' if expired else code), lines


def main(argv):
    skip = []
    if '--skip' in argv:
        i = argv.index('--skip')
        skip, argv = argv[i + 1:], argv[:i]
    if not ELECTRON.exists():
        note_error('Electron is missing', [f'{ELECTRON} is not there: npm ci did not download it.'])
        sys.exit('Electron is missing: run npm ci first.')
    if not (FIX / 'doc1.pdf').exists():
        print('making the test files…', flush=True)
        code, lines = run([sys.executable, str(TESTS / 'make_fixtures.py')], 600)
        if code != 0:
            note_error('make_fixtures.py failed', lines[-40:])
            sys.exit(1)
    files = sorted((TESTS / 'e2e').glob('test_*.py'))
    files = [f for f in files if (not argv or any(w in f.stem for w in argv)) and not any(w in f.stem for w in skip)]
    results = []
    with display():                                  # one X display for all of them
        for f in files:
            print(f'\n=== {f.stem}', flush=True)
            t0 = time.time()
            code, lines = run([sys.executable, str(f)], 900)
            results.append((f.stem, code, time.time() - t0))
            if code != 0:                            # the failed checks, then the end of the output (a traceback)
                fails = [l[:300] for l in lines if l.startswith('FAIL ')]
                note_error(f'{f.stem} failed ({code})', fails + ['…'] + [l[:300] for l in lines[-25:]])
    print('\n' + '\n'.join(f'{"ok  " if c == 0 else "FAIL"} {name}  ({s:.0f} s)' for name, c, s in results))
    sys.exit(0 if results and all(c == 0 for _, c, _ in results) else 1)


if __name__ == '__main__':
    main(sys.argv[1:])
