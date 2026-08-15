from ...helpers import FrameContext, merge_props, split_props
from ..style import apply_control_styles
from ...pages.layout.icon import Icon


def gui_icon(props, style=None, data=None):
    """Add an icon image to the current GUI layout.

    Renders an icon from the atlas or media path. It is not clickable on its
    own, but a ``click_tag:`` in the style makes it so - which is why it can
    carry ``data`` like any other widget.

    Args:
        props (str): Icon key, atlas name, or image property string, e.g.
            ``"icons/torpedo"`` or ``"image:icons/torpedo;color:yellow;"``.
        style (str, optional): CSS-like style overrides. Defaults to None.
        data (object, optional): Arbitrary data carried by the widget, read
            back in a handler as ``__ITEM__.data`` and - when it is a dict -
            unpacked into the handler's variables. Defaults to None.

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
    layout_item.data = data
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


def gui_icon_recolor(widget, color):
    """Tint an icon that is already on screen, whatever `gui_icon_name` gave back.

    That function returns an Icon for a built-in glyph and an Image for a name a
    mission has re-skinned, and the two carry their color in different places - so a
    caller that recolored by hand would work until someone registered their own sheet,
    which is the one thing the name indirection exists to survive. Recolor, never
    rebuild: the widget keeps its tag, so the engine re-sends one glyph instead of the
    console rebuilding a row that may be under the pilot's cursor.

    Args:
        widget: the layout item from `gui_icon_name` (None is a no-op).
        color (str): the new tint.

    Returns:
        bool: whether the tint was applied.
    """
    if widget is None or not color:
        return False
    if isinstance(widget, Icon):
        props = split_props(widget.props, "icon_index")
        props["color"] = str(color)
        widget.update(merge_props(props))
        return True
    if hasattr(widget, "color"):
        widget.color = str(color)
        if not widget.is_hidden_by_script:
            widget.mark_value_dirty()
        return True
    return False


def gui_icon_add_atlas(name, image, left=None, top=None, right=None, bottom=None,
                       color=None):
    """Claim an icon NAME for a cell of your own sheet.

        gui_icon_add_atlas("wanted", media_shared("icons/quest-sheet"), 0, 0, 64, 64)

    From then on every `gui_icon_name("quest.job")` draws your art - the meaning points
    at the look `wanted`, and this claims that look. Nothing that draws it changes.

    This is `gui_image_add_atlas(..., domain="icon")`. The domain is what separates a
    deliberate re-skin from an image that happens to be called `square`.
    """
    from .image import gui_image_add_atlas
    from .icon_sheet import ICON_DOMAIN
    return gui_image_add_atlas(name, image, left, top, right, bottom, color, ICON_DOMAIN)


def gui_icon_add_atlas_grid(image, cols, rows=None, names=None, cell=None, color=None,
                            start=0):
    """Claim a whole sheet of icon names at once - `gui_image_add_atlas_grid` in the icon
    domain. Names are laid out row-major; a `None` entry skips a cell."""
    from .image import gui_image_add_atlas_grid
    from .icon_sheet import ICON_DOMAIN
    return gui_image_add_atlas_grid(image, cols, rows, names, cell, color, ICON_DOMAIN,
                                    start)


from ...pages.layout.icon_button import IconButton
def gui_icon_button(props, style=None, data=None, on_press=None, is_sub_task=False):
    """Add a clickable icon button to the current GUI layout.

    Like ``gui_icon`` but the rendered item accepts click events. Takes
    ``data`` and ``on_press`` exactly as ``gui_button`` does, so a row of icon
    buttons built in a loop can each say which row they belong to (LM #708).

    Args:
        props (str): Icon key, atlas name, or image property string, e.g.
            ``"icons/fire"`` or ``"image:icons/fire;color:red;"``.
        style (str, optional): CSS-like style overrides. Defaults to None.
        data (object, optional): Arbitrary data carried by the widget. The
            handler reads it as ``__ITEM__.data``; a dict is also unpacked
            into the handler's variables. Defaults to None.
        on_press (label | callable | Promise, optional): What to do when the
            icon is pressed. A label is jumped to; a callable is called; a
            Promise has its result set. Defaults to None - attach the handler
            with ``gui_message`` / ``gui_click`` instead.
        is_sub_task (bool, optional): When ``True`` an ``on_press`` label runs
            as an independent sub-task. Defaults to False.

    Returns:
        IconButton: The layout item created.

    Example:
        btn = gui_icon_button("icons/fire", data={"slot": i})
        gui_message(btn, on_fire_clicked)
        ///on_fire_clicked
            fire_torpedo(SHIP_ID, slot)
    """        
    page = FrameContext.page
    task = FrameContext.task
    props = task.compile_and_format_string(props)
    if page is None:
        return None
    
    tag = page.get_tag()
    layout_item = IconButton(tag,props)
    layout_item.data = data
    apply_control_styles(".icon_button", style, layout_item, task)
    # Last in case tag changed in style
    #
    # Only when there is something to run: every icon button ever built passed
    # None here, and a MessageHandler with no handler starts a sub-task on the
    # label None for each click.
    runtime_item = None
    if on_press is not None:
        from .button import MessageHandler
        runtime_item = MessageHandler(layout_item, task, on_press, is_sub_task)
    page.add_content(layout_item, runtime_item)
    return layout_item

