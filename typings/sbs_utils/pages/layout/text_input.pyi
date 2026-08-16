from sbs_utils.pages.layout.column import Column
from sbs_utils.helpers import FrameContext
def apply_overflow (props, bounds, policy, cascade_font=None):
    """Adjust a props string so it honours `policy` inside `bounds`.
    
    Returns (props, draw). `draw` is False only for `hide`, when the text
    genuinely does not fit.
    
    Called at PRESENT time, because that is the first moment the final rect is
    known. Everything it does is expressible through send_gui_*: change the
    font, change the string, or do not send. It cannot ask the engine to clip,
    because the engine has no such thing."""
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
def measure_props (props, mode, avail_px, font, ar):
    """Cached front end for the per-widget natural size. See
    _measure_props_uncached for the real work and the reasoning."""
class TextInput(Column):
    """class TextInput"""
    def __init__ (self, tag, props) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def _present (self, event):
        ...
    def _sanitize (v):
        ...
    def _take_props (self, props):
        """Split a props string into the VALUE and everything else.
        
        Shared by __init__ and update() so a widget built from a props string
        and one restyled by gui_update() can never disagree about how that
        string was read."""
    def _text_prop (self):
        ...
    def measure (self, client_id, mode, avail_px, font, ar):
        """Natural size of this column's content, in PERCENT, or None.
        
        Returns (width_pct, height_pct) for `col-width: content` and
        `row-height: content` to size against, or None when the widget has no
        measurable content.
        
        None is the important default. Every existing subclass inherits it, so
        adding content sizing changes NO existing layout until a subclass opts
        in by overriding. A column that cannot be measured -- an engine-owned
        console widget, a 3D ship, engine-drawn chrome -- falls back to flex,
        which is exactly today's behaviour. It must never fall back to 0: a
        section-level `col-width: content` cascades to every column in it, and
        zero-width widgets would be a far worse failure than an unsized one.
        
        Args:
            client_id: the client being laid out.
            mode:      a ContentSize -- content, min-content or max-content.
            avail_px:  width available to this column in pixels, or None when
                       it is not known yet. Needed because wrapped height
                       depends on the width the text is given.
            font:      the cascaded font, already resolved by the caller (see
                       effective_font). A font in the widget's own props string
                       overrides it, since present() appends the cascade AFTER
                       the message and the engine takes the last value.
            ar:        this client's aspect ratio, for the px -> percent
                       conversion."""
    def on_message (self, event):
        ...
    def update (self, props):
        """Restyle / re-value this input from a props string.
        
        Without this override Column.update's `pass` ran, so gui_update() on a
        gui_input was a silent no-op: the widget was re-sent with its OLD props
        and the author's new font / desc / value never arrived.
        
        A props string carrying no `text:` leaves the VALUE alone. The text in
        a typein belongs to the player, and restyling the box must not wipe
        what someone is in the middle of typing -- which is why this cannot
        just forward to the value setter the way Button.update does."""
    @property
    def value (self):
        ...
    @value.setter
    def value (self, v):
        ...
