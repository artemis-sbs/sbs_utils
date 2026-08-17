from sbs_utils.agent import Agent
from sbs_utils.pages.layout.bounds import Bounds
from sbs_utils.pages.layout.clickable import Clickable
from sbs_utils.pages.layout.dirty import Dirty
from sbs_utils.helpers import FrameContext
def apply_col_width (item, width):
    """Set `default_width` / `square` from a col-width value, keeping the two
    MUTUALLY EXCLUSIVE.
    
    `col-width: square` and an explicit width are two answers to one question,
    and holding both is an illegal state rather than a combination:
    `_resolve_col_widths` counts a square column in `squares` AND, if it also
    carries a width, in `assigned_cols`/`assigned_space` -- so `need_assigned`
    subtracts it twice and the row reserves its space twice over. The engine does
    not clip, so the surplus is drawn over and outside its neighbours.
    
    Setting either therefore clears the other. This does change behaviour for a
    screen that puts a col-width on an already-square widget (a face, an icon):
    it now gets the width it asked for, instead of the double-count."""
def backdrop_props (image, color, layer=None):
    """Props for a background / border fill.
    
    `layer` None keeps the historic 1000, which is UNDER content -- so a
    backdrop cannot hide a neighbour's spill unless the author raises it."""
def invoke_message_cb (cb, event, item):
    """Call whatever is in an `on_message_cb` slot: chain, object, or function."""
class Column(object):
    """class Column"""
    def __init__ (self, left=0, top=0, right=0, bottom=0) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def _post_present (self, event):
        ...
    def _pre_present (self, event):
        ...
    def _present (self, event):
        ...
    @property
    def bounds (self):
        ...
    @bounds.setter
    def bounds (self, v):
        ...
    def calc (self, client_id):
        ...
    @property
    def click_tag (self):
        ...
    @click_tag.setter
    def click_tag (self, v):
        ...
    def get_cascade_props (self, font=False, color=False, justify=False, layer=False, message=None):
        ...
    def get_color (self):
        ...
    def get_font (self):
        ...
    def get_justify (self):
        ...
    def get_layer (self):
        ...
    def get_variable (self, default=None):
        ...
    def invalidate_regions (self):
        ...
    @property
    def is_hidden (self):
        """Use :func:`is_hidden` only to check if the layout item is currently visible to the user.
        It checks both :func:`_show` and :func:`_is_shown`.
        If either of these are False, will return True."""
    @property
    def is_hidden_by_script (self):
        """Hidden because the SCRIPT asked -- show() / gui_hide().
        
        This is the question the LAYOUT pass must ask. :func:`is_hidden` also
        folds in :func:`_is_shown`, which is an OUTPUT of the present pass, so
        reading it during calc makes geometry depend on the previous frame:
        a control clipped last frame is dropped from the width split and comes
        back the wrong size, and gui_show() cannot fix it because _show never
        changed."""
    def is_message_for (self, event):
        """Used by MessageTrigger i.e. gui_message to know if message is for this object
        
        Args:
            event (EVENT): the engine event
        
        Returns:
            bool: if the gui_message MessageTrigger should be True"""
    def mark_layout_dirty (self):
        ...
    def mark_value_dirty (self, force_layout=False):
        """Dirty-mark after this widget's VALUE changed.
        
        Content sizing is what turns a text change into a LAYOUT change, and
        this is where that cost is contained. A full subtree re-calc happens
        only when the column is content-sized AND its measured size actually
        moved -- the common case (text changes, width does not) stays on the
        cheap visual-only path, and a layout using no content keywords never
        takes the expensive branch at all, since content_sized defaults False.
        
        The re-measure it costs is memoized and far cheaper than the calc() it
        avoids."""
    def mark_visual_dirty (self):
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
    def measured_size_changed (self):
        """True if re-measuring now would give a different size.
        
        Conservative: anything unknown returns True, so the layout is rebuilt
        rather than left stale."""
    def note_measured (self, mode, avail_px, font, ar, size):
        """Record what a content measurement was taken with, and what it gave.
        
        Layout.calc calls this for any column it measured, so a later value
        change can re-measure under identical conditions and tell whether the
        size actually moved."""
    def on_begin_presenting (self, client_id):
        ...
    def on_end_presenting (self, client_id):
        ...
    def on_message (self, event):
        ...
    @property
    def parent (self):
        ...
    @parent.setter
    def parent (self, v):
        ...
    def present (self, event):
        ...
    def represent (self, event):
        ...
    def set_border (self, border):
        ...
    def set_bounds (self, bounds) -> None:
        ...
    def set_col_width (self, width):
        ...
    def set_margin (self, margin):
        ...
    def set_padding (self, padding):
        ...
    def set_row_height (self, height):
        ...
    def show (self, _show):
        """Use to force the gui element to be hidden, or to allow it to be seen.
        If False - the gui element will always be hidden.
        If True - will be visible assuming that it is within the bounds of its parent.
        
        Args:
            _show (bool): Should the element be visible."""
    def update (self, props):
        ...
    def update_variable (self):
        ...
    @property
    def value (self):
        ...
    @value.setter
    def value (self, a):
        ...
