from sbs_utils.pages.layout.column import Column
from sbs_utils.helpers import FrameContext
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
def merge_props (d):
    ...
def props_display_text (props, def_key='$text'):
    """Extract the plain display text from a widget props string.
    
    The inverse of the ``$text:`...`;`` quoting that ``gui_text_escape`` and
    ``Text.update`` apply. Given ``"$text:`Hello`;font:gui-2;"`` this returns
    ``"Hello"``. Handles the unquoted form, the bare ``text:`` spelling, and a
    props string that is really just a bare label (no colon at all).
    
    This is what a measurement needs: the glyphs the engine will actually draw,
    with the style props stripped off. Returns ``""`` when there is no text."""
def split_props (s, def_key):
    ...
class Dropdown(Column):
    """class Dropdown"""
    def __init__ (self, tag, props) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def _present (self, event):
        ...
    def _set_value (self, v, repaint):
        """Select `v`, in the props string as well as in `_value`.
        
        Holding the selection only in `_value` was the other half of LM #568:
        `_present` sends `values`, so a value the props string did not know
        about never reached the screen -- and was undone the next time the
        layout was presented."""
    def measure (self, client_id, mode, avail_px, font, ar):
        """Deliberately unmeasurable -- do not "fix" this to measure the list.
        
        A dropdown's rendered width is its widest option PLUS engine-drawn
        chrome (the arrow, the border) whose size we cannot ask for. Sizing to
        the text alone would come out narrow, and because the engine does not
        clip, a narrow dropdown draws its label over its neighbour rather than
        truncating. Falling back to flex is the safe answer, and it is exactly
        what happened before content sizing existed."""
    def on_message (self, event):
        ...
    def update (self, props):
        """Replace the whole props string -- the option list AND the selection.
        
        Writes `values`, which is the string `_present` sends. It used to write
        a `props` attribute nothing reads, so `update()` -- and `gui_update()`
        with it, since that calls this -- was a silent no-op on a dropdown
        (LM #568)."""
    @property
    def value (self):
        ...
    @value.setter
    def value (self, v):
        ...
