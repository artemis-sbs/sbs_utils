from sbs_utils.pages.layout.column import Column
from sbs_utils.helpers import FrameContext
def get_client_aspect_ratio (cid):
    """Get the aspect ratio of the specified client's screen.
    Args:
        cid (int): The client ID.
    Returns:
        Vec3: The aspect ratio. If Vec3.z is 99, then the client hasn't set the aspect ratio."""
def merge_props (d):
    ...
def split_props (s, def_key):
    ...
class Image(Column):
    """class Image"""
    def __init__ (self, tag, file, mode=1) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def _present (self, event):
        ...
    def get_image_size (self):
        ...
    def update (self, file):
        ...
    @property
    def value (self):
        ...
    @value.setter
    def value (self, v):
        ...
