from sbs_utils.helpers import FrameContext
from sbs_utils.pages.layout.text import Text
from sbs_utils.pages.layout.text_area import TextArea
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
def gui_text (props, style=None):
    """Add a text label to the current GUI layout.
    
    Args:
        props (str): Text content or property string, e.g. ``"Hello"`` or
            ``"$text:Hello;color:white;"``. Supports ``{var}`` interpolation.
        style (str, optional): CSS-like style overrides. Defaults to None.
    
    Returns:
        Text: The layout item created.
    
    Example:
        gui_text("Hull: {hull_pct}%")
        gui_text("$text:WARNING;color:red;")"""
def gui_text_area (props, style=None, markdown=True, line_styles=None, on_link=None, link_resolver=None):
    """Add a rich text area to the current GUI layout.
    
    Supports Markdown-style formatting: headings (``##+``/``##-`` fold), lists,
    pipe tables, gauges (``[Energy](gauge://946?max=1000)``), links
    (``[Text](ref://key)``) and pictures. A picture ALONE on its line
    (``![](image://key?scale=0.5)``, ``face://``, ``ship://``) is drawn full size;
    followed by text it LEADS the line - a square ``size=N`` text lines tall with
    the text beside it, and at the start of a ``-`` item it is the bullet. Use for
    multi-line or formatted text blocks.
    
    **Choices.** A line that is only ``[Display](signal://name?key=value)`` is a
    button. Lines of them next to each other are one group, drawn as flat buttons
    that share a row while they fit and wrap when they do not. Clicking one
    replaces the whole group with the choice made (so the document reads as the
    story so far) and emits ``name`` with the query as variables, plus
    ``SIGNAL_CHOICE`` (the words), ``SIGNAL_CLIENT_ID`` and ``SIGNAL_ITEM`` (this
    area). Continue the story from the route with
    ``gui_text_area_append(SIGNAL_ITEM, text)``. A line
    ``[](choices://?layout=stack&fill=#234)`` above a group restyles the groups
    after it (``fill``, ``text``, ``chosen_fill``, ``chosen_text``, ``font``,
    ``pad_x``, ``pad_y``, ``gap``, ``layout`` = ``flow`` | ``stack``).
    
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
        on_link (callable, optional): ``fn(key, widget)``, called when a
            ``[Text](ref://key)`` link is clicked - a whole-line link or a table
            cell. Defaults to None.
        link_resolver (callable | dict, optional): what a link NAVIGATES to -
            ``fn(key) -> new text`` or a ``{key: text}`` dict. The area swaps to
            that text in place (back to the top). None, or a key it does not know,
            leaves the text alone. Defaults to None.
    
    Returns:
        TextArea: The layout item created.
    
    Example:
        gui_text_area("## Status\nAll systems nominal.")
        gui_text_area("![](image://logo?scale=0.5)")
        gui_text_area("![](icon://check.on?color=#8f8) Mission active")
        gui_text_area(source, markdown=False, line_styles=per_line_keys)"""
def gui_text_area_append (text_area, text, sep='\n\n'):
    """Add text to the end of a text area - how a story continues after a choice.
    
    The area repaints itself and, when the reader is at the bottom, stays there.
    Use this rather than ``area.value += text``: ``value`` reads back as a list of
    lines. The text is not ``{var}``-formatted here; format it before passing it.
    
    Args:
        text_area (TextArea): the area, e.g. ``SIGNAL_ITEM`` in a choice's route.
        text (str): markdown to add, choices included.
        sep (str, optional): what goes between. A blank line by default, so the
            new text starts a paragraph.
    
    Returns:
        TextArea: the area.
    
    Example:
        //shared/signal/lp_pick
            gui_text_area_append(SIGNAL_ITEM, next_scene_text(pick))"""
def gui_text_escape (s):
    """Quote a dynamic value for safe inclusion as a ``$text:`` style value.
    
    Wraps ``s`` in backticks so any ``:`` or ``;`` it contains is treated as
    literal text by the style parser rather than a style property (issue #569).
    A literal backtick -- the quoting delimiter itself -- is stripped. An empty
    or ``None`` value returns ``""`` so the caller emits ``$text:;`` with no
    stray backtick in the box (issue #641).
    
    Use this ONLY on the dynamic value, e.g. ``f"$text:{gui_text_escape(name)};color:red;"``
    -- never on a whole authored props string, so the author's own ``:``/``;``
    styling is left untouched."""
def gui_text_literal (text):
    """``text`` made safe to hand to a widget that fills ``{name}`` in what it is given.
    
    `gui_text_area` treats its text as a template: `{ship}` is looked up and filled in.
    That is right for a string a script wrote and wrong for a line an AUTHOR wrote - a
    spoken line in an .amd file, a message from home. `Call me {Captain}, everyone does.`
    is a `NameError` against the screen's own `await gui()`, and the console that was
    drawing it stops drawing. Seen in the engine, 2026-10-03.
    
    Pass prose through this first. The braces come out the other side as braces."""
def text_sanitize (text):
    ...
