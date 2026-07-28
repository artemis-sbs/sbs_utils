from ...helpers import FrameContext
from ..style import apply_control_styles
from ...pages.layout.icon import Icon


def gui_icon(props, style=None):
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
        gui_text("{shield_pct}%")
    """        
    page = FrameContext.page
    task = FrameContext.task
    props = task.compile_and_format_string(props)
    if page is None:
        return None
    
    tag = page.get_tag()
    layout_item = Icon(tag,props)
    apply_control_styles(".icon", style, layout_item, task)
    # Last in case tag changed in style
    page.add_content(layout_item, None)
    return layout_item

def gui_icon_name(name, color=None, style=None, props=None):
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
        Icon | Image | None
    """
    from .icon_sheet import icon_resolve
    from .image import gui_image, IMAGE_KEEP_ASPECT_CENTER
    index, atlas_key = icon_resolve(name)
    if index is None and atlas_key is None:
        from ..execution import log
        log(f"no icon named {name!r} - nothing drawn", "gui", "warning")
        return None
    if atlas_key is not None:
        # The KEY, never a props string: ImageAtlas parses only image and color out of
        # one of those, so a sub_rect would be dropped and the whole sheet drawn.
        widget = gui_image(atlas_key, style, IMAGE_KEEP_ASPECT_CENTER, color)
        if widget is not None:
            # Lay out like the icon it stands in for - a square column, sized by the row
            # height - so re-skinning a name cannot shift a layout.
            widget.square = True
        return widget
    parts = [f"icon_index:{index}"]
    if color:
        parts.append(f"color:{color}")
    if props:
        parts.append(props.strip().strip(";"))
    return gui_icon(";".join(parts) + ";", style)


from ...pages.layout.icon_button import IconButton
def gui_icon_button(props, style=None):
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
        gui_click(btn, on_fire_clicked)
    """        
    page = FrameContext.page
    task = FrameContext.task
    props = task.compile_and_format_string(props)
    if page is None:
        return None
    
    tag = page.get_tag()
    layout_item = IconButton(tag,props)
    apply_control_styles(".icon_button", style, layout_item, task)
    # Last in case tag changed in style
    page.add_content(layout_item, None)
    return layout_item

