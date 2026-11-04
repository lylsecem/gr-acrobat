# Stands in for GRAcrobatUnlock.exe where it can't run (Linux without Wine): the same job with pikepdf, the same
# arguments (in.pdf out.pdf, the password on standard input) and the same exit codes: 0 done, 1 no such file or
# wrong arguments, 2 wrong password, 3 not a PDF it can read, 4 the copy could not be written.
import sys
import pikepdf

if len(sys.argv) != 3:
    sys.exit(1)
password = sys.stdin.buffer.read().decode('utf-8')
try:
    pdf = pikepdf.open(sys.argv[1], password=password)
except FileNotFoundError:
    sys.exit(1)
except pikepdf.PasswordError:
    sys.exit(2)
except Exception:
    sys.exit(3)
try:
    pdf.save(sys.argv[2])
except Exception:
    sys.exit(4)
