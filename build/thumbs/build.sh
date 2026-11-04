#!/bin/bash
# Builds the two PDFium components for 64-bit and 32-bit Windows into build/thumbs/x64 and build/thumbs/ia32, next to
# the pdfium.dll they load: GRAcrobatThumbs.dll (File Explorer thumbnails) and GRAcrobatUnlock.exe (an unprotected
# copy of a password-protected PDF). The built files are kept in git; run this only after changing src/.
# Needs MinGW-w64 (x86_64-w64-mingw32-gcc and i686-w64-mingw32-gcc): `apt install mingw-w64` on Debian / Ubuntu, or a
# MinGW-w64 / llvm-mingw toolchain on PATH on Windows (Git Bash). PDFium is the build below from
# github.com/bblanchon/pdfium-binaries, downloaded only when its files are missing; its two headers are kept in src/.
set -euo pipefail
cd "$(dirname "$0")"
PDFIUM=8125                                   # chromium/8125 = PDFium 158.0.8125.0, see PDFium-licenses.txt

[ -f src/badge.h ] || python3 make-badge.py
for arch in x64 ia32; do
  case $arch in
    x64)  cc=x86_64-w64-mingw32-gcc; pkg=win-x64 ;;
    ia32) cc=i686-w64-mingw32-gcc;   pkg=win-x86 ;;
  esac
  if [ ! -f "$arch/pdfium.dll" ] || [ ! -f src/fpdfview.h ] || [ ! -f src/fpdf_save.h ]; then
    tmp=$(mktemp -d)
    curl -fsSL "https://github.com/bblanchon/pdfium-binaries/releases/download/chromium/$PDFIUM/pdfium-$pkg.tgz" | tar -xz -C "$tmp"
    mkdir -p "$arch"
    [ -f "$arch/pdfium.dll" ] || cp "$tmp/bin/pdfium.dll" "$arch/"
    [ -f src/fpdfview.h ] || cp "$tmp/include/fpdfview.h" src/
    [ -f src/fpdf_save.h ] || cp "$tmp/include/fpdf_save.h" src/
    rm -rf "$tmp"
  fi
  # -static-libgcc: nothing beyond Windows' own DLLs and pdfium.dll; --kill-at: plain export names on 32-bit too
  $cc -O2 -s -Wall -Wextra -Isrc -shared -static-libgcc -o "$arch/GRAcrobatThumbs.dll" src/thumbs.c src/thumbs.def -lgdi32 -Wl,--kill-at
  $cc -O2 -s -Wall -Wextra -Isrc -municode -static-libgcc -o "$arch/GRAcrobatUnlock.exe" src/unlock.c
  echo "$arch: $(ls -l "$arch" | tail -n +2 | awk '{print $5, $NF}' | tr '\n' ' ')"
done
