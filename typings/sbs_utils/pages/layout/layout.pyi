from sbs_utils.pages.layout.bounds import Bounds
from sbs_utils.pages.layout.clickable import Clickable
from sbs_utils.pages.layout.column import Column
from sbs_utils.mast.parsers import ContentSize
from sbs_utils.mast.parsers import LayoutAreaParser
from sbs_utils.pages.layout.dirty import Dirty
from sbs_utils.helpers import FrameContext
from sbs_utils.pages.layout.hole import Hole
from enum import IntEnum
from sbs_utils.pages.layout.row import Row
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
def calc_bounds (att, aspect_ratio, font_size):
    ...
def calc_float_attribute (name, col, row, sec, aspect_ratio_axis, font_size):
    ...
def cascade_attribute (name, col, row, sec):
    ...
def col_box_width (col, aspect_ratio, font_size):
    """Horizontal margin + border + padding of a column, in percent.
    
    A measured natural size is the size of the CONTENT. The column also has to
    fit its own box model, so this is added before the width is used as a size
    or as a floor. Miss it and a widget with `margin: 3,3,3,3` asks for exactly
    its text width, then draws that text into what is left after 6% of margin
    -- which is the shape of LM issue 672's first row.
    
    Computed from the *_style values because col.margin/border/padding are not
    filled in until the presentation pass, which runs after this."""
def effective_font (col, row_font):
    """The font a column renders with.
    
    Note the precedence is ROW-first, not column-first: a row font overrides
    the column's own default_font. That is long-standing behaviour and is
    relied on by existing layouts, so it is preserved exactly. It is hoisted
    into one place only so the width pass and the presentation pass can never
    drift apart on it -- a measure pass that used a different font than the
    renderer would mis-size every cell."""
def get_client_aspect_ratio (cid):
    """Get the aspect ratio of the specified client's screen.
    Args:
        cid (int): The client ID.
    Returns:
        Vec3: The aspect ratio. If Vec3.z is 99, then the client hasn't set the aspect ratio."""
def get_font_size (font):
    ...
def invoke_message_cb (cb, event, item):
    """Call whatever is in an `on_message_cb` slot: chain, object, or function."""
def is_out_of_bounds (child, parent, tolerance=0.0):
    """Check if the child's bounds are within the parent's bounds, with an acceptable tolerance.
    
    This is a separate check from is_hidden() or equivalents. It shouldn't be used in scripting at all, it should be used in lower-level python to ensure that a child element is only visible when within the bounds its parent.
    
    Does not make any changes to anything, is purely a helper function.
    
    Args:
        child (layout_item): The child layout item
        parent (layout_item): The parent layout item
        tolerance (float, optional): The amount that the child is allowed to be outside its parent and still be visible. Default is 0.0.
    
    Returns:
        bool: True if it is out of bounds, False if it is within bounds."""
def pct_to_px_x (pct, ar):
    """Percent of region width -> pixels, for this client's aspect ratio."""
def px_to_pct_x (px, ar):
    """Pixels -> percent of region width, for this client's aspect ratio."""
def resolved_size (value):
    """A resolved size as a number, or None when it is not one yet.
    
    calc_float_attribute returns either a percentage or a ContentSize marker.
    Call sites that do arithmetic use this to fall back to flex sizing for a
    content value they cannot yet resolve, instead of letting a marker reach
    a subtraction."""
class Layout(Clickable):
    """class Layout"""
    def __init__ (self, tag=None, rows=None, left=0, top=0, right=100, bottom=50, region_type=<RegionType.SECTION_AREA_ABSOLUTE: 0>) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def _apply_clipping (self):
        """Decide which children are clipped out of view.
        
        This is a LAYOUT-time step, not a drawing one. `_is_shown` is derived
        purely from geometry, so it belongs to the pass that decides geometry.
        Computing it while drawing made it an OUTPUT of the present pass that
        the next layout pass then read back -- geometry went stale by a frame,
        a control clipped last frame was dropped from the width split, and
        gui_show() could not put it right because `_show` never changed.
        
        Top-down, after the whole tree has been laid out: a child's verdict
        depends on its parent's, so the parent must be decided first. Runs over
        EVERY row, including script-hidden ones that calc() filtered out of the
        layout loop -- their columns still have to be told, or they draw at
        their own stale bounds inside a row that is not there."""
    def _content_row_height (self, row, bounds_area, aspect_ratio, row_font, mode, client_id, provisional_height):
        """Height for a `row-height: content` row, breaking the square cycle.
        
        Squares are sized from the ROW HEIGHT and they CONSUME WIDTH, while a
        content height is measured at the column widths. So with a square in
        the row: height <- content <- widths <- square_width <- height. A real
        cycle, not just an ordering problem.
        
        Resolved in a bounded, deterministic way:
        
          * no squares (the overwhelmingly common case) -- widths do not depend
            on the row height at all, so one pass is exact.
          * squares present -- measure once at a PROVISIONAL height (what the
            row would have got as a flex row), then once more at the height
            that produced. Stop there. Column widths may shift slightly on the
            second pass because square_width changed; converging further is not
            worth the measurements. Documented, not silently approximate."""
    def _measure_row_height (self, row, row_bounds_area, aspect_ratio, row_font, mode, client_id):
        """Natural height of `row` in percent, or None if nothing measurable.
        
        Height depends on WIDTH -- text wraps to the width it is given -- so the
        columns are resolved first and each is measured at the width it will
        actually get.
        
        Squares are excluded from the maximum on purpose. A square's height
        comes FROM the row height, so letting it contribute would be circular.
        A row of nothing but squares (or unmeasurable widgets) therefore has no
        natural height at all and returns None, falling back to flex."""
    def _post_present (self, event):
        ...
    def _pre_present (self, event):
        ...
    def _present (self, event):
        ...
    def _raise_flex_to_floors (actual_cols, widths, auto_floor, flex_width):
        """Push `auto` columns up to their min-content, paid for by the slack
        in the other flex columns.
        
        This is the LM issue 672 behaviour. Every flex column starts on the
        even split; any `auto` column whose content needs more than that takes
        it from the flex columns that have room to give, down to their own
        floor (0 for a plain flex column, min-content for another `auto`).
        
        Deliberately a single redistribution rather than an iteration to
        convergence: it fixes the reported case (a long string beside short
        ones) without turning every row into a solver. When there is not
        enough slack to satisfy every floor, each `auto` column gets a
        proportional share of what was available -- the issue's own "at some
        point there just isn't enough room" case."""
    def _resolve_col_widths (self, row, row_bounds_area, aspect_ratio, row_font, client_id=None):
        """Decide how wide each visible column in `row` gets to be.
        
        Returns (actual_cols, col_widths, square_width, square_height), where
        col_widths is parallel to actual_cols and holds the width BEFORE the
        square override and Hole donation are applied. None if the row has no
        visible columns.
        
        Split out of calc() so width can be resolved independently of the
        presentation pass. Content-sized rows need their columns' widths before
        their height can be measured (text wraps to the width it is given), and
        that ordering is impossible while the two are interleaved.
        
        Behaviour is deliberately unchanged here -- see
        tests/test_layout_geometry_golden.py, which pins every rect this
        produces across a corpus of layouts and three aspect ratios.
        
        Note squares are sized from row_bounds_area.HEIGHT, so column width
        depends on row height whenever a square is present. That knot is why a
        content row containing squares has to be resolved in two steps."""
    def add (self, row: sbs_utils.pages.layout.row.Row):
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
    @property
    def color (self):
        ...
    @color.setter
    def color (self, v):
        ...
    @property
    def drawing_region_tag (self):
        ...
    @property
    def font (self):
        ...
    @font.setter
    def font (self, v):
        ...
    def get_content_bounds (self, merge_self):
        ...
    def get_layer (self):
        ...
    def invalidate_all (self):
        ...
    def invalidate_children (self):
        ...
    def invalidate_regions (self):
        ...
    @property
    def is_hidden (self):
        """Use `is_hidden` only to check if the layout item is currently visible to the user.
        It checks both `_show` and `_is_shown`.
        If either of these are False, will return True."""
    @property
    def is_hidden_by_script (self):
        """Hidden because the SCRIPT asked -- show() / gui_hide().
        
        This is the question the LAYOUT pass must ask; see
        `Column.is_hidden_by_script`."""
    def is_message_for (self, event):
        """Used by MessageTrigger i.e. gui_message to know if message is for this object
        
        Args:
            event (EVENT): the engine event
        
        Returns:
            bool: if the gui_message MessageTrigger should be True"""
    @property
    def justify (self):
        ...
    @justify.setter
    def justify (self, v):
        ...
    @property
    def layer (self):
        ...
    @layer.setter
    def layer (self, v):
        ...
    def mark_layout_dirty (self):
        ...
    def mark_visual_dirty (self):
        ...
    def measure (self, client_id, mode, avail_px, font, ar):
        """Natural size of a nested section, by recursing into its children.
        
        A sub-section is a Layout stored AS a column, so it has to answer the
        same question its own columns do. Natural width is the widest row (the
        sum of that row's columns); natural height is the sum of row heights.
        
        WIDTH-AWARE when the caller knows one. If `avail_px` is given, each row
        is measured at that width, so text that will wrap is counted as the
        several lines it will actually occupy. Reporting the UNWRAPPED height
        here is what let a nested section ask its parent for less room than its
        content needs -- the parent then had no reason to raise its row, and the
        section's own rows fought over a box that was too small, drawing over
        each other (LM issue672's green panel).
        
        When `avail_px` is None the parent genuinely has not decided a width
        yet, and the natural (unwrapped) size is the only honest answer --
        guessing a width there would bake in a wrap that may never happen.
        
        Returns None when nothing inside could be measured, so an unmeasurable
        sub-section falls back to flex like any other unmeasurable column."""
    def measured_size_changed (self):
        ...
    def note_measured (self, mode, avail_px, font, ar, size):
        """Same contract as Column.note_measured -- see the duck-typing note in
        __init__."""
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
    def print_bounds (self, bounds=None):
        ...
    def rebuild (self):
        ...
    def region_begin (self, client_id):
        ...
    def region_end (self, client_id):
        ...
    @property
    def region_tag (self):
        ...
    @region_tag.setter
    def region_tag (self, t):
        ...
    def represent (self, event):
        ...
    def resize_to_content (self):
        ...
    def set_border (self, border):
        ...
    def set_bounds (self, bounds):
        ...
    def set_col_width (self, width):
        ...
    def set_margin (self, margin):
        ...
    def set_orientation (self, s):
        """Set the orientation of the layout element.
        Valid values:
            "TB" - Top to Bottom
            "BT" - Bottom to Top"""
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
class RegionType(IntEnum):
    """Enum where members are also (and must be) ints"""
    REGION_ABSOLUTE : 100
    REGION_RELATIVE : 200
    SECTION_AREA_ABSOLUTE : 0
