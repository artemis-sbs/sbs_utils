from sbs_utils.pages.layout.bounds import Bounds
from sbs_utils.pages.layout.column import Column
from sbs_utils.pages.widgets.control import Control
from sbs_utils.helpers import FrameContext
from textwrap import TextWrapper
def _choice_options (urn):
    """`[](choices://?fill=#234&layout=stack)` -> the ChoiceFlowLine options it sets."""
def _icon_send (SBS, client_id, region_tag, tag, urn, left, top, right, bottom, layer=None):
    """Draw `icon://` art into a rect. The urn is an icon NAME (`check.on`, `wanted`)
    or a sheet INDEX (`137`), plus `?color=`. A name is resolved the way
    `gui_icon_name` resolves it, so a mission that re-skins a name re-skins it here too;
    a name nobody knows draws nothing (a wrong glyph looks deliberate)."""
def _layer_prop (layer):
    """``draw_layer:N;`` for a raised container, or ``''`` when nobody asked for one.
    
    A SUFFIX rather than a parameter, so a props string in an unraised text area is
    emitted byte-for-byte as it always was and nothing existing can shift.
    
    WHY THE RICH PATH NEEDS THIS AT ALL. `_present_simple` gets the cascade for free
    (`get_cascade_props(..., layer=True)`), but the rich path builds its own per-segment
    props and so drops it -- which meant a markdown text area in a RAISED container
    (an overlay panel with an opaque background above it) rendered underneath its own
    backdrop and vanished. The cascade still must not go into the `$$` per-line
    mini-language, which is what the comment in `_apply_cascade` protects: that is a
    style string the text area parses itself, not one the engine reads."""
def _lead_px (ns, urn, font):
    ...
def _lead_send (SBS, client_id, region_tag, tag, ns, urn, left, top, right, bottom, layer=None):
    """Draw a lead picture of any kind into a square rect."""
def _line_has_embed (line):
    """Does this line carry an `ns://urn` the rich path would turn into a widget?
    
    `RE_LINK_REF` has every group optional, so it matches almost any line - a bare `ns` is
    what says a reference is present at all, and the scheme is what says it draws something."""
def _line_is_choice (line):
    """A lone choice is still a button: the fast path would print its markup."""
def _split_scheme (urn):
    """`image://arrow` -> ("image", "arrow"); a bare `check.on` is an icon."""
def amd_parse_url (text):
    """`key?scale=0.5&align=center` -> `{"url": "key", "scale": "0.5", ...}`.
    
    Values stay STRINGS; every caller coerces to what it needs. Malformed pairs
    are skipped rather than raising - a mistyped option should cost the option,
    not the image."""
def amd_table_rows (raw_rows):
    """Raw `|a|b|` lines -> `(rows, aligns)`.
    
    `aligns` is one of `l`/`c`/`r` per column, taken from the `|:--|--:|`
    separator row, which is dropped from the data. A table with no separator
    renders all-left with row 0 as the header, so the separator is optional."""
def amd_table_scan (lines, i):
    """A GFM pipe table starting at `lines[i]` -> `(rows, next_index)`, else None.
    
    A table is **2 or more** consecutive lines starting with `|`. The pair is
    required deliberately: a lone `|` line is prose (a table drawn in words, an
    ASCII diagram, a sentence about a pipe) and must stay prose."""
def gauge_has_text (spec):
    ...
def gauge_height_px (spec):
    """Natural height: one line of text (if any) plus the bar."""
def gauge_send (SBS, client_id, region_tag, tag, left, top, right, bottom, spec, ar, layer=None, justify='left'):
    """Draw one gauge into a rect (percent units, like every send_gui_*).
    
    `justify` places a label that stands ALONE (the ENGN cell is centred by its
    column); a label with a value is always label-left, value-right, the way the
    engine lays out "Energy ...... 946"."""
def gauge_spec_from_url (urn, label='', font='gui-2'):
    """`946?max=1000&show=frac&warn=0.4&invert=1` (after `gauge://`) -> spec."""
def gauge_value_text (spec):
    ...
def get_client_aspect_ratio (cid):
    """Get the aspect ratio of the specified client's screen.
    Args:
        cid (int): The client ID.
    Returns:
        Vec3: The aspect ratio. If Vec3.z is 99, then the client hasn't set the aspect ratio."""
def get_font_size (font):
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
    """`key?scale=0.5&align=center` -> `{"url": "key", "scale": "0.5", ...}`.
    
    Values stay STRINGS; every caller coerces to what it needs. Malformed pairs
    are skipped rather than raising - a mistyped option should cost the option,
    not the image."""
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
class ChoiceFlowLine(object):
    """A group of `[Display](signal://name?k=v)` lines, drawn as ONE wrapping row of
    flat buttons - a wrap panel. Clicking one routes back to the owning TextArea,
    which consumes the group and emits the signal.
    
    Flat, not `send_gui_button`: each chip is a filled image, its words, and a
    transparent clickregion the size of the whole chip - the build the ePADD app links
    and the tab strip use - so it looks like part of the document, not engine chrome.
    
    Packing happens here, in pixels, at the width the text is drawn at. A chip is as
    wide as its label plus padding; chips go left to right and a chip that does not
    fit starts a new row. A label wider than a whole row gets a row to itself and
    wraps inside its chip. The line is as tall as its rows, so scrolling, `follow_tail`
    and the rest of the area treat it as one line.
    
    A chip with no click tag is a CHOSEN one - `[Display](chosen://)`, what a group
    leaves behind - drawn in the quieter chosen colors with no hit area."""
    def __init__ (self, choices, ar, pixel_width, options=None) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def pack (choices, pixel_width, opts):
        """Chips as `(x, y, w, h, choice)` in pixels, packed into rows."""
    def send_gui (self, SBS, client_id, region_tag, tag, left, top, right, bottom, layer=None):
        ...
class FaceLine(object):
    """class FaceLine"""
    def __init__ (self, text, ar) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def send_gui (self, SBS, client_id, region_tag, tag, left, top, right, bottom, layer=None):
        ...
class FoldLine(IconLine):
    """A collapsible heading (`##+ Title` / `##- Title`): the expand or collapse icon,
    the title in its heading style, and a click region over the whole line that
    routes back to the owning TextArea to open or close the section."""
    def __init__ (self, title, style, is_open, click_tag, ar, pixel_width) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def send_gui (self, SBS, client_id, region_tag, tag, left, top, right, bottom, layer=None):
        ...
class GaugeLine(object):
    """A whole-line gauge `[Energy](gauge://946?max=1000)`: label left, value right,
    a bar colored by fraction underneath. The drawing is `layout/gauge.py`'s, shared
    with the `gui_gauge` widget."""
    def __init__ (self, label, urn, ar) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def send_gui (self, SBS, client_id, region_tag, tag, left, top, right, bottom, layer=None):
        ...
class HrLine(object):
    """Horizontal rule (`<hr>` / `<hr/>`) — a thin full-width divider. Uses `<hr>`
    rather than `---` so it never clashes with the table separator row."""
    def __init__ (self, ar) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def send_gui (self, SBS, client_id, region_tag, tag, left, top, right, bottom, layer=None):
        ...
class IconLine(object):
    """`![](icon://name) text` - an icon one text line tall, the text wrapped beside it.
    
    Starting a list item with one (`- ![](icon://check.on) Shields up`) makes the icon
    the item's BULLET: it replaces the `-` or number, and wrapped lines stay aligned
    under the text, not under the icon."""
    def __init__ (self, urn, text, style, ar, pixel_width, ns='icon') -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def send_gui (self, SBS, client_id, region_tag, tag, left, top, right, bottom, layer=None):
        ...
class ImageLine(object):
    """class ImageLine"""
    def __init__ (self, text, ar) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def send_gui (self, SBS, client_id, region_tag, tag, left, top, right, bottom, layer=None):
        ...
class LinkLine(object):
    """A whole-line hyperlink `[Display](ref://key)`. Renders as styled clickable
    text plus a transparent clickregion on top whose click_tag routes back to the
    owning TextArea's on_message, which resolves the key (intra-document nav)."""
    def __init__ (self, display, click_tag, ar, sbs, font='gui-2') -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def send_gui (self, SBS, client_id, region_tag, tag, left, top, right, bottom, layer=None):
        ...
class ShipLine(object):
    """class ShipLine"""
    def __init__ (self, text, ar) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def send_gui (self, SBS, client_id, region_tag, tag, left, top, right, bottom, layer=None):
        ...
class TableLine(object):
    """A GFM pipe-table rendered as a grid of text cells — a block-line like
    ImageLine/FaceLine (owns its rect via send_gui). Columns are sized to their
    measured content then shrunk to fit the region width (never overflow — there's
    no horizontal scroll); row height is the tallest wrapped cell. Per-column
    alignment comes from the |:--|--:| separator row. Keep tables SMALL/static:
    scrolling is line-indexed so a tall table clips at the block boundary."""
    def __init__ (self, rows, aligns, ar, pixel_width, sbs, link_map=None, link_prefix='lnk') -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def _font (self, ri):
        ...
    def _icon_px (font):
        ...
    def send_gui (self, SBS, client_id, region_tag, tag, left, top, right, bottom, layer=None):
        ...
class TextArea(Control):
    """class TextArea"""
    def __init__ (self, tag, message, markdown=True, line_styles=None) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def _build_table (self, raw_rows, ar, pixel_width):
        """Parse GFM pipe rows into a TableLine. The |:--|--:| separator row (if
        present) supplies per-column alignment and is dropped from the data; a
        table with no separator row just renders all-left with row 0 as header."""
    def _callout_styles (self):
        """Register the callout named styles once, from their ONE definition.
        
        Lazy and local: `procedural.amd_callout` is stdlib-shallow (it reaches only
        `procedural.amd`, which is `re` + `fs`), but importing it at module scope
        would still tie this widget's import order to the procedural package for a
        feature most text areas never use."""
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
    def _repaint (self, event):
        """Redraw after a click, scroll or fold.
        
        On its own this area re-sends itself. Inside a REGION that is wrong: the engine
        draws the new paint over the old one (a scroll showed both). There the region's
        owner has to repaint, so `repaint_cb(area)` - set by whoever owns it - is asked
        to, and this area draws nothing itself."""
    def _scan_choice_group (lines, i):
        """The choice group starting at `lines[i]` -> `(choices, next_index)`, else None.
        
        A group is consecutive `signal://` / `chosen://` lines; anything else, a
        blank line included, ends it. Each choice is a dict with `display`, and for
        a live one `signal` (the name) and `data` (the query, as strings)."""
    def _scroll_to_fold (self, key):
        """After a toggle, keep the heading that was clicked on screen."""
    def append (self, text, sep='\n\n'):
        """Add text to the end of the document - how a story continues after a choice.
        
        `value` reads back as a LIST of lines, so `value += "..."` does not do this.
        A blank line goes between by default, so the new text starts a paragraph."""
    def calc (self, client_id):
        ...
    def calc_rich (self, client_id, _retry=True):
        ...
    def choose (self, click_tag, client_id=None):
        """Make the choice behind `click_tag`: consume its group, then emit its signal.
        
        The group is replaced by the one choice made, as `[Display](chosen://name)`,
        so the reader is left with the story so far and a second click finds nothing
        to press. The signal is emitted AFTER, so a route that appends the next
        scene appends it below the choice. Returns the choice, or None."""
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
    def represent (self, event):
        """A dirty pass redrawing this area on its own - unless its OWNER repaints it.
        
        With `repaint_cb` set the area lives in a region its owner rebuilds, and a rebuild
        reuses the same sub-region tags. So a self-redraw is not merely out of band, it
        is stale: engine-seen, a picked choice settled the OLD area (`choose` sets its
        value, which marks it dirty), the owner's rebuild drew the new transcript, and
        then this pass painted the old one over it - "the pick does nothing until
        something else changes". The owner's in-band present calls `present`, not this."""
    def split_styled_lines (self, some_lines):
        ...
    def toggle_fold (self, key, client_id=None):
        """Open a closed section or close an open one, by its heading key
        (`"##" + title`). Returns the new state, or None for an unknown key."""
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
