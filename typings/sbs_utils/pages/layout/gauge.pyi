from sbs_utils.pages.layout.column import Column
from sbs_utils.helpers import FrameContext
def _flag (v):
    ...
def _fmt (v):
    """946.0 -> "946", 0.25 -> "0.25"."""
def _num (v, default):
    ...
def gauge_color (spec):
    ...
def gauge_fraction (spec):
    """0..1. Out-of-range values (the engine shows "-45 / 8") clamp the BAR;
    the number printed is still the raw value."""
def gauge_has_text (spec):
    ...
def gauge_height_px (spec):
    """Natural height: one line of text (if any) plus the bar."""
def gauge_send (SBS, client_id, region_tag, tag, left, top, right, bottom, spec, ar, layer=None, justify='left'):
    """Draw one gauge into a rect (percent units, like every send_gui_*).
    
    `justify` places a label that stands ALONE (the ENGN cell is centred by its
    column); a label with a value is always label-left, value-right, the way the
    engine lays out "Energy ...... 946"."""
def gauge_spec (value, max=100, label='', show=None, warn=None, crit=None, color=None, font='gui-2', invert=False):
    """Normalise gauge inputs into one dict. Nothing here raises: a bad number
    costs that number (it falls back to a default), not the whole panel.
    
    `invert` is for a value where MORE is WORSE - wear, heat, damage taken. The bar
    still grows with the value; only the colors turn round: green while low, yellow
    past `1 - warn`, red past `1 - crit`, and over max it is red, not tuned cyan."""
def gauge_spec_from_url (urn, label='', font='gui-2'):
    """`946?max=1000&show=frac&warn=0.4&invert=1` (after `gauge://`) -> spec."""
def gauge_value_text (spec):
    ...
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
def measure_line_height (font, text):
    """Height in PIXELS one line OCCUPIES, or None if unmeasurable.
    
    This deliberately does NOT call sbs.get_text_line_height. That function
    returns the INK EXTENT -- how tall the glyphs themselves are -- not how much
    vertical space a line consumes. For gui-2 it reports 13px where a drawn line
    actually occupies 24px, so every row sized from it came out ~45% short.
    Because the engine does not clip, short rows do not truncate, they overdraw
    whatever is beneath them.
    
    Measured in the engine with missions/layout_probe -> "Wrap Ruler": the same
    sentence at shrinking widths drew 2/3/4 lines in exactly 48/72/96px, so the
    advance is exactly block_height / lines with no constant term. Asking for a
    single unwrapped line therefore gives the true advance, and it agrees with
    the nominal _FONT_SIZES table for every font -- which is the second,
    independent confirmation that that table is real line occupancy.
    
    `text` stays part of the key on purpose: the engine may vary line height
    with the glyphs present, and encoding the mock's belief that it does not
    would bake a mock assumption into the library."""
def measure_line_width (font, text):
    """Width in PIXELS of one unwrapped line, or None if unmeasurable."""
def px_to_pct_x (px, ar):
    """Pixels -> percent of region width, for this client's aspect ratio."""
def px_to_pct_y (px, ar):
    """Pixels -> percent of region height, for this client's aspect ratio."""
class Gauge(Column):
    """`gui_gauge` - a gauge as a layout widget, for values that change often.
    
    `update()` repaints only this widget (visual-dirty); the text area host would
    re-parse and re-send its whole document for the same change."""
    def __init__ (self, tag, value, max=100, label='', show=None, warn=None, crit=None, color=None, invert=False) -> None:
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
    def spec (self):
        ...
    def update (self, value=None, max=None, label=None, color=None):
        """Change any of value / max / label / color and repaint. Only what is
        passed changes."""
    @property
    def value (self):
        ...
    @value.setter
    def value (self, v):
        ...
