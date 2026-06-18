from ...helpers import FrameContext
from ..style import apply_control_styles
from ...pages.layout.face import Face

def gui_face(face, style=None):
    """Add a character face portrait to the current GUI layout.

    Renders the named face asset, typically used in comms panels to show the
    speaker's portrait.

    Args:
        face (str): Face asset name or property string, e.g. ``"crew/captain"``.
        style (str, optional): CSS-like style overrides. Defaults to None.

    Returns:
        Face: The layout item created.

    Example:
        gui_face("crew/captain")
    """    
    page = FrameContext.page
    task = FrameContext.task
    if page is None:
        return None
    
    tag = page.get_tag()
    layout_item = Face(tag,face)
    apply_control_styles(".face", style, layout_item, task)
    # Last in case tag changed in style
    page.add_content(layout_item, None)
    return layout_item
