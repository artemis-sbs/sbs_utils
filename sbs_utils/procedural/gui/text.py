from ...helpers import FrameContext
from ..style import apply_control_styles

from ...pages.layout.text import Text
from ...pages.layout.text_area import TextArea

def gui_text(props, style=None):
    """Add a text label to the current GUI layout.

    Args:
        props (str): Text content or property string, e.g. ``"Hello"`` or
            ``"$text:Hello;color:white;"``. Supports ``{var}`` interpolation.
        style (str, optional): CSS-like style overrides. Defaults to None.

    Returns:
        Text: The layout item created.

    Example:
        gui_text("Hull: {hull_pct}%")
        gui_text("$text:WARNING;color:red;")
    """
    page = FrameContext.page
    task = FrameContext.task

    if page is None:
        return
    if style is None: 
        style = ""
    else:
        style = task.compile_and_format_string(style)

    props = task.compile_and_format_string(props)
    
    layout_item = Text(page.get_tag(), props)
    apply_control_styles(".text", style, layout_item, task)

    page.add_content(layout_item, None)
    return layout_item


def text_sanitize(text):
    # text = text.replace(",", "_")
    #text = text.replace(":", "_")
    return text

def gui_text_area(props, style=None):
    """Add a rich text area to the current GUI layout.

    Supports Markdown-style formatting and inline image references
    (``![](image://key)``). Use for multi-line or formatted text blocks.

    Args:
        props (str): Text content or Markdown string. Supports ``{var}``
            interpolation.
        style (str, optional): CSS-like style overrides. Defaults to None.

    Returns:
        TextArea: The layout item created.

    Example:
        gui_text_area("## Status\\nAll systems nominal.")
        gui_text_area("![](image://logo?scale=0.5) Mission active")
    """
    page = FrameContext.page
    task = FrameContext.task

    props = task.compile_and_format_string(props)

    if page is None:
        return
    if style is None: 
        style = ""
    else:
        style = task.compile_and_format_string(style)

    layout_item = TextArea(page.get_tag(), text_sanitize(props))
    apply_control_styles(".textarea", style, layout_item, task)

    page.add_content(layout_item, None)
    return layout_item
