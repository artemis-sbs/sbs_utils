from ...helpers import FrameContext, gui_text_escape
from ..style import apply_control_styles

from ...pages.layout.text import Text
from ...pages.layout.text_area import TextArea

# Re-exported for MAST authors: wrap a dynamic name/value before dropping it
# into a $text: string, e.g.  gui_text(f"$text:{gui_text_escape(ship.name)};color:red;")
# so a name containing ':' or ';' cannot inject style properties (issue #569).
__all__ = ["gui_text", "gui_text_area", "gui_text_escape"]

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

def gui_text_area(props, style=None, markdown=True, line_styles=None):
    """Add a rich text area to the current GUI layout.

    Supports Markdown-style formatting and inline image references
    (``![](image://key)``). Use for multi-line or formatted text blocks.

    Args:
        props (str): Text content or Markdown string. Supports ``{var}``
            interpolation.
        style (str, optional): CSS-like style overrides. Defaults to None.
        markdown (bool, optional): Parse the mini-markdown. Pass ``False`` to
            render lines VERBATIM - the right choice for source code, a MAST
            error dump or a raw log, where the markup rules actively corrupt the
            content: ``#`` starts a heading (so every MAST comment becomes one),
            a leading ``-`` is consumed as a bullet (``->END``), any ``[...]``
            is read as a link reference and replaces the line, and ``^`` becomes
            a newline. ``{var}`` interpolation is also skipped, since a brace in
            code is a brace. Defaults to True.
        line_styles (list, optional): One style key per line, applied in order -
            how you colorize text that is no longer being parsed. Pairs with
            ``markdown=False``. Defaults to None.

    Returns:
        TextArea: The layout item created.

    Example:
        gui_text_area("## Status\\nAll systems nominal.")
        gui_text_area("![](image://logo?scale=0.5) Mission active")
        gui_text_area(source, markdown=False, line_styles=per_line_keys)
    """
    page = FrameContext.page
    task = FrameContext.task

    # Literal text is not a template: '{' in code is a brace, not a format field.
    if markdown:
        props = task.compile_and_format_string(props)

    if page is None:
        return
    if style is None: 
        style = ""
    else:
        style = task.compile_and_format_string(style)

    layout_item = TextArea(page.get_tag(), text_sanitize(props),
                           markdown=markdown, line_styles=line_styles)
    apply_control_styles(".textarea", style, layout_item, task)

    page.add_content(layout_item, None)
    return layout_item
