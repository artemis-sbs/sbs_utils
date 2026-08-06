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
def measure_props (props, mode, avail_px, font, ar):
    """Cached front end for the per-widget natural size. See
    _measure_props_uncached for the real work and the reasoning."""
class RadioButton(Column):
    """class RadioButton"""
    def __init__ (self, tag, message, parent, value=False) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def _present (self, event):
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
    @property
    def value (self):
        ...
    @value.setter
    def value (self, v):
        ...
