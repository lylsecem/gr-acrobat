# Calls GRAcrobatThumbs.dll the way File Explorer does (Windows only, through ctypes): the class factory,
# IInitializeWithStream with the file's stream, IThumbnailProvider::GetThumbnail. Used by test_components.py,
# and by hand: python tests/windows/thumbs.py <dll> <file.pdf> <size> <out.png>
import ctypes, sys, uuid
from ctypes import wintypes as W

HRESULT = ctypes.c_long
ole32 = ctypes.WinDLL('ole32')
shlwapi = ctypes.WinDLL('shlwapi')
gdi32 = ctypes.WinDLL('gdi32')
CLSID_THUMBS = '{80FC8DA7-5504-4437-AF79-D37C756234E6}'
IID_ICLASSFACTORY = '{00000001-0000-0000-C000-000000000046}'
IID_IINIT_STREAM = '{b824b49d-22ac-4161-ac8a-9916e8fa3f7f}'
IID_ITHUMBNAIL = '{e357fccd-a995-4576-b01f-234630154e96}'
shlwapi.SHCreateStreamOnFileEx.argtypes = [W.LPCWSTR, W.DWORD, W.DWORD, W.BOOL, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
shlwapi.SHCreateStreamOnFileEx.restype = HRESULT


def guid(s):
    return (ctypes.c_byte * 16).from_buffer_copy(uuid.UUID(s).bytes_le)


def method(obj, index, *argtypes):
    """The index-th function of a COM object's vtable, called on the object."""
    vtbl = ctypes.cast(obj, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
    fn = ctypes.WINFUNCTYPE(HRESULT, ctypes.c_void_p, *argtypes)(vtbl[index])
    return lambda *args: fn(obj, *args)


def release(obj):
    if obj:
        ctypes.WINFUNCTYPE(W.ULONG, ctypes.c_void_p)(ctypes.cast(obj, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents[2])(obj)


class BITMAP(ctypes.Structure):
    _fields_ = [('bmType', W.LONG), ('bmWidth', W.LONG), ('bmHeight', W.LONG), ('bmWidthBytes', W.LONG),
                ('bmPlanes', W.WORD), ('bmBitsPixel', W.WORD), ('bmBits', ctypes.c_void_p)]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [('biSize', W.DWORD), ('biWidth', W.LONG), ('biHeight', W.LONG), ('biPlanes', W.WORD), ('biBitCount', W.WORD),
                ('biCompression', W.DWORD), ('biSizeImage', W.DWORD), ('biXPelsPerMeter', W.LONG), ('biYPelsPerMeter', W.LONG),
                ('biClrUsed', W.DWORD), ('biClrImportant', W.DWORD)]


class Thumbs:
    def __init__(self, dll):
        self.dll = ctypes.WinDLL(str(dll))
        self.dll.DllGetClassObject.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
        self.dll.DllGetClassObject.restype = HRESULT
        self.dll.DllCanUnloadNow.restype = HRESULT

    def thumbnail(self, path, size):
        """(hresult, width, height, alpha type, BGRA bytes top-down) for the file at that size."""
        factory, init, thumb, stream = ctypes.c_void_p(), ctypes.c_void_p(), ctypes.c_void_p(), ctypes.c_void_p()
        hr = self.dll.DllGetClassObject(guid(CLSID_THUMBS), guid(IID_ICLASSFACTORY), ctypes.byref(factory))
        if hr < 0:
            return hr, 0, 0, 0, b''
        try:
            hr = method(factory, 3, ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p))(None, guid(IID_IINIT_STREAM), ctypes.byref(init))
            if hr < 0:
                return hr, 0, 0, 0, b''
            hr = shlwapi.SHCreateStreamOnFileEx(str(path), 0x20, 0, False, None, ctypes.byref(stream))   # STGM_READ | SHARE_DENY_WRITE
            if hr < 0:
                return hr, 0, 0, 0, b''
            hr = method(init, 3, ctypes.c_void_p, W.DWORD)(stream, 0)
            if hr < 0:
                return hr, 0, 0, 0, b''
            hr = method(init, 0, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p))(guid(IID_ITHUMBNAIL), ctypes.byref(thumb))
            if hr < 0:
                return hr, 0, 0, 0, b''
            hbmp, alpha = W.HBITMAP(), ctypes.c_int()
            hr = method(thumb, 3, W.UINT, ctypes.POINTER(W.HBITMAP), ctypes.POINTER(ctypes.c_int))(size, ctypes.byref(hbmp), ctypes.byref(alpha))
            if hr < 0:
                return hr, 0, 0, 0, b''
            w, h, px = self.pixels(hbmp)
            gdi32.DeleteObject(hbmp)
            return hr, w, h, alpha.value, px
        finally:
            for o in (thumb, init, stream, factory):
                release(o)

    @staticmethod
    def pixels(hbmp):
        bm = BITMAP()
        gdi32.GetObjectW(hbmp, ctypes.sizeof(bm), ctypes.byref(bm))
        bih = BITMAPINFOHEADER(ctypes.sizeof(BITMAPINFOHEADER), bm.bmWidth, -bm.bmHeight, 1, 32, 0)
        buf = ctypes.create_string_buffer(bm.bmWidth * bm.bmHeight * 4)
        dc = ctypes.windll.user32.GetDC(None)
        gdi32.GetDIBits(dc, hbmp, 0, bm.bmHeight, buf, ctypes.byref(bih), 0)
        ctypes.windll.user32.ReleaseDC(None, dc)
        return bm.bmWidth, bm.bmHeight, buf.raw

    def can_unload(self):
        return self.dll.DllCanUnloadNow() == 0


def save_png(w, h, bgra, path):
    from PIL import Image
    Image.frombuffer('RGBA', (w, h), bgra, 'raw', 'BGRA', 0, 1).save(path)


if __name__ == '__main__':
    t = Thumbs(sys.argv[1])
    hr, w, h, alpha, px = t.thumbnail(sys.argv[2], int(sys.argv[3]))
    print('hr', hex(hr & 0xffffffff), 'size', w, h, 'alpha', alpha)
    if px:
        save_png(w, h, px, sys.argv[4])
