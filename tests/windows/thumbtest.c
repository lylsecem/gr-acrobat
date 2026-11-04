// Asks GRAcrobatThumbs.dll for a thumbnail the way File Explorer does, in a process of the DLL's own size (the
// 32-bit DLL needs a 32-bit caller; test_components.py builds this with MinGW-w64 when it is there).
//   thumbtest.exe <dll> <file.pdf> <size> <out.raw>
// out.raw: "hr width height alphatype\n" then the pixels, BGRA, top-down. Exit code 0 when it could ask at all.
#define COBJMACROS
#include <windows.h>
#include <shlwapi.h>
#include <thumbcache.h>
#include <stdio.h>

static const GUID CLSID_T = { 0x80fc8da7, 0x5504, 0x4437, { 0xaf, 0x79, 0xd3, 0x7c, 0x75, 0x62, 0x34, 0xe6 } };
static const GUID IID_CF = { 0x00000001, 0x0000, 0x0000, { 0xc0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x46 } };
static const GUID IID_INIT = { 0xb824b49d, 0x22ac, 0x4161, { 0xac, 0x8a, 0x99, 0x16, 0xe8, 0xfa, 0x3f, 0x7f } };
static const GUID IID_THUMB = { 0xe357fccd, 0xa995, 0x4576, { 0xb0, 0x1f, 0x23, 0x46, 0x30, 0x15, 0x4e, 0x96 } };

int wmain(int argc, wchar_t **argv) {
  if (argc != 5) return 2;
  HMODULE dll = LoadLibraryW(argv[1]);
  if (!dll) return 3;
  HRESULT (WINAPI *get)(REFCLSID, REFIID, void **) = (void *)GetProcAddress(dll, "DllGetClassObject");
  if (!get) return 4;
  IClassFactory *cf = NULL;
  IInitializeWithStream *init = NULL;
  IThumbnailProvider *thumb = NULL;
  IStream *stream = NULL;
  HBITMAP hbmp = NULL;
  WTS_ALPHATYPE alpha = WTSAT_UNKNOWN;
  HRESULT hr = get(&CLSID_T, &IID_CF, (void **)&cf);
  if (SUCCEEDED(hr)) hr = IClassFactory_CreateInstance(cf, NULL, &IID_INIT, (void **)&init);
  if (SUCCEEDED(hr)) hr = SHCreateStreamOnFileEx(argv[2], STGM_READ | STGM_SHARE_DENY_WRITE, 0, FALSE, NULL, &stream);
  if (SUCCEEDED(hr)) hr = IInitializeWithStream_Initialize(init, stream, STGM_READ);
  if (SUCCEEDED(hr)) hr = IInitializeWithStream_QueryInterface(init, &IID_THUMB, (void **)&thumb);
  if (SUCCEEDED(hr)) hr = IThumbnailProvider_GetThumbnail(thumb, (UINT)_wtoi(argv[3]), &hbmp, &alpha);
  FILE *out = _wfopen(argv[4], L"wb");
  if (!out) return 5;
  BITMAP bm = { 0 };
  if (hbmp) GetObjectW(hbmp, sizeof bm, &bm);
  fprintf(out, "%ld %ld %ld %d\n", (long)hr, bm.bmWidth, bm.bmHeight, (int)alpha);
  if (hbmp) {
    BITMAPINFO bi = { { sizeof(BITMAPINFOHEADER), bm.bmWidth, -bm.bmHeight, 1, 32, BI_RGB, 0, 0, 0, 0, 0 } };
    size_t n = (size_t)bm.bmWidth * bm.bmHeight * 4;
    unsigned char *px = malloc(n);
    HDC dc = GetDC(NULL);
    GetDIBits(dc, hbmp, 0, bm.bmHeight, px, &bi, DIB_RGB_COLORS);
    ReleaseDC(NULL, dc);
    fwrite(px, 1, n, out);
    free(px);
    DeleteObject(hbmp);
  }
  fclose(out);
  if (thumb) IThumbnailProvider_Release(thumb);
  if (init) IInitializeWithStream_Release(init);
  if (stream) IStream_Release(stream);
  if (cf) IClassFactory_Release(cf);
  return 0;
}
