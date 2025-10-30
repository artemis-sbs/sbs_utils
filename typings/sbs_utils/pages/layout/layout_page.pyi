from sbs_utils.pages.layout.column import Column
from sbs_utils.helpers import FrameContext
from sbs_utils.pages.layout.layout import Layout
from sbs_utils.gui import Page
def get_client_aspect_ratio (cid):
    """Get the aspect ratio of the specified client's screen.
    Args:
        cid (int): The client ID.
    Returns:
        Vec3: The aspect ratio. If Vec3.z is 99, then the client hasn't set the aspect ratio."""
class LayoutPage(Page):
    """A interface class for creating GUI pages
    
        """
    def __init__ (self) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def _present (self, event):
        """Present the gui """
