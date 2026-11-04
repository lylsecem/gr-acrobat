# Runs the end-to-end tests (tests/e2e/test_*.py) one after another against the real program, after making the
# test PDFs if they are missing. Usage:
#   python3 tests/run.py                 all of them
#   python3 tests/run.py split language  only those whose file name contains one of the words
#   python3 tests/run.py --skip ocr      all but those
# Exit code 0 when every check passed. The Windows tests (Wine) run separately: tests/windows/*.sh.
import subprocess, sys, time
from pathlib import Path

TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS))
from helpers import ELECTRON, FIX, display  # noqa: E402


def main(argv):
    skip = []
    if '--skip' in argv:
        i = argv.index('--skip')
        skip, argv = argv[i + 1:], argv[:i]
    if not ELECTRON.exists():
        sys.exit('Electron is missing: run npm ci first.')
    if not (FIX / 'doc1.pdf').exists():
        print('making the test PDFs…', flush=True)
        subprocess.run([sys.executable, str(TESTS / 'make_fixtures.py')], check=True)
    files = sorted((TESTS / 'e2e').glob('test_*.py'))
    files = [f for f in files if (not argv or any(w in f.stem for w in argv)) and not any(w in f.stem for w in skip)]
    results = []
    with display():                                  # one X display for all of them
        for f in files:
            print(f'\n=== {f.stem}', flush=True)
            t0 = time.time()
            try:
                code = subprocess.run([sys.executable, str(f)], timeout=900).returncode
            except subprocess.TimeoutExpired:
                code = 'timeout'
            results.append((f.stem, code, time.time() - t0))
    print('\n' + '\n'.join(f'{"ok  " if c == 0 else "FAIL"} {name}  ({s:.0f} s)' for name, c, s in results))
    sys.exit(0 if results and all(c == 0 for _, c, _ in results) else 1)


if __name__ == '__main__':
    main(sys.argv[1:])
