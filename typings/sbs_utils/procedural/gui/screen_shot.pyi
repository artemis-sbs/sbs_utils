from ctypes import SIZE_T
def bmicheck (result, func, args):
    ...
def boolcheck (result, func, args):
    ...
def gui_screenshot (image_path):
    ...
def nonnullcheck (result, func, args):
    ...
def null_or_hgdi_errorcheck (result, func, args):
    ...
def nullcheck (result, func, args):
    ...
def saveBitmapToDisk (w, h, wDC, dataBitMap, file_path):
    ...
def zeroerrorcheck (result, func, args):
    ...
class BITMAP(Structure):
    """Structure base class"""
    def __repr__ (self):
        """Return repr(self)."""
    bmBits : CField
    """Structure/Union member"""
    bmBitsPixel : CField
    """Structure/Union member"""
    bmHeight : CField
    """Structure/Union member"""
    bmPlanes : CField
    """Structure/Union member"""
    bmType : CField
    """Structure/Union member"""
    bmWidth : CField
    """Structure/Union member"""
    bmWidthBytes : CField
    """Structure/Union member"""
class BITMAPFILEHEADER(Structure):
    """Structure base class"""
    def __repr__ (self):
        """Return repr(self)."""
    bfOffBits : CField
    """Structure/Union member"""
    bfReserved1 : CField
    """Structure/Union member"""
    bfReserved2 : CField
    """Structure/Union member"""
    bfSize : CField
    """Structure/Union member"""
    bfType : CField
    """Structure/Union member"""
class BITMAPINFO(Structure):
    """Structure base class"""
    def __repr__ (self):
        """Return repr(self)."""
    bmiColors : CField
    """Structure/Union member"""
    bmiHeader : CField
    """Structure/Union member"""
class BITMAPINFOHEADER(Structure):
    """Structure base class"""
    def __init__ (self, *args, **kwargs):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def __repr__ (self):
        """Return repr(self)."""
    biBitCount : CField
    """Structure/Union member"""
    biClrImportant : CField
    """Structure/Union member"""
    biClrUsed : CField
    """Structure/Union member"""
    biCompression : CField
    """Structure/Union member"""
    biHeight : CField
    """Structure/Union member"""
    biPlanes : CField
    """Structure/Union member"""
    biSize : CField
    """Structure/Union member"""
    biSizeImage : CField
    """Structure/Union member"""
    biWidth : CField
    """Structure/Union member"""
    biXPelsPerMeter : CField
    """Structure/Union member"""
    biYPelsPerMeter : CField
    """Structure/Union member"""
class LPBITMAPINFO(_Pointer):
    """XXX to be provided"""
class RECT(RECT):
    """Structure base class"""
    def __eq__ (self, other):
        """Return self==value."""
    def __repr__ (self):
        """Return repr(self)."""
class RGBQUAD(Structure):
    """Structure base class"""
    def __repr__ (self):
        """Return repr(self)."""
    rgbBlue : CField
    """Structure/Union member"""
    rgbGreen : CField
    """Structure/Union member"""
    rgbRed : CField
    """Structure/Union member"""
    rgbReserved : CField
    """Structure/Union member"""
