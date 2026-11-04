// GRAcrobatUnlock.exe — an unprotected copy of a password-protected PDF, for saving pages from it. 龙禹良制作
//   GRAcrobatUnlock.exe in.pdf out.pdf        the password (UTF-8) on standard input, so it is never on a command line
// Exit code: 0 done, 1 wrong arguments or in.pdf can't be opened, 2 wrong password, 3 not a PDF PDFium can read,
// 4 out.pdf could not be written. Uses PDFium (pdfium.dll in this program's folder), as the thumbnails do.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include "fpdfview.h"
#include "fpdf_save.h"

#define PDFIUM_FUNCS(X) X(FPDF_InitLibrary) X(FPDF_LoadCustomDocument) X(FPDF_GetLastError) X(FPDF_CloseDocument) X(FPDF_SaveAsCopy)
#define DECLARE(name) static __typeof__(name) *p##name;
PDFIUM_FUNCS(DECLARE)

static int load_pdfium(void) {
  WCHAR path[MAX_PATH + 16];
  DWORD n = GetModuleFileNameW(NULL, path, MAX_PATH);
  if (!n || n >= MAX_PATH) return 0;
  while (n && path[n - 1] != L'\\') n--;
  lstrcpyW(path + n, L"pdfium.dll");
  HMODULE lib = LoadLibraryExW(path, NULL, LOAD_WITH_ALTERED_SEARCH_PATH);
  if (!lib) return 0;
#define RESOLVE(name) if (!(p##name = (__typeof__(name) *)(void *)GetProcAddress(lib, #name))) return 0;
  PDFIUM_FUNCS(RESOLVE)
  return 1;
}

// PDFium reads the file by position; a large one is never read whole into memory.
static int get_block(void *param, unsigned long position, unsigned char *buf, unsigned long size) {
  HANDLE file = (HANDLE)param;
  LARGE_INTEGER at;
  at.QuadPart = position;
  if (!SetFilePointerEx(file, at, NULL, FILE_BEGIN)) return 0;
  while (size) {
    DWORD got = 0;
    if (!ReadFile(file, buf, size, &got, NULL) || !got) return 0;
    buf += got;
    size -= got;
  }
  return 1;
}

typedef struct {
  FPDF_FILEWRITE base;                   // first, so PDFium's pointer is this one
  HANDLE file;
  int failed;
} Writer;
static int write_block(FPDF_FILEWRITE *self, const void *data, unsigned long size) {
  Writer *w = (Writer *)self;
  const char *p = (const char *)data;
  while (size && !w->failed) {
    DWORD put = 0;
    if (!WriteFile(w->file, p, size, &put, NULL) || !put) w->failed = 1;
    p += put;
    size -= put;
  }
  return !w->failed;
}

int wmain(int argc, wchar_t **argv) {
  if (argc != 3) {
    fprintf(stderr, "usage: GRAcrobatUnlock.exe in.pdf out.pdf  (password on standard input)\n");
    return 1;
  }
  // the password: all of standard input, UTF-8, as PDFium takes it
  static char password[4096];
  DWORD len = 0, got;
  HANDLE in = GetStdHandle(STD_INPUT_HANDLE);
  while (in && in != INVALID_HANDLE_VALUE && len < sizeof password - 1 &&
         ReadFile(in, password + len, (DWORD)(sizeof password - 1 - len), &got, NULL) && got) len += got;
  password[len] = 0;

  if (!load_pdfium()) { fprintf(stderr, "pdfium.dll is missing\n"); return 1; }
  HANDLE src = CreateFileW(argv[1], GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
  if (src == INVALID_HANDLE_VALUE) { fprintf(stderr, "can't open the PDF\n"); return 1; }
  LARGE_INTEGER size;
  if (!GetFileSizeEx(src, &size) || !size.QuadPart || size.QuadPart > 0xFFFFFFFFu) { CloseHandle(src); return 3; }

  pFPDF_InitLibrary();
  FPDF_FILEACCESS access = { (unsigned long)size.QuadPart, get_block, src };
  FPDF_DOCUMENT doc = pFPDF_LoadCustomDocument(&access, password);
  if (!doc) {
    unsigned long err = pFPDF_GetLastError();
    CloseHandle(src);
    fprintf(stderr, err == FPDF_ERR_PASSWORD ? "wrong password\n" : "not a PDF that can be read\n");
    return err == FPDF_ERR_PASSWORD ? 2 : 3;
  }
  Writer w = { { 1, write_block }, CreateFileW(argv[2], GENERIC_WRITE, 0, NULL, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL), 0 };
  if (w.file == INVALID_HANDLE_VALUE) { pFPDF_CloseDocument(doc); CloseHandle(src); fprintf(stderr, "can't write the copy\n"); return 4; }
  int ok = pFPDF_SaveAsCopy(doc, &w.base, FPDF_REMOVE_SECURITY) && !w.failed;
  CloseHandle(w.file);
  pFPDF_CloseDocument(doc);
  CloseHandle(src);
  if (!ok) { fprintf(stderr, "can't write the copy\n"); return 4; }
  return 0;
}
