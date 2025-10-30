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
    def get_style (self, key):
        ...
    def on_message (self, event):
        ...
    def parse_header (self, header):
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
