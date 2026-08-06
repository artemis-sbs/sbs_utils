from sbs_utils.helpers import FrameContext
from sbs_utils.pages.layout.icon import Icon
from sbs_utils.pages.layout.icon_button import IconButton
def apply_control_styles (control_name, extra_style, layout_item, task):
    """Apply a named control style and optional overrides to a layout item.
    
    ``extra_style`` may be a raw CSS-style string (``"key:value;..."``) or
    a style name. It is applied on top of the base ``control_name`` style.
    
    Args:
        control_name (str): Base control style name.
        extra_style (str | dict | None): Additional style string, name, or
            parsed dict applied after the base style.
        layout_item (LayoutItem): Layout item to receive the style.
        task (MastAsyncTask): GUI task used for string formatting."""
def gui_icon (props, style=None):
    """Add an icon image to the current GUI layout.
    
    Renders a non-interactive icon from the atlas or media path.
    
    Args:
        props (str): Icon key, atlas name, or image property string, e.g.
            ``"icons/torpedo"`` or ``"image:icons/torpedo;color:yellow;"``.
        style (str, optional): CSS-like style overrides. Defaults to None.
    
    Returns:
        Icon: The layout item created.
    
    Example:
        gui_icon("icons/shield")
        gui_text("{shield_pct}%")"""
def gui_icon_add_atlas (name, image, left=None, top=None, right=None, bottom=None, color=None):
    """Claim an icon NAME for a cell of your own sheet.
    
        gui_icon_add_atlas("wanted", media_shared("icons/quest-sheet"), 0, 0, 64, 64)
    
    From then on every `gui_icon_name("quest.job")` draws your art - the meaning points
    at the look `wanted`, and this claims that look. Nothing that draws it changes.
    
    This is `gui_image_add_atlas(..., domain="icon")`. The domain is what separates a
    deliberate re-skin from an image that happens to be called `square`."""
def gui_icon_add_atlas_grid (image, cols, rows=None, names=None, cell=None, color=None, start=0):
    """Claim a whole sheet of icon names at once - `gui_image_add_atlas_grid` in the icon
    domain. Names are laid out row-major; a `None` entry skips a cell."""
def gui_icon_button (props, style=None):
    """Add a clickable icon button to the current GUI layout.
    
    Like ``gui_icon`` but the rendered item accepts click events.
    
    Args:
        props (str): Icon key, atlas name, or image property string, e.g.
            ``"icons/fire"`` or ``"image:icons/fire;color:red;"``.
        style (str, optional): CSS-like style overrides. Defaults to None.
    
    Returns:
        IconButton: The layout item created.
    
    Example:
        btn = gui_icon_button("icons/fire")
        gui_click(btn, on_fire_clicked)"""
def gui_icon_name (name, color=None, style=None, props=None):
    """Draw an icon by NAME rather than by sheet index.
    
        gui_icon_name("quest.job", color="#cc0")
    
    The name is resolved by `icon_names.icon_resolve`: a meaning (`quest.job`) follows
    its alias to a look, and a look is either a cell of the built-in sheet or - when a
    mission has registered that name with `gui_image_add_atlas` - a cell of its own
    sheet. The caller says what it wants; where the art comes from is not its business,
    which is what lets a consumer be written before the art exists and lets a mission
    re-skin every screen that draws it.
    
    An unknown name draws NOTHING and says so once, rather than falling back to some
    arbitrary glyph: a wrong icon is worse than a missing one, because it looks
    deliberate.
    
    Args:
        name (str): a meaning or a look - see `icon_names.icon_names()`.
        color (str, optional): tint. The built-in glyphs are white on transparent, so
            one glyph serves every state.
        style (str, optional): layout style, as for `gui_icon`.
        props (str, optional): extra icon properties appended verbatim.
    
    Returns:
        Icon | Image | None"""
