// GRAcrobatThumbs.dll — File Explorer thumbnails for PDF files. 龙禹良制作
// An in-process thumbnail handler (IInitializeWithStream + IThumbnailProvider) registered on GR Acrobat's ProgID
// by the installer. The first page is drawn with PDFium (pdfium.dll in this DLL's folder, loaded on first use),
// reading only the parts of the file it needs through the stream Explorer hands over. The thumbnail has a thin
// grey edge and the GR Acrobat mark in its bottom left corner. Password-protected or damaged files get no
// thumbnail (Explorer shows the usual icon).
// PDFium is not thread safe, and Explorer asks for thumbnails on several threads: all of it runs under one lock.
#define COBJMACROS
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <objidl.h>
#include <thumbcache.h>
#include "fpdfview.h"
#include "badge.h"

// {80FC8DA7-5504-4437-AF79-D37C756234E6}, written by the installer under the ProgID's ShellEx key
static const GUID CLSID_GRAcrobatThumbs = { 0x80fc8da7, 0x5504, 0x4437, { 0xaf, 0x79, 0xd3, 0x7c, 0x75, 0x62, 0x34, 0xe6 } };
static const GUID IID_IUnknown_ = { 0x00000000, 0x0000, 0x0000, { 0xc0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x46 } };
static const GUID IID_IClassFactory_ = { 0x00000001, 0x0000, 0x0000, { 0xc0, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x46 } };
static const GUID IID_IInitializeWithStream_ = { 0xb824b49d, 0x22ac, 0x4161, { 0xac, 0x8a, 0x99, 0x16, 0xe8, 0xfa, 0x3f, 0x7f } };
static const GUID IID_IThumbnailProvider_ = { 0xe357fccd, 0xa995, 0x4576, { 0xb0, 0x1f, 0x23, 0x46, 0x30, 0x15, 0x4e, 0x96 } };

#define EDGE_GREY 196                    // the thin edge around the page

static HINSTANCE g_module;
static volatile LONG g_objects;          // live objects and server locks, for DllCanUnloadNow
static CRITICAL_SECTION g_lock;          // around every PDFium call

static int same_guid(REFGUID a, REFGUID b) { return memcmp(a, b, sizeof(GUID)) == 0; }

/* ---------- PDFium, loaded from this DLL's folder on first use ---------- */
static HMODULE g_pdfium;
static int g_pdfium_ready;
#define PDFIUM_FUNCS(X) X(FPDF_InitLibrary) X(FPDF_LoadCustomDocument) X(FPDF_CloseDocument) X(FPDF_LoadPage) \
  X(FPDF_ClosePage) X(FPDF_GetPageWidthF) X(FPDF_GetPageHeightF) X(FPDFBitmap_CreateEx) X(FPDFBitmap_FillRect) \
  X(FPDFBitmap_Destroy) X(FPDF_RenderPageBitmap)
#define DECLARE(name) static __typeof__(name) *p##name;
PDFIUM_FUNCS(DECLARE)

// Called with g_lock held.
static int load_pdfium(void) {
  if (g_pdfium_ready) return 1;
  if (g_pdfium) return 0;                // tried and failed: not again for every file
  WCHAR path[MAX_PATH + 16];
  DWORD n = GetModuleFileNameW(g_module, path, MAX_PATH);
  if (!n || n >= MAX_PATH) return 0;
  while (n && path[n - 1] != L'\\') n--;
  lstrcpyW(path + n, L"pdfium.dll");
  g_pdfium = LoadLibraryExW(path, NULL, LOAD_WITH_ALTERED_SEARCH_PATH);
  if (!g_pdfium) { g_pdfium = (HMODULE)1; return 0; }
#define RESOLVE(name) if (!(p##name = (__typeof__(name) *)(void *)GetProcAddress(g_pdfium, #name))) return 0;
  PDFIUM_FUNCS(RESOLVE)
  pFPDF_InitLibrary();
  g_pdfium_ready = 1;
  return 1;
}

/* ---------- reading the file through Explorer's stream ---------- */
// PDFium asks for blocks by position; the stream is read from there.
static int get_block(void *param, unsigned long position, unsigned char *buf, unsigned long size) {
  IStream *stream = (IStream *)param;
  LARGE_INTEGER at;
  at.QuadPart = position;
  if (FAILED(IStream_Seek(stream, at, STREAM_SEEK_SET, NULL))) return 0;
  while (size) {
    ULONG got = 0;
    HRESULT hr = IStream_Read(stream, buf, size, &got);
    if (FAILED(hr) || !got) return 0;
    buf += got;
    size -= got;
  }
  return 1;
}

/* ---------- the picture ---------- */
// The mark laid over the bottom left corner of a w × h top-down BGRA picture: the largest of its ready-drawn sizes
// for a thumbnail of this size (none on the smallest ones), an eighth of its size away from the edge.
static void draw_badge(unsigned char *bits, int w, int h, int side) {
  int k = -1;
  for (int i = 0; i < BADGE_COUNT; i++) if (side >= BADGE_FROM[i]) k = i;
  if (k < 0) return;
  int size = BADGE_SIZES[k], margin = 1 + size / 8, x0 = margin, y0 = h - margin - size;
  if (x0 + size > w || y0 < 0) return;
  const unsigned char *src = BADGE + BADGE_OFFSET[k];
  for (int y = 0; y < size; y++) {
    for (int x = 0; x < size; x++, src += 4) {
      unsigned a = src[3];
      if (!a) continue;
      unsigned char *p = bits + ((size_t)(y0 + y) * w + x0 + x) * 4;
      for (int c = 0; c < 3; c++) p[c] = (unsigned char)(src[c] + p[c] * (255 - a) / 255);
    }
  }
}

// The first page drawn to fit side × side: a top-down 32-bit DIB section, or NULL.
static HBITMAP render_first_page(IStream *stream, UINT side) {
  STATSTG st;
  if (FAILED(IStream_Stat(stream, &st, STATFLAG_NONAME)) || !st.cbSize.QuadPart || st.cbSize.QuadPart > 0xFFFFFFFFu) return NULL;
  FPDF_FILEACCESS access = { (unsigned long)st.cbSize.QuadPart, get_block, stream };
  HBITMAP hbmp = NULL;
  unsigned char *bits = NULL;
  int w = 0, h = 0;

  EnterCriticalSection(&g_lock);
  if (load_pdfium()) {
    FPDF_DOCUMENT doc = pFPDF_LoadCustomDocument(&access, NULL);   // no password: protected files get no thumbnail
    FPDF_PAGE page = doc ? pFPDF_LoadPage(doc, 0) : NULL;
    if (page) {
      float pw = pFPDF_GetPageWidthF(page), ph = pFPDF_GetPageHeightF(page);
      if (pw > 0 && ph > 0) {
        if (pw >= ph) { w = side; h = (int)(side * ph / pw + 0.5f); }
        else { h = side; w = (int)(side * pw / ph + 0.5f); }
        if (w < 1) w = 1;
        if (h < 1) h = 1;
        BITMAPINFO bi = { .bmiHeader = { sizeof(BITMAPINFOHEADER), w, -h, 1, 32, BI_RGB, 0, 0, 0, 0, 0 } };
        hbmp = CreateDIBSection(NULL, &bi, DIB_RGB_COLORS, (void **)&bits, NULL, 0);
        // BGRx: an opaque page, so text is smoothed against the white below it (the alpha bytes are set after)
        FPDF_BITMAP bmp = hbmp ? pFPDFBitmap_CreateEx(w, h, FPDFBitmap_BGRx, bits, w * 4) : NULL;
        if (bmp) {
          pFPDFBitmap_FillRect(bmp, 0, 0, w, h, 0xFFFFFFFF);
          pFPDF_RenderPageBitmap(bmp, page, 0, 0, w, h, 0, FPDF_ANNOT);
          pFPDFBitmap_Destroy(bmp);
        } else if (hbmp) {
          DeleteObject(hbmp);
          hbmp = NULL;
        }
      }
      pFPDF_ClosePage(page);
    }
    if (doc) pFPDF_CloseDocument(doc);
  }
  LeaveCriticalSection(&g_lock);
  if (!hbmp) return NULL;

  for (int x = 0; x < w; x++)                        // the edge, so a white page stands out from the window
    for (int c = 0; c < 3; c++) bits[x * 4 + c] = bits[((size_t)(h - 1) * w + x) * 4 + c] = EDGE_GREY;
  for (int y = 0; y < h; y++)
    for (int c = 0; c < 3; c++) bits[(size_t)y * w * 4 + c] = bits[((size_t)y * w + w - 1) * 4 + c] = EDGE_GREY;
  draw_badge(bits, w, h, (int)side);
  for (size_t i = 3; i < (size_t)w * h * 4; i += 4) bits[i] = 255;
  return hbmp;
}

/* ---------- the thumbnail handler ---------- */
typedef struct {
  IInitializeWithStream init;            // first: the object's address is this interface's
  IThumbnailProvider thumb;
  LONG refs;
  IStream *stream;
} Handler;

#define FROM_THUMB(p) ((Handler *)((char *)(p) - offsetof(Handler, thumb)))

static HRESULT STDMETHODCALLTYPE init_query(IInitializeWithStream *self, REFIID riid, void **ppv) {
  Handler *h = (Handler *)self;
  if (!ppv) return E_POINTER;
  if (same_guid(riid, &IID_IUnknown_) || same_guid(riid, &IID_IInitializeWithStream_)) *ppv = &h->init;
  else if (same_guid(riid, &IID_IThumbnailProvider_)) *ppv = &h->thumb;
  else { *ppv = NULL; return E_NOINTERFACE; }
  InterlockedIncrement(&h->refs);
  return S_OK;
}
static ULONG STDMETHODCALLTYPE init_addref(IInitializeWithStream *self) { return InterlockedIncrement(&((Handler *)self)->refs); }
static ULONG STDMETHODCALLTYPE init_release(IInitializeWithStream *self) {
  Handler *h = (Handler *)self;
  LONG n = InterlockedDecrement(&h->refs);
  if (!n) {
    if (h->stream) IStream_Release(h->stream);
    HeapFree(GetProcessHeap(), 0, h);
    InterlockedDecrement(&g_objects);
  }
  return n;
}
static HRESULT STDMETHODCALLTYPE init_initialize(IInitializeWithStream *self, IStream *stream, DWORD mode) {
  Handler *h = (Handler *)self;
  (void)mode;
  if (!stream) return E_INVALIDARG;
  if (h->stream) return HRESULT_FROM_WIN32(ERROR_ALREADY_INITIALIZED);
  IStream_AddRef(stream);
  h->stream = stream;
  return S_OK;
}
static IInitializeWithStreamVtbl init_vtbl = { init_query, init_addref, init_release, init_initialize };

static HRESULT STDMETHODCALLTYPE thumb_query(IThumbnailProvider *self, REFIID riid, void **ppv) { return init_query(&FROM_THUMB(self)->init, riid, ppv); }
static ULONG STDMETHODCALLTYPE thumb_addref(IThumbnailProvider *self) { return init_addref(&FROM_THUMB(self)->init); }
static ULONG STDMETHODCALLTYPE thumb_release(IThumbnailProvider *self) { return init_release(&FROM_THUMB(self)->init); }
static HRESULT STDMETHODCALLTYPE thumb_get(IThumbnailProvider *self, UINT cx, HBITMAP *phbmp, WTS_ALPHATYPE *alpha) {
  Handler *h = FROM_THUMB(self);
  if (!phbmp || !alpha) return E_POINTER;
  *phbmp = NULL;
  if (!h->stream) return E_UNEXPECTED;
  if (!cx || cx > 4096) return E_INVALIDARG;
  HBITMAP hbmp = render_first_page(h->stream, cx);
  if (!hbmp) return E_FAIL;
  *phbmp = hbmp;
  *alpha = WTSAT_RGB;
  return S_OK;
}
static IThumbnailProviderVtbl thumb_vtbl = { thumb_query, thumb_addref, thumb_release, thumb_get };

/* ---------- class factory and DLL entry points ---------- */
static HRESULT STDMETHODCALLTYPE cf_query(IClassFactory *self, REFIID riid, void **ppv) {
  if (!ppv) return E_POINTER;
  if (same_guid(riid, &IID_IUnknown_) || same_guid(riid, &IID_IClassFactory_)) { *ppv = self; return S_OK; }
  *ppv = NULL;
  return E_NOINTERFACE;
}
static ULONG STDMETHODCALLTYPE cf_addref(IClassFactory *self) { (void)self; return 2; }    // a static object
static ULONG STDMETHODCALLTYPE cf_release(IClassFactory *self) { (void)self; return 1; }
static HRESULT STDMETHODCALLTYPE cf_create(IClassFactory *self, IUnknown *outer, REFIID riid, void **ppv) {
  (void)self;
  if (!ppv) return E_POINTER;
  *ppv = NULL;
  if (outer) return CLASS_E_NOAGGREGATION;
  Handler *h = (Handler *)HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY, sizeof(Handler));
  if (!h) return E_OUTOFMEMORY;
  h->init.lpVtbl = &init_vtbl;
  h->thumb.lpVtbl = &thumb_vtbl;
  h->refs = 1;
  InterlockedIncrement(&g_objects);
  HRESULT hr = init_query(&h->init, riid, ppv);
  init_release(&h->init);
  return hr;
}
static HRESULT STDMETHODCALLTYPE cf_lock(IClassFactory *self, BOOL lock) {
  (void)self;
  if (lock) InterlockedIncrement(&g_objects); else InterlockedDecrement(&g_objects);
  return S_OK;
}
static IClassFactoryVtbl cf_vtbl = { cf_query, cf_addref, cf_release, cf_create, cf_lock };
static IClassFactory g_factory = { &cf_vtbl };

STDAPI DllGetClassObject(REFCLSID rclsid, REFIID riid, void **ppv) {
  if (!ppv) return E_POINTER;
  *ppv = NULL;
  if (!same_guid(rclsid, &CLSID_GRAcrobatThumbs)) return CLASS_E_CLASSNOTAVAILABLE;
  return cf_query(&g_factory, riid, ppv);
}
STDAPI DllCanUnloadNow(void) { return g_objects ? S_FALSE : S_OK; }

BOOL WINAPI DllMain(HINSTANCE instance, DWORD reason, LPVOID reserved) {
  (void)reserved;
  if (reason == DLL_PROCESS_ATTACH) {
    g_module = instance;
    DisableThreadLibraryCalls(instance);
    InitializeCriticalSection(&g_lock);
  } else if (reason == DLL_PROCESS_DETACH) {
    DeleteCriticalSection(&g_lock);    // PDFium stays loaded: freeing it while the process ends is not safe
  }
  return TRUE;
}
