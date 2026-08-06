from sbs_utils.pages.layout.bounds import Bounds
from sbs_utils.pages.layout.column import Column
from sbs_utils.pages.widgets.control import Control
from sbs_utils.helpers import FrameContext
from textwrap import TextWrapper
def get_client_aspect_ratio (cid):
    """Get the aspect ratio of the specified client's screen.
    Args:
        cid (int): The client ID.
    Returns:
        Vec3: The aspect ratio. If Vec3.z is 99, then the client hasn't set the aspect ratio."""
def get_font_size (font):
    ...
def measure_block_height (font, text, px_width):
    """Height in PIXELS of `text` wrapped to `px_width`, or None.
    
    Wrapping is the ENGINE's, not ours. We ask rather than compute a line count
    -- computing it is exactly how the mock's wrap and the mock's measure became
    the same code, which is why the mock cannot detect its own wrap error."""
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
def measure_props (props, mode, avail_px, font, ar):
    """Cached front end for the per-widget natural size. See
    _measure_props_uncached for the real work and the reasoning."""
def merge_props (d):
    ...
def parse_url (text):
    ...
def split_props (s, def_key):
    ...
def to_float (text, defa):
    ...
def wrap_to_width (font, text, px_width):
    """Break `text` into lines that each MEASURE within `px_width`.
    
    Two invariants, both learned the hard way:
    
    1. EVERY RETURNED LINE FITS. A line that comes back wider than px_width gets
       wrapped AGAIN by the engine, into a box sized for the line count we
       returned -- and since the engine does not clip, the extra line is drawn on
       top of its neighbour. This is the whole reason the function exists.
    2. NO WORD IS LOST. Obvious, but a greedy version of this that "gave back"
       an over-long word by popping it silently deleted it from the document.
       Hence the index walk below: a word is only consumed by being placed.
    
    On the "ask, never model" rule: measurement still asks the engine. But a
    TextArea has to know where the breaks fall, because it keeps a record per
    display line (styles, links, line-indexed scrolling). It used to guess from
    an AVERAGE glyph width and a character count -- wrong in both directions,
    early on narrow glyphs and late on wide ones. Summed word widths are not
    enough either: a joined string does not measure as the sum of its parts, so
    the candidate itself has to be measured.
    
    Fidelity, from the engine capture (missions/font_measure): line counts agree
    with the engine at >=600px, drift ~6% at 300px, and badly below that -- so a
    very narrow column is still worth confirming in a real session.
    
    Words wider than a whole line are broken MID-WORD, as the engine does."""
class FaceLine(object):
    """class FaceLine"""
    def __init__ (self, text, ar) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def send_gui (self, SBS, client_id, region_tag, tag, left, top, right, bottom):
        ...
class HrLine(object):
    """Horizontal rule (`<hr>` / `<hr/>`) — a thin full-width divider. Uses `<hr>`
    rather than `---` so it never clashes with the table separator row."""
    def __init__ (self, ar) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def send_gui (self, SBS, client_id, region_tag, tag, left, top, right, bottom):
        ...
class ImageLine(object):
    """class ImageLine"""
    def __init__ (self, text, ar) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def send_gui (self, SBS, client_id, region_tag, tag, left, top, right, bottom):
        ...
class LinkLine(object):
    """A whole-line hyperlink `[Display](ref://key)`. Renders as styled clickable
    text plus a transparent clickregion on top whose click_tag routes back to the
    owning TextArea's on_message, which resolves the key (intra-document nav)."""
    def __init__ (self, display, click_tag, ar, sbs, font='gui-2') -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def send_gui (self, SBS, client_id, region_tag, tag, left, top, right, bottom):
        ...
class ShipLine(object):
    """class ShipLine"""
    def __init__ (self, text, ar) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def send_gui (self, SBS, client_id, region_tag, tag, left, top, right, bottom):
        ...
class TableLine(object):
    """A GFM pipe-table rendered as a grid of text cells — a block-line like
    ImageLine/FaceLine (owns its rect via send_gui). Columns are sized to their
    measured content then shrunk to fit the region width (never overflow — there's
    no horizontal scroll); row height is the tallest wrapped cell. Per-column
    alignment comes from the |:--|--:| separator row. Keep tables SMALL/static:
    scrolling is line-indexed so a tall table clips at the block boundary."""
    def __init__ (self, rows, aligns, ar, pixel_width, sbs) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def send_gui (self, SBS, client_id, region_tag, tag, left, top, right, bottom):
        ...
class TextArea(Control):
    """class TextArea"""
    def __init__ (self, tag, message, markdown=True, line_styles=None) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def _build_table (self, raw_rows, ar, pixel_width):
        """Parse GFM pipe rows into a TableLine. The |:--|--:| separator row (if
        present) supplies per-column alignment and is dropped from the data; a
        table with no separator row just renders all-left with row 0 as header."""
    def _present (self, event):
        ...
    def _present_simple (self, event):
        ...
    def _promote_if_overflowing (self, client_id):
        """A one-line message that does not FIT is not a simple label.
        
        The simple/rich choice is made in the `value` setter, before the widget
        has bounds -- so "one line" there means "contains no newline", NOT
        "draws as one line". Hand a whole paragraph to gui_text_area as
        `$text:...` and it took the fast path: a single send_gui_text across the
        widget's rect, with no wrap accounting, no line list and no scrollbar.
        The engine wraps it anyway and, since it does not clip, draws the tail
        below the widget. Reaching for gui_text_area to fix a spilling label
        therefore changed nothing -- the widget quietly declined to be a text
        area, which is what sent LM's mission picker down this path.
        
        So ask the question again HERE, where the bounds exist: measure the text
        at the width it will be drawn at, and if it is taller than the widget,
        rewrite it as rich content so calc_rich wraps it and gives it a
        scrollbar. Text that fits keeps the cheap path untouched, which is the
        overwhelmingly common case (a one-line styled label).
        
        The rewrite uses the `$$<props> <text>` line form DELIBERATELY. The
        author wrote a styled label, not markdown, so a description that happens
        to start with '-' or a digit must not silently become a bullet or a
        numbered list item. `$$` names the style outright and skips the markdown
        sniffing in get_line_style.
        
        Promotion is one-way until the value is re-set. Re-deciding every frame
        would oscillate: the rich form is exactly what makes the text fit."""
    def calc (self, client_id):
        ...
    def calc_rich (self, client_id, _retry=True):
        ...
    def get_line_style (self, some_lines, previous):
        ...
    def get_markdown_line_style (self, some_lines, previous):
        ...
    def get_style (self, key):
        ...
    def invalidate_regions (self):
        ...
    def line_style_for (self, index):
        """The caller-supplied style for content line `index`, or None.
        
        Normalised so a caller can pass just the parts it cares about --
        `{"style": "font:gui-1;color:#6a8;", "indent": 4}` is enough."""
    def measure (self, client_id, mode, avail_px, font, ar):
        """Deliberately unmeasurable, for two independent reasons.
        
        A text area already handles its own overflow by scrolling -- it adds a
        vertical slider when the content exceeds its bounds -- so it does not
        need the row to grow around it the way a plain label does.
        
        And measuring it would mean running the whole rich-text parse (images,
        ship/face embeds, tables, wrapping) at a width the parent has not
        committed to yet, then throwing that work away. Falling back to flex is
        both cheaper and closer to what the widget is for."""
    def on_message (self, event):
        ...
    def parse_header (self, header):
        ...
    def parse_style_line (self, line):
        ...
    def split_styled_lines (self, some_lines):
        ...
    def update (self, message):
        ...
    @property
    def value (self):
        ...
    @value.setter
    def value (self, message):
        ...
class TextLine(object):
    """class TextLine"""
    def __init__ (self, text, style, width, height, is_sec_end) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
