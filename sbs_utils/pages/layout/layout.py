from ...gui import get_client_aspect_ratio
from ...helpers import FrameContext
from ...message_chain import invoke_message_cb
from ...mast.parsers import LayoutAreaParser, ContentSize, MIN_CONTENT, AUTO

from enum import IntEnum
from .bounds import Bounds, is_out_of_bounds
from .hole import Hole
from .measure import pct_to_px_x, px_to_pct_x, DEFAULT_FONT, backdrop_props, backdrop_tag
# for type hints
from .row import Row 
from .column import Column, apply_col_width
from .dirty import Dirty

import weakref

#
# When True, a row or column with no explicit size behaves as `auto`:
# still flex, but never squeezed below its own content. This is the LM
# issue 672 request applied globally -- a long string beside short ones grows,
# and its roomier neighbours give way, with nothing annotated.
#
# It is a BEHAVIOUR CHANGE for every existing layout, which is why it is a
# single switch: set it False to restore the historical pure-FILL default.
#
# Cost, measured rather than assumed: the extra measurement is ~0.58ms per
# repaint in the engine (1015 calls at 0.57us, from missions/font_measure)
# against ~6ms of layout arithmetic. Unmeasurable widgets return None and stay
# plain flex, so the added work is proportional to how much TEXT is on screen.
#
AUTO_DEFAULT = True

        

def calc_float_attribute(name, col, row, sec, aspect_ratio_axis, font_size):
    att = None
    if col is not None and hasattr(col, name)and getattr(col, name, None) is not None:
        att = getattr(col, name, None)
    elif row is not None and hasattr(row, name) and getattr(row, name, None) is not None:
        att = getattr(row, name, None)
    elif sec is not None and hasattr(sec, name) and getattr(sec, name, None) is not None:
        att = getattr(sec, name, None)

    if att is not None:
        #
        # A content size is a marker, not an expression -- it cannot be
        # resolved without the widgets, so hand it back for calc to interpret.
        # This check must come BEFORE the float test, since compute() would
        # blow up on it. One identity comparison per resolution is the entire
        # cost content sizing imposes on a layout that does not use it.
        #
        if att.__class__ is ContentSize:
            return att
        if not isinstance(att, float):
            return LayoutAreaParser.compute(att, None,aspect_ratio_axis, font_size)
    return att


def effective_font(col, row_font):
    """The font a column renders with.

    Note the precedence is ROW-first, not column-first: a row font overrides
    the column's own default_font. That is long-standing behaviour and is
    relied on by existing layouts, so it is preserved exactly. It is hoisted
    into one place only so the width pass and the presentation pass can never
    drift apart on it -- a measure pass that used a different font than the
    renderer would mis-size every cell.
    """
    return row_font if row_font is not None else col.default_font


#
# Slack added to a measured CONTENT width, in pixels.
#
# A content width is the exact width the text needs -- so a column sized to it
# has ZERO room to spare, and anything that shaves a fraction off at the engine
# boundary (percent -> pixel rounding, an inclusive-vs-exclusive wrap test, a
# rect computed through one more nested section) tips the line into wrapping.
# Because the engine does not clip, that wrapped line is drawn ON TOP of the row
# below: LM issue672's "New Row1 is longer" overdrawing "New Row2".
#
# The costs are wildly asymmetric, which is what decides the default. Two pixels
# too wide is invisible. One pixel too narrow is an extra line drawn over a
# neighbour. So round the author's way.
#
CONTENT_WIDTH_SLACK_PX = 2


def col_box_width(col, aspect_ratio, font_size):
    """Horizontal margin + border + padding of a column, in percent.

    A measured natural size is the size of the CONTENT. The column also has to
    fit its own box model, so this is added before the width is used as a size
    or as a floor. Miss it and a widget with `margin: 3,3,3,3` asks for exactly
    its text width, then draws that text into what is left after 6% of margin
    -- which is the shape of LM issue 672's first row.

    Computed from the *_style values because col.margin/border/padding are not
    filled in until the presentation pass, which runs after this.
    """
    total = 0.0
    for style in (col.margin_style, col.border_style, col.padding_style):
        if style is None:
            continue
        b = calc_bounds(style, aspect_ratio, font_size)
        if b is not None:
            total += b.left + b.right
    return total


def resolved_size(value):
    """A resolved size as a number, or None when it is not one yet.

    calc_float_attribute returns either a percentage or a ContentSize marker.
    Call sites that do arithmetic use this to fall back to flex sizing for a
    content value they cannot yet resolve, instead of letting a marker reach
    a subtraction.
    """
    return None if value.__class__ is ContentSize else value


def cascade_attribute(name, col, row, sec):
    att = None
    if col is not None and hasattr(col, name) is not None:
        att = getattr(col, name, None)
    elif row is not None and hasattr(row, name) is not None:
        att = getattr(row, name, None)
    elif sec is not None and hasattr(sec, name) is not None:
        att = getattr(sec, name, None)

    return att


# def calc_bounds_attribute(name, col, row, sec, aspect_ratio, font_size):
#     att = None
#     if col is not None and hasattr(col, name) is not None:
#         att = getattr(col, name, None)
#     elif row is not None and hasattr(row, name) is not None:
#         att = getattr(row, name, None)
#     elif sec is not None and hasattr(sec, name) is not None:
#         att = getattr(sec, name, None)

#     return calc_bounds(att, aspect_ratio, font_size)

def calc_bounds(att, aspect_ratio, font_size):
    if att is not None:
        if not isinstance(att, Bounds):
            i = 1
            values=[]
            for ast in att:
                if i >0:
                    ratio =  aspect_ratio.x
                else:
                    ratio =  aspect_ratio.y
                i=-i
                if ratio == 0:
                    ratio = 1
                values.append(LayoutAreaParser.compute(ast, None,ratio,font_size))
            return Bounds(*values)
    return att
                
# NOMINAL font sizes for `em` arithmetic only. NOT a measurement -- these agree
# with neither the engine nor the mock's real metrics, and must never be used to
# size text (see pages/layout/measure.py, which asks the engine instead).
_FONT_SIZES = {           # MIN  2k 4k
    "smallest": 18,       # LB   -- --
    "gui-1": 22,          # BD   LB --
    "gui-2": 24,          # H3   BD LB
    "gui-3": 28,          # H2   H3 BD
    "gui-4": 32,          # H1   H2 H3
    "gui-5": 36,          # TT   H1 H2
    "gui-6": 52,          # __   TT H1/TT
}


# What an UNSET font is worth in em arithmetic, single-sourced from the
# render-confirmed default font so the two cannot drift apart again.
#
# This was a hardcoded 30 while the default font is gui-2 (24) -- a real bug,
# not a harmless inconsistency: `1em` on an unfonted row reserved 25% more
# height than one line of that row's own font needs.
#
# Fixing it removes slack that some layouts were unknowingly relying on. The
# shape that breaks is a row sized in ems whose CHILD declares a bigger font:
#
#     gui_row("row-height: 1em;")              # row: no font -> 24
#     gui_text("$text:{name};font:gui-3;")     # text: draws at 28 -> spills
#
# That was always mis-authored -- the row was never asking for enough height,
# the old 30 just happened to cover it. The fix at the call site is to declare
# the font on the row, or to use `row-height: content` (or auto), which measures
# the real text instead of approximating it in nominal ems.
_DEFAULT_FONT_SIZE = _FONT_SIZES.get(DEFAULT_FONT, 30)


def get_font_size(font):
    # Hot: called per section, per row and per column on every calc. The table
    # used to be rebuilt as a dict literal on each of those calls.
    if font is None:
        return _DEFAULT_FONT_SIZE
    size = _FONT_SIZES.get(font)
    if size is not None:                  # already lower-cased and trimmed
        return size
    return _FONT_SIZES.get(font.strip().lower(), _DEFAULT_FONT_SIZE)

class RegionType(IntEnum):
    SECTION_AREA_ABSOLUTE = 0,       # Not a window layout, Old school layout
    """
    Not a window layout, old school layout
    """
    REGION_ABSOLUTE = 100,   # a Sub region that use 0,0,100,100 of screen
    """
    A sub region that uses 0,0,100,100 of screen
    """
    REGION_RELATIVE = 200,   # TODO: Sub Region that uses pixel size of area as aspect ration
    """
    TODO: Sub region that uses pixel size of area as aspect ratio.
    """
    # CHILD_WINDOW = 2,          
    
from .clickable import Clickable
class Layout(Clickable):
    
        
    def __init__(self, tag=None,  rows = None, 
                left=0, top=0, right=100, bottom=50, region_type=RegionType.SECTION_AREA_ABSOLUTE) -> None:
        self.rows = rows if rows else []
        self.set_bounds(Bounds(left,top,right,bottom))
        # self.restore_bounds = self.bounds
        self.default_height = None
        self.default_width = None
        self.default_color = None
        self.default_justify = None
        self.default_font = None
        # Paint order -- None keeps the historic backdrop layer. See measure.py.
        self.default_layer = None

        self.square = False
        # Layout duck-types Column (a sub-section IS a column), so it has to
        # carry the content-sizing fields too -- a content-sized sub-section
        # otherwise crashes when calc tries to record its measurement.
        self.content_sized = False
        self._measure_ctx = None
        self._measured_size = None

        self.padding = None
        self.border = None
        self.margin = None

        self.padding_style = None
        self.border_style = None
        self.margin_style = None
        self.bounds_style = None


        self.background_color = None
        self.background_image = "smallWhite"
        self.border_image = "smallWhite"
        self.border_color = None

        self.tag = tag
        # The author's `tag:` style name (LM #349). Held BESIDE the engine tag, not
        # in place of it: the page registers it as an extra tag_map key so
        # gui_update() can find this widget by name, while the engine keeps the
        # library-managed tag it needs for region and slot identity.
        self.alias = None
        self.parent_region_tag = ""
        
        self.click_text  = None
        self._click_tag  = None
        self.click_font  = None
        self.click_color  = None
        self.click_background = None
        self.client_id = None

        self.region = None
        self.region_type = region_type
        self.representing = False
        self._show = True
        """
        `_show` represents the user's desire for a gui element to be displayed. This should only be set using `Layout.show()`.
        """
        self._is_shown = True
        """
        `_is_shown` is used internally to ensure that only gui elements that are within the bounds of their parent are displayed.
        If a gui element is outside the bounds of its parent, it will be hidden using `_is_shown = False`. This is handled by the parent.
        Don't change this manually. `Layout.show()` uses `_show` instead.
        """
        self.is_presenting = False
        """
        Used to determine if true bounds should be used, or if hidden bounds should be used instead. Primary purpose of this is for presenting. When NOT presenting, the true bounds should be used for calculations. If presenting, we hide a gui element (if applicable) using `Bounds.hidden`.
        """
        self.orientation = 0 # 0 = Top to bottom, 1 = bottom to top

        self.runtime_node = None
        self.on_message_cb = None
        self._parent = None


    @property
    def parent(self):
        if self._parent is None:
            return None
        return self._parent()
        
    @parent.setter
    def parent(self, v):
        self._parent = weakref.ref(v)

    def mark_layout_dirty(self):
        Dirty.mark_dirty(self.parent)

    def mark_visual_dirty(self):
        Dirty.mark_dirty(self)


    @property
    def drawing_region_tag(self):
        if self.region_type != RegionType.SECTION_AREA_ABSOLUTE:
            return self.tag + "$$"
        return self.region_tag

    @property
    def bounds(self):
        if not self._show:
            # Hidden by the SCRIPT: off screen at all times, layout included.
            # A region's own rect is always sent full-screen (region_begin), so
            # laying the CONTENT out off screen is the only thing that takes a
            # hidden panel off the display.
            # A COPY, never the shared sentinel -- callers assign this and then
            # mutate it, and writing through it un-hides every hidden element.
            return Bounds(Bounds.hidden)
        if self.is_presenting and not self._is_shown:
            # Clipped by the PARENT: recomputed every present pass, so it must
            # not reach the layout pass or geometry goes stale by a frame.
            return Bounds(Bounds.hidden)
        return self._bounds

    @bounds.setter
    def bounds(self, v):
        self._bounds = v


    def set_bounds(self, bounds):
        self._bounds = bounds
    
    
    def get_content_bounds(self, merge_self):
        b = Bounds()
        if merge_self:
            b = Bounds(self.bounds)

        for row in self.rows:
            b.merge(row.bounds)
        return b
        
    def resize_to_content(self):
        self.bounds = self.get_content_bounds(True)


    @property
    def is_hidden(self):
        """
        Use `is_hidden` only to check if the layout item is currently visible to the user.
        It checks both `_show` and `_is_shown`.
        If either of these are False, will return True.
        """
        return not self._show or not self._is_shown

    @property
    def is_hidden_by_script(self):
        """Hidden because the SCRIPT asked -- show() / gui_hide().

        This is the question the LAYOUT pass must ask; see
        `Column.is_hidden_by_script`.
        """
        return not self._show
    
    @property
    def color(self):
        return self.default_color

    @color.setter
    def color(self, v):
        self.default_color = v

    @property
    def justify(self):
        return self.default_justify

    @justify.setter
    def justify(self, v):
        self.default_justify = v

    @property
    def font(self):
        return self.default_font

    @font.setter
    def font(self, v):
        self.default_font = v

    @property
    def layer(self):
        return self.default_layer

    @layer.setter
    def layer(self, v):
        self.default_layer = v

    def get_layer(self):
        return self.default_layer

    def set_orientation(self, s):
        """
        Set the orientation of the layout element.
        Valid values:
            "TB" - Top to Bottom
            "BT" - Bottom to Top
        """
        s = s.strip().upper()
        if s == "TB":
            self.orientation = 0
        elif s == "BT":
            self.orientation = 1
    
    def set_padding(self, padding):
        self.padding = padding

    def set_border(self, border):
        self.border = border

    def set_margin(self, margin):
        self.margin = margin

    def set_row_height(self, height):
        self.default_height = height

    def set_col_width(self, width):
        # A SECTION can be square too (Layout carries `square`), so it goes
        # through the same mutually-exclusive rule as a plain column.
        apply_col_width(self, width)

    def add(self, row:Row):
        self.rows.append(row)

    def rebuild(self):
        self.rows = [Row()]

    def clear_content(self, client_id=None):
        """Empty this layout AND take what it drew off the screen.

        `rebuild()` only drops the rows from the model. The widgets it dropped are
        still on the CLIENT: every widget carries a tag, the engine keeps drawing a
        tag until something tells it otherwise, and a refill allocates NEW tags - so
        each refill left the previous fill painted underneath. Reported from a real
        bridge as the ePADD inbox "creating numerous text areas instead of updating
        the one that is there": three messages' worth of title, sender and body
        superimposed, unreadable.

        A REGION has an answer already: `region_begin` sends `send_gui_clear` for its
        own drawing region before it redraws, so its old children genuinely go. A
        plain sub-section has no region of its own to clear, and the engine offers no
        "delete this widget" - so this uses the visibility model instead: hiding a row
        lays its content out at `Bounds.hidden`, and presenting it there re-sends each
        widget, by its own tag, at -1011,-1011. The tag is then off screen and nothing
        draws it again.

        Those tags stay parked on the client until the next FULL page repaint (whose
        root clear takes everything), which is the cost of doing it this way. It is
        bounded by one visit to a screen, and it is what a leaking ghost cost anyway -
        the widgets were already there, just on top of the new ones.

        Args:
            client_id (int, optional): who to send the retirement to. Defaults to the
                client this layout last presented for; nothing is sent if it has never
                presented, because then nothing was drawn.

        Returns:
            bool: True if anything was retired.
        """
        from ...helpers import FakeEvent
        retired = False
        cid = client_id if client_id is not None else self.client_id
        # A region clears itself on its next present, and a layout that never
        # presented has nothing on any client to take back.
        if (cid is not None and self.rows
                and self.region_type == RegionType.SECTION_AREA_ABSOLUTE):
            for row in self.rows:
                row.show(False)
            self.invalidate_all()
            self.present(FakeEvent(cid))
            retired = True
        self.rebuild()
        return retired

    def show(self, _show):
        """
        Use to force the gui element to be hidden, or to allow it to be seen.
        If False - the gui element will always be hidden.
        If True - will be visible assuming that it is within the bounds of its parent.

        Args:
            _show (bool): Should the element be visible.
        """
        if _show == self._show:
            return
        self._show = _show

        # Instead of all this, we just need to use `self.bounds`
        # if not _show:
        #     self.set_bounds(Bounds(-1000,-1000, -999,-999))
        # else:
        #     self.set_bounds(self.restore_bounds)
        self.mark_visual_dirty()

    # Called when the content is clear and not presented
    # Meaning all the children no longer exist
    # So THEY need to recreate any regions they have
    # If the are shown again
    def invalidate_children(self):
        for r in self.rows:
            r.invalidate_regions()
    
    def invalidate_regions(self):
        self.region = None

    def invalidate_all(self):
        self.invalidate_regions()
        self.invalidate_children()

    def represent(self, event):
        if self.client_id is None:
            return
        #self.representing = True
        # if self.region_type == RegionType.SECTION_AREA_ABSOLUTE:
        #     self.calc(event.client_id)
        #     self.present(event)
        #     #self.representing = False
        #     return
        # el
        # print(f"Recalculating Layout")
        # self.calc(event.client_id)
        # self.present(event)
        if not self._show:
            # self.calc(event.client_id)
            self.present(event)
            #self.representing = False
            return
        else:  # is_hidden 
            
            self.present(event)
            # #self.calc(event.client_id)
            # self.region_begin(event.client_id)
            # self.invalidate_children()
            # self.region_end(event.client_id)
        #self.representing = False

        

    def note_measured(self, mode, avail_px, font, ar, size):
        """Same contract as Column.note_measured -- see the duck-typing note in
        __init__."""
        self._measure_ctx = (mode, avail_px, font, ar)
        self._measured_size = size

    def measured_size_changed(self):
        ctx = self._measure_ctx
        if ctx is None or self._measured_size is None:
            return True
        mode, avail_px, font, ar = ctx
        current = self.measure(self.client_id, mode, avail_px, font, ar)
        if current is None:
            return True
        return (abs(current[0] - self._measured_size[0]) > 1e-6
                or abs(current[1] - self._measured_size[1]) > 1e-6)

    def measure(self, client_id, mode, avail_px, font, ar):
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
        sub-section falls back to flex like any other unmeasurable column.
        """
        if avail_px is not None and avail_px > 0:
            area = Bounds(0.0, 0.0, px_to_pct_x(avail_px, ar), 0.0)
            total_height = 0.0
            measured_any = False
            rows = list(filter(lambda r: r._show, self.rows))
            for row in rows:
                row_font = row.default_font
                if row_font is None:
                    row_font = self.default_font
                h = self._measure_row_height(row, area, ar, row_font,
                                             mode, client_id)
                if h is not None:
                    total_height += h
                    measured_any = True
            if measured_any:
                return (area.width, total_height)
            return None

        width = 0.0
        height = 0.0
        measured_any = False
        rows = list(filter(lambda r: r._show, self.rows))
        for row in rows:
            row_font = row.default_font
            if row_font is None:
                row_font = self.default_font
            row_width = 0.0
            row_height = 0.0
            for col in row.columns:
                if col.is_hidden_by_script:
                    continue
                natural = col.measure(client_id, mode, None,
                                      effective_font(col, row_font), ar)
                if natural is None:
                    continue
                measured_any = True
                row_width += natural[0]
                if natural[1] > row_height:
                    row_height = natural[1]
            if row_width > width:
                width = row_width
            height += row_height
        return (width, height) if measured_any else None

    def _resolve_col_widths(self, row, row_bounds_area, aspect_ratio, row_font,
                            client_id=None):
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
        content row containing squares has to be resolved in two steps.
        """
        actual_cols = []
        fixed_widths = []
        squares = 0
        assigned_space = 0
        assigned_cols = 0
        # Allocated only if a content column is actually seen. calc runs on
        # every repaint, so a layout using no content keywords should not pay
        # two list allocations per row for the privilege of the feature
        # existing.
        content_idx = None    # indices into actual_cols that sized to content
        content_floor = None  # their min-content width, parallel to content_idx
        auto_floor = None     # {index: min-content width} for `auto` columns

        col: Column
        columns = filter(lambda c: c._show, row.columns)
        for col in columns:
            if col.is_hidden_by_script:
                continue
            squares += 1 if col.square else 0
            col_font = effective_font(col, row_font)
            col_font_size = get_font_size(col_font)
            # NOT `self`. A Layout's own `default_width` is how wide IT is in its
            # parent row - a sub-section is both a column and a section, so
            # `gui_sub_section("col-width:25;")` means "I take 25", never "every column
            # inside me takes 25". Cascading it to children gave each of them 25 and
            # spilled the last one straight out of the sub-section, over whatever came
            # next. A top-level section never set default_width (it is placed by
            # `area:`), which is why this only ever bit nested ones.
            raw_width = calc_float_attribute(
                "default_width", col, row, None, aspect_ratio.x, col_font_size)
            if raw_width is None and AUTO_DEFAULT:
                raw_width = AUTO
            default_width = resolved_size(raw_width)

            if (default_width is None and raw_width.__class__ is ContentSize
                    and raw_width.is_auto):
                #
                # `auto` stays FLEX -- it is not given a width of its own here.
                # It only records a FLOOR, so the even split below can be
                # pushed up for a column whose content genuinely needs more.
                # This is the LM issue 672 case: a long string next to short
                # ones should grow while its roomier neighbours give way.
                #
                if not col.square:
                    floor = col.measure(client_id, MIN_CONTENT, None,
                                        col_font, aspect_ratio)
                    if floor is not None:
                        if auto_floor is None:
                            auto_floor = {}
                        auto_floor[len(actual_cols)] = floor[0] + col_box_width(
                            col, aspect_ratio, col_font_size)
                        col.content_sized = True
                        col.note_measured(MIN_CONTENT, None, col_font,
                                          aspect_ratio, floor)

            elif default_width is None and raw_width.__class__ is ContentSize:
                #
                # A content-sized column: ask the widget how wide it wants to
                # be. A square ignores it (its size comes from the row height),
                # and an unmeasurable widget returns None and simply stays
                # flex -- never 0, since one `col-width: content` on a SECTION
                # cascades to every column in it.
                #
                if not col.square:
                    natural = col.measure(client_id, raw_width, None,
                                          col_font, aspect_ratio)
                    if natural is not None:
                        box = col_box_width(col, aspect_ratio, col_font_size)
                        # A hair of slack, so rounding at the engine boundary
                        # cannot turn an exact fit into a wrapped line drawn
                        # over the next row -- see CONTENT_WIDTH_SLACK_PX.
                        #
                        # Only when there IS content: a column measuring zero
                        # (empty text, a Blank) must collapse to nothing rather
                        # than reserve two pixels of nothing.
                        default_width = natural[0] + box
                        if natural[0] > 0:
                            default_width += px_to_pct_x(CONTENT_WIDTH_SLACK_PX,
                                                         aspect_ratio)
                        col.content_sized = True
                        col.note_measured(raw_width, None, col_font,
                                          aspect_ratio, natural)
                        # Remember how far it may be squeezed. min-content is
                        # the widest unbreakable word: below that the engine
                        # breaks mid-word, and since it does not clip, glyphs
                        # spill over the neighbouring column.
                        floor = col.measure(client_id, MIN_CONTENT, None,
                                            col_font, aspect_ratio)
                        if content_idx is None:
                            content_idx = []
                            content_floor = []
                        content_idx.append(len(actual_cols))
                        content_floor.append(
                            floor[0] + box if floor else default_width)

            if default_width is not None:
                assigned_space += default_width
                assigned_cols += 1
            actual_cols.append(col)
            fixed_widths.append(default_width)

        if len(actual_cols) == 0:
            return None

        #
        # Content columns are satisfied before flex (like CSS grid `auto` vs
        # `1fr`), but they are REQUESTS, not reservations. When the row cannot
        # hold everything, give way in a strict order:
        #
        #   1. flex columns shrink to 0   -- they draw nothing, so this is free
        #   2. content columns shrink proportionally, down to min-content
        #   3. below that, clamp and accept the overflow
        #
        # The order matters because the engine does not clip: a flex column at
        # zero width is invisible, whereas a content column squeezed past
        # min-content spills its glyphs across whatever is beside it.
        #
        if content_idx:
            overflow = assigned_space - row_bounds_area.width
            if overflow > 0:
                shrinkable = sum(fixed_widths[i] - content_floor[k]
                                 for k, i in enumerate(content_idx))
                if shrinkable > 0:
                    take = min(overflow, shrinkable)
                    for k, i in enumerate(content_idx):
                        room = fixed_widths[i] - content_floor[k]
                        if room > 0:
                            fixed_widths[i] -= take * (room / shrinkable)
                    assigned_space = sum(w for w in fixed_widths if w is not None)

        # get the width and the height of a cell in pixels
        actual_width = row_bounds_area.width/len(actual_cols) * aspect_ratio.x / 100
        actual_height =  row_bounds_area.height * aspect_ratio.y /100

        # get the low of these two as a percentage of the window width
        if actual_height < actual_width:
            square_width = (actual_height/aspect_ratio.x) * 100
            square_height = (actual_height/aspect_ratio.y) * 100
        else:
            square_width = (actual_width/aspect_ratio.x) *100
            square_height = (actual_width/aspect_ratio.y) * 100

        if len(actual_cols) != squares:
            need_assigned = max(len(actual_cols)-squares-assigned_cols,1)
            rect_col_width = (row_bounds_area.width-assigned_space-(squares*square_width))/need_assigned
            if square_width> rect_col_width:
                # Squares would be wider than a flex column, so shrink them to
                # it and re-divide what is left.
                #
                # This recompute used to omit `assigned_space`, so columns with
                # an explicit col-width stopped being deducted and the flex
                # columns were handed width that was already spoken for. Three
                # columns with one at 60% summed to 160%; two fixed at 35% plus
                # one flex summed to 170%. The engine does not clip, so those
                # columns were drawn over their neighbours.
                #
                # It fires more often than "a square edge case" implies:
                # square_width is computed unconditionally and this branch is
                # not guarded by `squares > 0`, so a row of plain columns with
                # one fixed width hits it whenever the row is tall.
                square_width= rect_col_width
                rect_col_width = (row_bounds_area.width-assigned_space-(squares*square_width))/need_assigned
            # Fixed columns can already oversubscribe the row -- an authoring
            # error, but flex columns must then get nothing rather than a
            # negative width, which would invert the rect.
            if rect_col_width < 0:
                rect_col_width = 0
        else:
            rect_col_width = square_width

        # Fill the flex slots in place rather than building a second list.
        for i, w in enumerate(fixed_widths):
            if w is None:
                fixed_widths[i] = rect_col_width

        if auto_floor:
            self._raise_flex_to_floors(actual_cols, fixed_widths, auto_floor,
                                       rect_col_width)

        return actual_cols, fixed_widths, square_width, square_height

    @staticmethod
    def _raise_flex_to_floors(actual_cols, widths, auto_floor, flex_width):
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
        point there just isn't enough room" case.
        """
        need = 0.0
        for i, floor in auto_floor.items():
            if floor > widths[i]:
                need += floor - widths[i]
        if need <= 0:
            return

        # Slack is what the OTHER flex columns can surrender. A plain flex
        # column can go to 0 (it draws nothing); an auto column stops at its
        # own floor.
        donors = []
        slack = 0.0
        for i, w in enumerate(widths):
            if i in auto_floor and auto_floor[i] >= w:
                continue                      # already at or below its floor
            if abs(w - flex_width) > 1e-9:
                continue                      # not a flex column (fixed width)
            floor = auto_floor.get(i, 0.0)
            room = w - floor
            if room > 1e-9:
                donors.append((i, room))
                slack += room
        if slack <= 0:
            return

        take = min(need, slack)
        for i, room in donors:
            widths[i] -= take * (room / slack)

        # Hand the reclaimed space out, proportionally if it was not enough.
        share = take / need if need > take else 1.0
        for i, floor in auto_floor.items():
            if floor > widths[i]:
                widths[i] += (floor - widths[i]) * share

    def _measure_row_height(self, row, row_bounds_area, aspect_ratio, row_font,
                            mode, client_id):
        """Natural height of `row` in percent, or None if nothing measurable.

        Height depends on WIDTH -- text wraps to the width it is given -- so the
        columns are resolved first and each is measured at the width it will
        actually get.

        Squares are excluded from the maximum on purpose. A square's height
        comes FROM the row height, so letting it contribute would be circular.
        A row of nothing but squares (or unmeasurable widgets) therefore has no
        natural height at all and returns None, falling back to flex.
        """
        resolved = self._resolve_col_widths(row, row_bounds_area, aspect_ratio,
                                            row_font, client_id)
        if resolved is None:
            return None
        actual_cols, col_widths, _sw, _sh = resolved

        tallest = None
        for i, col in enumerate(actual_cols):
            if col.square:
                continue
            col_font = effective_font(col, row_font)
            # Measure at this column's own width, minus its box model, since
            # that is the space the text actually has to wrap inside.
            avail_pct = col_widths[i]
            col_font_size = get_font_size(col_font)
            margin = Bounds(calc_bounds(col.margin_style, aspect_ratio, col_font_size))
            border = Bounds(calc_bounds(col.border_style, aspect_ratio, col_font_size))
            padding = Bounds(calc_bounds(col.padding_style, aspect_ratio, col_font_size))
            avail_pct -= (margin.left + margin.right + border.left + border.right
                          + padding.left + padding.right)
            avail_px = pct_to_px_x(avail_pct, aspect_ratio) if avail_pct > 0 else None

            natural = col.measure(client_id, mode, avail_px, col_font, aspect_ratio)
            if natural is None:
                continue
            col.note_measured(mode, avail_px, col_font, aspect_ratio, natural)
            height = natural[1]
            # Give the height back its vertical box model, or a bordered cell
            # clips its own text.
            height += (margin.top + margin.bottom + border.top + border.bottom
                       + padding.top + padding.bottom)
            if tallest is None or height > tallest:
                tallest = height
                col.content_sized = True

        return tallest

    def _content_row_height(self, row, bounds_area, aspect_ratio, row_font,
                            mode, client_id, provisional_height):
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
            worth the measurements. Documented, not silently approximate.
        """
        area = Bounds(bounds_area)
        area.shrink(row.margin)
        area.shrink(row.padding)
        area.shrink(row.border)

        has_square = any(c.square for c in row.columns if not c.is_hidden_by_script)

        if not has_square:
            area.height = bounds_area.height     # width is height-independent
            return self._measure_row_height(row, area, aspect_ratio, row_font,
                                            mode, client_id)

        area.height = provisional_height
        first = self._measure_row_height(row, area, aspect_ratio, row_font,
                                         mode, client_id)
        if first is None:
            return None
        area.height = first
        second = self._measure_row_height(row, area, aspect_ratio, row_font,
                                          mode, client_id)
        return first if second is None else second

    def calc(self, client_id):
        aspect_ratio = get_client_aspect_ratio(client_id)
        self.client_id = client_id
        
        sec_font_size = get_font_size(self.default_font)
        if self.bounds_style is None:
            bounds_area = Bounds(self.bounds)
        elif self.bounds is not None and not self._show:
            bounds_area = Bounds(self.bounds)
        else:
            bounds_area = Bounds(calc_bounds(self.bounds_style, aspect_ratio, sec_font_size))
            self.bounds = Bounds(bounds_area)

        if self.region_type == RegionType.REGION_RELATIVE:
            w = bounds_area.width
            h = bounds_area.height
            bounds_area = Bounds(0,0,w,h)

        # rows = self.rows
        rows = list(filter(lambda r: r._show, self.rows))
        #if self.orientation == 1:
        #    rows = list(reversed(rows))
        
        # remove empty
        #self.rows = [x for x in self.rows if len(x.columns)>0]
        if len(rows):
            self.margin = Bounds(calc_bounds(self.margin_style, aspect_ratio, sec_font_size))
            self.padding =Bounds(calc_bounds(self.padding_style, aspect_ratio, sec_font_size))
            self.border =Bounds(calc_bounds(self.border_style, aspect_ratio, sec_font_size))

            bounds_area.shrink(self.margin)
            bounds_area.shrink(self.border)
            bounds_area.shrink(self.padding)
            
            section_height = resolved_size(
                calc_float_attribute("default_height", None, None, self, aspect_ratio.y, 20)
            ) if self.default_height is not None else None

            # Heights measured for content rows, keyed by row, so the main loop
            # below reuses them instead of measuring a second time.
            content_heights = {}
            auto_row_floor = {}   # id(row) -> content height, for `auto` rows

            if section_height is not None:
                layout_row_height = section_height
            else:
                layout_row_height = bounds_area.height
                flex_rows = len(rows)
                fixed_total = 0.0
                for row in rows:
                    row_font = self.default_font
                    if row.default_font is not None:
                        row_font = row.default_font

                    row_font_height  = get_font_size(row_font)
                    raw = calc_float_attribute("default_height", None, row, self, aspect_ratio.y, row_font_height) \
                        if row.default_height is not None else None
                    if raw is None and AUTO_DEFAULT:
                        raw = AUTO
                    value = resolved_size(raw) if raw is not None else None

                    if (value is None and raw is not None
                            and raw.__class__ is ContentSize and raw.is_auto):
                        #
                        # `auto` keeps the row in the FLEX pool -- it only
                        # records a floor, so a row whose content genuinely
                        # needs more than the even share can be raised below.
                        #
                        floor = self._content_row_height(
                            row, bounds_area, aspect_ratio, row_font, raw,
                            client_id, layout_row_height / max(len(rows), 1))
                        if floor is not None and floor > 0:
                            auto_row_floor[id(row)] = floor
                        continue

                    if value is None and raw is not None and raw.__class__ is ContentSize:
                        value = self._content_row_height(
                            row, bounds_area, aspect_ratio, row_font, raw,
                            client_id, layout_row_height / max(len(rows), 1))
                        if value is not None:
                            content_heights[id(row)] = value

                    if value is not None:
                        layout_row_height -= value
                        fixed_total += value
                        flex_rows -= 1

                #
                # Content rows are requests, not reservations. If they and the
                # fixed rows have oversubscribed the section, scale the CONTENT
                # rows down proportionally so the flex rows are not left with a
                # negative share. Fixed rows are never scaled -- an over-large
                # fixed row already drove the remainder negative before content
                # sizing existed, and that behaviour must not change.
                #
                if layout_row_height < 0 and content_heights:
                    content_total = sum(content_heights.values())
                    keep = max(0.0, content_total + layout_row_height)
                    scale = (keep / content_total) if content_total > 0 else 0.0
                    for key in content_heights:
                        content_heights[key] *= scale
                    layout_row_height = bounds_area.height - (fixed_total - content_total) - keep

                if flex_rows>0:
                    layout_row_height /= flex_rows

                #
                # Raise `auto` rows to their content height, paid for by the
                # flex rows that have slack. Same shape as the column side, but
                # rows all share ONE flex height, so a raised row is moved into
                # content_heights (a per-row override) and the remaining flex
                # rows re-divide what is left.
                #
                if auto_row_floor:
                    #
                    # Share the flex height so that NO ROW ENDS UP BELOW ITS
                    # OWN FLOOR, and rows without a floor are unaffected.
                    #
                    # The old code raised the tall rows and gave the rest
                    # whatever was left -- possibly nothing. Its comment claimed
                    # "a row at zero draws nothing"; that is false, and it is
                    # what made this a bug. A zero-height row still draws its
                    # text, because the engine does not clip, so the content
                    # lands on the row above (LM issue672's "New Row2" and
                    # "New Row3" on top of a wrapped "New Row1").
                    #
                    # This is min-constrained water-filling, the same shape CSS
                    # uses for flex items with a minimum size: share evenly,
                    # freeze whatever cannot fit in its share at its floor, then
                    # re-share what is left among the rest. It settles in at
                    # most one pass per row, and a row whose floor is under the
                    # even share is left exactly where it always was.
                    #
                    avail = bounds_area.height - fixed_total
                    # A row is in the flex pool when it has no RESOLVED fixed
                    # height. `row-height: auto` stores the AUTO sentinel rather
                    # than None, so testing for None alone silently excluded
                    # every explicitly-auto row -- and an empty pool gave every
                    # row a share of zero.
                    flex_ids = [id(r) for r in rows
                                if id(r) not in content_heights
                                and (r.default_height is None
                                     or r.default_height.__class__ is ContentSize)]
                    floors = {k: auto_row_floor.get(k, 0.0) for k in flex_ids}
                    total_floor = sum(floors.values())

                    if total_floor > avail and total_floor > 0:
                        #
                        # The floors do not fit at all. They are requests, so
                        # scale them TOGETHER: every row keeps its share of what
                        # there is and none is starved to pay for another. Text
                        # still overdraws here -- the section is genuinely too
                        # small for its content, which is the author's to fix
                        # and what the layout audit reports.
                        #
                        scale = max(0.0, avail) / total_floor
                        for k in flex_ids:
                            content_heights[k] = floors[k] * scale
                        layout_row_height = 0.0
                    else:
                        frozen = {}
                        pool = list(flex_ids)
                        space = avail
                        while pool:
                            share = space / len(pool)
                            over = [k for k in pool if floors[k] > share]
                            if not over:
                                break
                            for k in over:
                                frozen[k] = floors[k]
                                space -= floors[k]
                                pool.remove(k)
                        share = (space / len(pool)) if pool else 0.0
                        for k in frozen:
                            content_heights[k] = frozen[k]
                        layout_row_height = share
            
            row : Row
            row_top = bounds_area.top
            row_bottom = bounds_area.bottom
            
            for row in rows:
                #
                # REGION STUFF
                #
                row.region_tag = self.drawing_region_tag
                # Cascading padding
                row_font = row.default_font
                if row_font is None:
                    row_font = self.default_font

                row_font_height  = get_font_size(row_font)
                row.margin = Bounds(calc_bounds(row.margin_style, aspect_ratio, row_font_height))
                row.padding =Bounds(calc_bounds(row.padding_style, aspect_ratio, row_font_height))
                row.border =Bounds(calc_bounds(row.border_style, aspect_ratio, row_font_height))

                # This is for drawing background and border?
                row_height = content_heights.get(id(row))
                if row_height is None and row.default_height is not None:
                    row_height = resolved_size(calc_float_attribute("default_height", None, row, None,  aspect_ratio.y, row_font_height))
                if row_height is None:
                    row_height = layout_row_height

                row_bounds_area = Bounds(bounds_area)
                # row_bounds_area.height = row_height
                #row.left = bounds_area.left
                #row.width = bounds_area.width
                if self.orientation==0:
                    row_bounds_area.top = row_top
                    row_top += row_height
                    row_bounds_area.bottom = row_top # + row_bounds_area.height
                else:
                    row_bounds_area.bottom=row_bottom
                    row_bottom -= row_height
                    row_bounds_area.top = row_bottom

                row.left = row_bounds_area.left
                row.top = row_bounds_area.top
                row.right = row_bounds_area.right
                row.bottom = row_bounds_area.bottom
                row.width = row.right - row.left
                row.height = row.bottom - row.top
                # SET Parent
                row.parent = self
                
                row.bounds = Bounds(row_bounds_area)
                row_bounds_area.shrink(row.margin)
                row_bounds_area.shrink(row.padding)
                row_bounds_area.shrink(row.border)

                if len(row.columns)==0:
                    continue

                resolved = self._resolve_col_widths(row, row_bounds_area,
                                                    aspect_ratio, row_font,
                                                    client_id)
                if resolved is None:
                    continue
                actual_cols, col_widths, square_width, square_height = resolved

                # bit of a hack to make sure face aren't the biggest things
                col: Column
                col_left = row_bounds_area.left
                hole_size = 0
                for col_index, col in enumerate(actual_cols):
                    col_font = effective_font(col, row_font)
                    col.font = col_font
                    col_font_size  = get_font_size(col_font)

                    col.margin = Bounds(calc_bounds(col.margin_style, aspect_ratio, col_font_size))
                    col.padding =Bounds(calc_bounds(col.padding_style, aspect_ratio, col_font_size))
                    col.border =Bounds(calc_bounds(col.border_style, aspect_ratio, col_font_size))

                    col_bounds_area = Bounds(row_bounds_area)
                    col_bounds_area.left = col_left

                    # Width already resolved by _resolve_col_widths. It used to
                    # be recomputed here, duplicating a calc_float_attribute per
                    # column on every calc for an identical result.
                    assigned_space = col_widths[col_index]


                    if col.square:
                        col_bounds_area.width = square_width
                        col_bounds_area.height = square_height
                        # Square ignores holes?
                        hole_size = 0
                    elif col.__class__ == Hole:
                        hole_size += assigned_space
                        continue
                    
                    else:
                        col_bounds_area.width =  assigned_space + hole_size
                        hole_size = 0

                    col_left = col_bounds_area.right

                    #
                    # A sub section is a Layout stored as a column, so it appears
                    # in BOTH passes. It applies its own margin/border/padding in
                    # its calc() below, so applying them here too insets its
                    # content twice. Leaf columns have no pass of their own, so
                    # the parent still applies the box model for them.
                    #
                    if not isinstance(col, Layout):
                        col_bounds_area.shrink(col.margin)
                        col_bounds_area.shrink(col.border)
                        col_bounds_area.shrink(col.padding)

                    

                    ##############
                    ### Cascade other attributes
                    if col.color is None:
                        if col.default_color is not None:
                            col.color = col.default_color
                        elif row.default_color is not None:
                            col.color = row.default_color
                        elif self.default_color is not None:
                            col.color = self.default_color

                    if col.justify is None:
                        if col.default_justify is not None:
                            col.justify = col.default_justify
                        elif row.default_justify is not None:
                            col.justify = row.default_justify
                        elif self.default_justify is not None:
                            col.justify = self.default_justify

                    # Paint order cascades the same way, so `layer:` on a
                    # section reaches every widget in it -- which is what makes
                    # a whole panel occludable in one declaration.
                    if col.layer is None:
                        if col.default_layer is not None:
                            col.layer = col.default_layer
                        elif row.default_layer is not None:
                            col.layer = row.default_layer
                        elif self.default_layer is not None:
                            col.layer = self.default_layer


                    ##################
                    col.set_bounds(col_bounds_area)
                    #
                    # REGION STUFF
                    #
                    col.region_tag = self.drawing_region_tag
                    # SET Parent
                    col.parent = self

                    col.calc(client_id)

    @property
    def click_tag(self):
        if self._click_tag is not None:
            return self._click_tag
        if self.click_text is not None:
            return f"__click:{self.tag}"
        
    @click_tag.setter
    def click_tag(self, v):
        self._click_tag = v

    @property
    def region_tag(self):
        # if self.region_type != RegionType.SECTION_AREA_ABSOLUTE:
        #     return self.local_region_tag
        return self.parent_region_tag

    @region_tag.setter
    def region_tag(self, t):
        # Setting the region tag of a layout is really 
        # setting the parent region tag
        self.parent_region_tag = t
    
    def _apply_clipping(self):
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
        their own stale bounds inside a row that is not there.
        """
        for row in self.rows:
            row._is_shown = not is_out_of_bounds(row, self) and not self.is_hidden
            row._apply_clipping()

    def present(self, event):
        self.calc(event.client_id)
        # Geometry is settled; decide visibility from it before anything draws.
        self._apply_clipping()
        self.is_presenting = True
        try:
            self.region_begin(event.client_id)
            self._pre_present(event)
            self._present(event)
            self._post_present(event)
            self.region_end(event.client_id)
        finally:
            # A raise here must not leave the flag set: `bounds` would then
            # keep reporting Bounds.hidden outside of a present pass and
            # poison every later layout calculation.
            self.is_presenting = False

    def _pre_present(self, event):
        pass

    def _present(self, event):
        # Sections are different their bounds are the whole container

        bounds = Bounds(self.bounds)
        
        ctx = FrameContext.context
        border = Bounds(bounds)
        border.shrink(self.margin)
        padding= Bounds(border)
        padding.shrink(self.border)
   
        if self.border is not None and self.border_color is not None:
            bb_props = backdrop_props(self.border_image, self.border_color, self.get_layer())
            ctx.sbs.send_gui_image(event.client_id, self.region_tag,
                "__bb:"+backdrop_tag(self), bb_props,
                border.left,
                border.top,
                border.right,
                border.bottom)

        if self.background_color is not None:
            props = backdrop_props(self.background_image, self.background_color, self.get_layer())
            ctx.sbs.send_gui_image(event.client_id, self.region_tag,
                "__bg:"+backdrop_tag(self), props,
                padding.left, 
                padding.top, 
                padding.right, 
                padding.bottom)

            
        row:Row
        for row in self.rows:
            # Visibility was decided in _apply_clipping, before drawing began.
            # We still want to present all children, because if we don't, then we get ghost gui elements
            row.present(event)


    def region_begin(self, client_id):
        #if self.representing and self.region:
        # if self.region:
        #     if self.region_type != RegionType.SECTION_AREA_ABSOLUTE:
        #         print(f"clear {self.region_tag}")
        #         sbs.send_gui_clear(client_id, self.drawing_region_tag)
        # elif not self.region:
        SBS = FrameContext.context.sbs
        if self.region_type == RegionType.REGION_ABSOLUTE:
            self.region = True
            SBS.send_gui_sub_region(client_id, self.region_tag, self.drawing_region_tag, "draggable:True;", 0.0,0.0,100.0,100.0)
            SBS.send_gui_clear(client_id, self.drawing_region_tag)
        elif self.region_type == RegionType.REGION_RELATIVE:
            #
            # TODO: This should be bounds
            #
            self.region = True
            SBS.send_gui_sub_region(client_id, self.region_tag, self.drawing_region_tag, "draggable:True;", 0,0,50,50)
            SBS.send_gui_clear(client_id, self.drawing_region_tag)
    
        
    def region_end(self, client_id):
        # There should always be the root

        #if self.representing:
        #    self.representing = False
        SBS = FrameContext.context.sbs
        if self.region_type != RegionType.SECTION_AREA_ABSOLUTE:
            SBS.send_gui_complete(client_id, self.drawing_region_tag)

        

    def _post_present(self, event):
        # A TAG IS ENOUGH. `Column._post_present` has always emitted on either, and this
        # matching the Column is what lets a caller ask for a hit target WITHOUT asking
        # for the engine to paint a word over it on press. The gate used to be click_text
        # alone, so wanting a silent region meant setting click_text to "" - which is a
        # value, so the engine drew it, and a name set later drew that.
        if self.click_text is not None or self.click_tag is not None:
            click_props = ""
            if self.click_text is not None:
                click_props = f"$text:{self.click_text};"
            if self.click_color is not None:
                click_props += f"color: {self.click_color};"
            if self.click_font is not None:
                click_props += f"font: {self.click_font};"
            if self.click_tag is None:
                self.click_tag = f"__click:{self.tag}"
            if self.click_background is not None:
                click_props += f"background_color:{self.click_background};"
            else:
                click_props += f"background_color: white;"

            bounds = Bounds(self.bounds)
            bounds.shrink(self.margin)
            bounds.shrink(self.border)

            ctx = FrameContext.context
            ctx.sbs.send_gui_clickregion(event.client_id, self.drawing_region_tag,
                self.click_tag, click_props,
                bounds.left, bounds.top, bounds.right, bounds.bottom)

    def is_message_for(self, event):
        """Used by MessageTrigger i.e. gui_message to know if message is for this object

        Args:
            event (EVENT): the engine event

        Returns:
            bool: if the gui_message MessageTrigger should be True
        """
        return event.sub_tag == self.tag or event.sub_tag == self.click_tag
  

    def on_message(self, event):
        # A GUI transcript, when one is being recorded, wants the WIDGET and not just the
        # tag: a tag is an ordinal assigned in page-build order, so it stops meaning
        # anything the moment a row is added above it. Only the widget the event is
        # actually for gets noted. See procedural/gui_record.py.
        from ...procedural import gui_record
        if gui_record._enabled and (event.sub_tag == self.tag
                                    or event.sub_tag == self.click_tag):
            gui_record.gui_record_note(event, self)

        # If this is clickable handle it
        if event.sub_tag == self.click_tag:
            Layout.clicked[event.client_id] = self

        if self.runtime_node is not None:
            self.runtime_node.on_message(event)
        if self.on_message_cb is not None:
            # Was `.on_message(event, self)`, which raised AttributeError for the
            # plain function gui_message_callback assigns. (LM #614)
            invoke_message_cb(self.on_message_cb, event, self)
        # Else propagate messages
        row:Row
        for row in self.rows:
            row.on_message(event)

    def on_end_presenting(self, client_id):
        # Else propagate messages
        row:Row
        for row in self.rows:
            row.on_end_presenting(client_id)

    def on_begin_presenting(self, client_id):
        # Else propagate messages
        row:Row
        for row in self.rows:
            row.on_begin_presenting(client_id)


    def print_bounds(self, bounds=None):
        if not bounds:
            bounds = self.bounds
        print(f"Left: {bounds.left}    Top: {bounds.top};   ")
        print(f"Rigth: {bounds.right}    Bottom: {bounds.bottom}")




        



