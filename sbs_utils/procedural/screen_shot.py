import ctypes as ct
import ctypes.wintypes as w

HGDI_ERROR = w.HANDLE(-1).value
NO_ERROR = 0
ERROR_INVALID_PARAMETER = 87

# GlobalAlloc flags
GHND          = 0x0042  # Combines GMEM_MOVEABLE and GMEM_ZEROINIT.
GMEM_FIXED    = 0x0000  # Allocates fixed memory. The return value is a pointer.
GMEM_MOVEABLE = 0x0002  # Allocates movable memory. Memory blocks are never moved in physical memory, but they can be moved within the default heap.
                        # The return value is a handle to the memory object. To translate the handle into a pointer, use the GlobalLock function.
                        # This value cannot be combined with GMEM_FIXED.
GMEM_ZEROINIT = 0x0040  # Initializes memory contents to zero.
GPTR          = 0x0040  # Combines GMEM_FIXED and GMEM_ZEROINIT.

# region flags for SelectObject
NULLREGION    = 1
SIMPLEREGION  = 2
COMPLEXREGION = 3

# DIB color table identifiers for GetDIBits
DIB_RGB_COLORS = 0  # color table in RGBs
DIB_PAL_COLORS = 1  # color table in palette indices

# raster-operation code for BitBlt
SRCCOPY        = 0x00CC0020  # dest = source
SRCPAINT       = 0x00EE0086  # dest = source OR dest
SRCAND         = 0x008800C6  # dest = source AND dest
SRCINVERT      = 0x00660046  # dest = source XOR dest
SRCERASE       = 0x00440328  # dest = source AND (NOT dest )
NOTSRCCOPY     = 0x00330008  # dest = (NOT source)
NOTSRCERASE    = 0x001100A6  # dest = (NOT src) AND (NOT dest)
MERGECOPY      = 0x00C000CA  # dest = (source AND pattern)
MERGEPAINT     = 0x00BB0226  # dest = (NOT source) OR dest
PATCOPY        = 0x00F00021  # dest = pattern
PATPAINT       = 0x00FB0A09  # dest = DPSnoo
PATINVERT      = 0x005A0049  # dest = pattern XOR dest
DSTINVERT      = 0x00550009  # dest = (NOT dest)
BLACKNESS      = 0x00000042  # dest = BLACK
WHITENESS      = 0x00FF0062  # dest = WHITE
NOMIRRORBITMAP = 0x80000000  # Do not Mirror the bitmap in this call
CAPTUREBLT     = 0x40000000  # Include layered windows

# constants for the biCompression field of BITMAPINFOHEADER
BI_RGB       = 0
BI_RLE8      = 1
BI_RLE4      = 2
BI_BITFIELDS = 3
BI_JPEG      = 4
BI_PNG       = 5

# function error handlers to raise exceptions on various error conditions

def boolcheck(result, func, args):
    if not result:
        raise ct.WinError(ct.get_last_error())
    return None

def nullcheck(result, func, args):
    if result is None:
        raise ct.WinError(ct.get_last_error())
    return result

def nonnullcheck(result, func, args):
    if not result is None:
        raise ct.WinError(ct.get_last_error())
    return result

def null_or_hgdi_errorcheck(result, func, args):
    if result is None:
        raise WindowsError('None')
    if result == HGDI_ERROR:
        raise WindowsError('HGDI_ERROR')
    return result

def zeroerrorcheck(result, func, args):
    if not result:
        err = ct.get_last_error()
        if err != NO_ERROR:
            raise ct.WinError(err)
    return result

def bmicheck(result, func, args):
    if result == ERROR_INVALID_PARAMETER:
        raise ct.WinError(ERROR_INVALID_PARAMETER)
    if not result:
        raise WindowsError('returned 0 (fail)')
    return result

# Windows structures not defined in ctypes.wintypes

class BITMAP(ct.Structure):
    _fields_ = (('bmType', w.LONG),
                ('bmWidth', w.LONG),
                ('bmHeight', w.LONG),
                ('bmWidthBytes', w.LONG),
                ('bmPlanes', w.WORD),
                ('bmBitsPixel', w.WORD),
                ('bmBits', w.LPVOID))
    def __repr__(self):
        return f'BITMAP(bmType={self.bmType}, bmWidth={self.bmWidth}, ' \
               f'bmHeight={self.bmHeight}, bmWidthBytes={self.bmWidthBytes}, ' \
               f'bmPlanes={self.bmPlanes}, bmBitsPixel={self.bmBitsPixel}, ' \
               f'bmBits={self.bmBits})'

class BITMAPFILEHEADER(ct.Structure):
    _pack_ = 2
    _fields_ = (('bfType', w.WORD),
                ('bfSize', w.DWORD),
                ('bfReserved1', w.WORD),
                ('bfReserved2', w.WORD),
                ('bfOffBits', w.DWORD))
    def __repr__(self):
        return f'BITMAPFILEHEADER(bfType={self.bfType}, bfSize={self.bfSize}, ' \
               f'bfReserved1={self.bfReserved1}, bfReserved2={self.bfReserved2}, ' \
               f'bfOffBits={self.bfOffBits})'

class BITMAPINFOHEADER(ct.Structure):
    _fields_ = (('biSize', w.DWORD),
                ('biWidth', w.LONG),
                ('biHeight', w.LONG),
                ('biPlanes', w.WORD),
                ('biBitCount', w.WORD),
                ('biCompression', w.DWORD),
                ('biSizeImage', w.DWORD),
                ('biXPelsPerMeter', w.LONG),
                ('biYPelsPerMeter', w.LONG),
                ('biClrUsed', w.DWORD),
                ('biClrImportant', w.DWORD))
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.biSize = ct.sizeof(self)
    def __repr__(self):
        return f'BITMAPINFOHEADER(biSize={self.biSize}, biWidth={self.biWidth}, ' \
               f'biHeight={self.biHeight}, biPlanes={self.biPlanes}, ' \
               f'biBitCount={self.biBitCount}, biCompression={self.biCompression}, ' \
               f'biSizeImage={self.biSizeImage}, biXPelsPerMeter={self.biXPelsPerMeter}, ' \
               f'biYPelsPerMeter={self.biYPelsPerMeter}, biClrUsed={self.biClrUsed}, ' \
               f'biClrImportant={self.biClrImportant})'

class RGBQUAD(ct.Structure):
    _fields_ = (('rgbBlue', w.BYTE),
                ('rgbGreen', w.BYTE),
                ('rgbRed', w.BYTE),
                ('rgbReserved', w.BYTE))
    def __repr__(self):
        return f'RGBQUAD(rgbBlue={self.rgbBlue}, rgbGreen={self.rgbGreen}, ' \
               f'rgbRed={self.rgbRed}, rgbReserved={self.rgbReserved})'

class BITMAPINFO(ct.Structure):
    _fields_ = (('bmiHeader', BITMAPINFOHEADER),
                ('bmiColors', RGBQUAD * 1))
    def __repr__(self):
        return f'BITMAPINFO(bmiHeader={self.bmiHeader}, bmiColors[0]={self.bmiColors[0]})'

# Extend RECT for display and comparison support
class RECT(w.RECT):
    def __repr__(self):
        return f'RECT(left={self.left}, top={self.top}, right={self.right}, bottom={self.bottom})'
    def __eq__(self, other):
        return bytes(self) == bytes(other)

LPBITMAPINFO = ct.POINTER(BITMAPINFO)
SIZE_T = ct.c_size_t

# Kernel32 APIs with full argtypes/restype and exception-on-error

kernel32 = ct.WinDLL('kernel32', use_last_error=True)
GlobalAlloc = kernel32.GlobalAlloc
GlobalAlloc.argtypes = w.UINT, SIZE_T
GlobalAlloc.restype = w.HGLOBAL
GlobalAlloc.errcheck = nullcheck
GlobalLock = kernel32.GlobalLock
GlobalLock.argtypes = w.HGLOBAL,
GlobalLock.restype = w.LPVOID
GlobalLock.errcheck = nullcheck
GlobalFree = kernel32.GlobalFree
GlobalFree.argtypes = w.HGLOBAL,
GlobalFree.restype = w.HGLOBAL
GlobalFree.errcheck = nonnullcheck
GlobalUnlock = kernel32.GlobalUnlock
GlobalUnlock.argtypes = w.HGLOBAL,
GlobalUnlock.restype = w.BOOL
GlobalUnlock.errcheck = zeroerrorcheck

# User32 APIs with full argtypes/restype and exception-on-error

user32 = ct.WinDLL('user32', use_last_error=True)
GetDesktopWindow = user32.GetDesktopWindow
GetDesktopWindow.argtypes = ()
GetDesktopWindow.restype = w.HWND
GetWindowDC = user32.GetWindowDC
GetWindowDC.argtypes = w.HWND,
GetWindowDC.restype = w.HDC
GetWindowDC.errcheck = nullcheck
GetClientRect = user32.GetClientRect
GetClientRect.argtypes = w.HWND, w.LPRECT
GetClientRect.restype = w.BOOL
GetClientRect.errcheck = boolcheck
ReleaseDC = user32.ReleaseDC
ReleaseDC.argtypes = w.HWND, w.HDC
ReleaseDC.restype = ct.c_int
ReleaseDC.errcheck = boolcheck

# GDI32 APIs with full argtypes/restype and exception-on-error

gdi32 = ct.WinDLL('gdi32', use_last_error=True)
CreateCompatibleDC = gdi32.CreateCompatibleDC
CreateCompatibleDC.argtypes = w.HDC,
CreateCompatibleDC.restype = w.HDC
CreateCompatibleDC.errcheck = nullcheck
CreateCompatibleBitmap = gdi32.CreateCompatibleBitmap
CreateCompatibleBitmap.argtypes = w.HDC, ct.c_int, ct.c_int
CreateCompatibleBitmap.restype = w.HBITMAP
CreateCompatibleBitmap.errcheck = nullcheck
SelectObject = gdi32.SelectObject
SelectObject.argtypes = w.HDC, w.HGDIOBJ
SelectObject.restype = w.HGDIOBJ
SelectObject.errcheck = null_or_hgdi_errorcheck
BitBlt = gdi32.BitBlt
BitBlt.argtypes = w.HDC, ct.c_int, ct.c_int, ct.c_int, ct.c_int, w.HDC, ct.c_int, ct.c_int, w.DWORD
BitBlt.restype = w.BOOL
BitBlt.errcheck = boolcheck
DeleteDC = gdi32.DeleteDC
DeleteDC.argtypes = w.HDC,
DeleteDC.restype = w.BOOL
DeleteDC.errcheck = boolcheck
DeleteObject = gdi32.DeleteObject
DeleteObject.argtypes = w.HGDIOBJ,
DeleteObject.restype = w.BOOL
DeleteObject.errcheck = boolcheck
GetObject = gdi32.GetObjectW
GetObject.argtypes = w.HANDLE, ct.c_int, w.LPVOID
GetObject.restype = ct.c_int
GetObject.errcheck = boolcheck
GetDIBits = gdi32.GetDIBits
GetDIBits.argtypes = w.HDC, w.HBITMAP, w.UINT, w.UINT, w.LPVOID, LPBITMAPINFO, w.UINT
GetDIBits.restype = ct.c_int
GetDIBits.errcheck = bmicheck

# Implementation.  APIs that needed cleanup all handled with try/finally blocks.

def saveBitmapToDisk(w, h, wDC, dataBitMap, file_path):
    bmpScreen = BITMAP()
    GetObject(dataBitMap, ct.sizeof(BITMAP), ct.byref(bmpScreen))
    bmfHeader = BITMAPFILEHEADER()
    bi = BITMAPINFOHEADER()
    bi.biSize = ct.sizeof(bi)
    bi.biWidth = bmpScreen.bmWidth
    bi.biHeight = bmpScreen.bmHeight
    bi.biPlanes = 1
    bi.biBitCount = 32
    bi.biCompression = BI_RGB
    dwBmpSize = ((bmpScreen.bmWidth * bi.biBitCount + 31) // 32) * 4 * bmpScreen.bmHeight
    hDIB = GlobalAlloc(GHND, dwBmpSize)
    try:
        lpbitmap = GlobalLock(hDIB)
        try:
            GetDIBits(wDC, dataBitMap, 0, bmpScreen.bmHeight, lpbitmap, ct.cast(ct.byref(bi), LPBITMAPINFO), DIB_RGB_COLORS)
            dwSizeofDIB = dwBmpSize + ct.sizeof(BITMAPFILEHEADER) + ct.sizeof(BITMAPINFOHEADER)
            bmfHeader.bfSize = dwSizeofDIB
            bmfHeader.bfType = 0x4D42  # ASCII 'BM'
            with open(file_path, 'wb') as f:
                f.write(bytes(bmfHeader))
                f.write(bytes(bi))
                f.write(ct.string_at(lpbitmap, dwBmpSize))
        finally:
            GlobalUnlock(hDIB)
    finally:
        GlobalFree(hDIB)

def gui_screenshot(image_path):
    hwnd = GetDesktopWindow()
    wDC = GetWindowDC(hwnd)
    try:
        cDC = CreateCompatibleDC(wDC)
        try:
            r = RECT()
            GetClientRect(hwnd, ct.byref(r))
            width = r.right - r.left
            height = r.bottom - r.top
            dataBitMap = CreateCompatibleBitmap(wDC, width, height)
            try:
                orig = SelectObject(cDC, dataBitMap)
                try:
                    BitBlt(cDC, 0, 0, width, height, wDC, 0, 0, SRCCOPY)
                    saveBitmapToDisk(width, height, wDC, dataBitMap, image_path)
                finally:
                    SelectObject(cDC, orig)
            finally:
                DeleteObject(dataBitMap)
        finally:
            DeleteDC(cDC)
    finally:
        ReleaseDC(hwnd, wDC)

