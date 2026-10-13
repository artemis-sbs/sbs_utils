from sbs_utils.mast.mast_node import MastNode
from sbs_utils.mast.mast_runtime_node import MastRuntimeNode
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
def mast_compile (source, mode='eval', filename=None):
    """``compile()`` for MAST expressions, with the source kept for tracebacks.
    
    Compiling against the shared ``"<string>"`` filename leaves Python with no
    source for the frame, so ``traceback.extract_tb`` reports the offending line
    as ``None`` - which is exactly the useless report a MAST author sees today.
    Compiling against a unique pseudo-filename and registering the text in
    ``linecache`` makes every traceback (eval and ``~~`` exec alike) print the
    real expression, and lets eval_code quote the WHOLE expression even when the
    deepest frame is inside some library function.
    
    An ``mtime`` of ``None`` in the linecache tuple is the documented "loaded by
    a __loader__" form: ``linecache.checkcache`` skips those, so the entry is
    never invalidated out from under us."""
def mast_node (append=True):
    ...
def mast_runtime_node (parser_node):
    ...
class AppendText(MastNode):
    """class AppendText"""
    def __init__ (self, message, if_exp, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (src, pos=0):
        ...
class AppendTextRuntimeNode(MastRuntimeNode):
    """class AppendTextRuntimeNode"""
    def enter (self, mast: 'Mast', task: 'MastAsyncTask', node: sbs_utils.mast_sbs.story_nodes.text.AppendText):
        ...
class Text(MastNode):
    """class Text"""
    def __init__ (self, message, if_exp, style_name=None, style=None, style_q=None, loc=None, compile_info=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def parse (src, pos=0):
        ...
class TextRuntimeNode(MastRuntimeNode):
    """class TextRuntimeNode"""
    def enter (self, mast: 'Mast', task: 'MastAsyncTask', node: sbs_utils.mast_sbs.story_nodes.text.Text):
        ...
