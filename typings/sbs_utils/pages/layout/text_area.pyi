from sbs_utils.pages.layout.bounds import Bounds
from sbs_utils.pages.layout.column import Column
from sbs_utils.pages.widgets.control import Control
from sbs_utils.helpers import FrameContext
def get_client_aspect_ratio (cid):
    """Get the aspect ratio of the specified client's screen.
    Args:
        cid (int): The client ID.
    Returns:
        Vec3: The aspect ratio. If Vec3.z is 99, then the client hasn't set the aspect ratio."""
def get_font_size (font):
    ...
def merge_props (d):
    ...
def parse_url (text):
    ...
def split_props (s, def_key):
    ...
def to_float (text, defa):
    ...
class FaceLine(object):
    """class FaceLine"""
    def __init__ (self, text, ar) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def send_gui (self, SBS, client_id, region_tag, tag, left, top, right, bottom):
        ...
class ImageLine(object):
    """class ImageLine"""
    def __init__ (self, text, ar) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def send_gui (self, SBS, client_id, region_tag, tag, left, top, right, bottom):
        ...
class ShipLine(object):
    """class ShipLine"""
    def __init__ (self, text, ar) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def send_gui (self, SBS, client_id, region_tag, tag, left, top, right, bottom):
        ...
class TextArea(Control):
    """class TextArea"""
    def __init__ (self, tag, message) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def _present (self, event):
        ...
    def _present_simple (self, event):
        ...
    def calc (self, client_id):
        ...
    def calc_rich (self, client_id):
        ...
    def get_line_style (self, some_lines, previous):
        ...
    def get_markdown_line_style (self, some_lines, previous):
        ...
    def get_style (self, key):
        ...
    def on_message (self, event):
        ...
    def parse_header (self, header):
        ...
    def parse_style_line (self, line):
        ...
    def split_styled_lines (self, some_lines):
        ...
    def update (self, message):
        ...
    @property
    def value (self):
        ...
    @value.setter
    def value (self, message):
        ...
class TextLine(object):
    """class TextLine"""
    def __init__ (self, text, style, width, height, is_sec_end) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
