from sbs_utils.pages.layout.clickable import Clickable
from sbs_utils.helpers import FakeEvent
from sbs_utils.helpers import FrameContext
from sbs_utils.mast.parsers import LayoutAreaParser
def _back_pack (heights, avail, item_height, sel):
    """The topmost row that can start the view while row `sel` still fits at the
    BOTTOM. Packs upward from `sel`, taking rows until the next one overflows."""
def accepts_kwargs (func):
    ...
def apply_control_styles (control_name, extra_style, layout_item, task):
    """Apply a named control style and optional overrides to a layout item.
    
    ``extra_style`` may be a raw CSS-style string (``"key:value;..."``) or
    a style name. It is applied on top of the base ``control_name`` style.
    
    Args:
        control_name (str): Base control style name.
        extra_style (str | dict | None): Additional style string, name, or
            parsed dict applied after the base style.
        layout_item (LayoutItem): Layout item to receive the style.
        task (MastAsyncTask): GUI task used for string formatting."""
def compose_handler (existing, layout_item, runtime_node):
    """Return the `(layout_item, node)` tuple a tag_map key should now hold.
    
    Replaces, exactly as before, unless there is a real handler already
    registered for this same widget -- then the two are chained."""
def get_client_aspect_ratio (cid):
    """Get the aspect ratio of the specified client's screen.
    Args:
        cid (int): The client ID.
    Returns:
        Vec3: The aspect ratio. If Vec3.z is 99, then the client hasn't set the aspect ratio."""
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
def invoke_message_cb (cb, event, item):
    """Call whatever is in an `on_message_cb` slot: chain, object, or function."""
def layout_list_box_control (items, template_func=None, title_template=None, section_style=None, title_section_style=None, select=False, multi=False, carousel=False, collapsible=False, read_only=False):
    ...
def max_cur (heights, avail, item_height=0.0):
    """The largest `cur` that still shows the LAST row -- the scroll RANGE.
    
    Not `len(heights) - pack_slots(..., start=cur)`. That counts how many rows fit
    *from where the view happens to be*, which with real per-row heights changes as
    you scroll: the same 40-item list reported a range of 19 at cur=0 and 39 at
    cur=39, so the scrollbar's own `high` moved under the thumb and the list could
    scroll off its own end. This answer does not depend on `cur` at all."""
def pack_slots (heights, avail, item_height=0.0, start=0):
    """How many rows fit starting at `start`, packing REAL heights."""
def reveal_cur (sel, cur, heights, avail, item_height=0.0):
    """Where the view must start so row `sel` is visible, moving the LEAST.
    
    `sel`, `cur` and `heights` are all in DISPLAY space -- the rows actually on
    show. A collapsible list also has an unfiltered index space; passing one of
    those in points past the end of the shorter list, which is how this broke the
    Control Gallery's index. Clamped rather than trusted.
    
    Above the window, scroll up to it. Below, back-pack UPWARD from it so it
    lands at the BOTTOM -- the smallest move that reveals it, where
    set_selected_index(i, True) would slam it to the top on every repaint."""
class LayoutListBoxHeader(object):
    """class LayoutListBoxHeader"""
    def __init__ (self, label, collapse, indent=0, selectable=False, data=None, visual_indent=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
class LayoutListbox(Column):
    """A widget to list things passing function/lamdas to get the data needed for option display of
     a template """
    def __init__ (self, left, top, tag_prefix, items, item_template=None, title_template=None, section_style=None, title_section_style=None, select=False, multi=False, carousel=False, collapsible=False, read_only=False, reveal=False, hint=None) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def _listbox_size (self, value, aspect_axis):
        """Resolve a style value against the LISTBOX's own font.
        
        It was resolved against a hard-coded font size of 20, so `0.1em` on a listbox
        was never 0.1 of anything on screen - while the same expression in one of its
        rows used the row's real font."""
    def _merge_tags (self, client_id, sub_page):
        """Publish this draw's row widgets to the real page, and retract the last one's.
        
        The other two SubPage users (overlay, tabbed panel) have always done the
        merge; the listbox never did, which is the whole of LM #349 -- gui_update
        resolves against page.tag_map, and the row widgets were never in it.
        
        The retraction is the part they are missing. A row that scrolled off the
        screen leaves an entry pointing at a widget that is no longer drawn; a later
        update would call present() on it and paint at coordinates that belong to
        nothing. Only entries THIS listbox put there and did not build again are
        taken back, so a same-named widget elsewhere on the page is untouched."""
    def _on_message (self, event):
        ...
    def _present (self, event):
        """present
        
        builds/manages the content of the widget
        Args:
            event (event): The event that triggered the gui to update"""
    def apply_selection_hint (self, hint):
        """Apply a hint. Always a HINT -- stale is the normal case (a shorter
        list, a collapsed section, another screen entirely), so everything is
        clamped and the reveal has the final word."""
    def calc_max (self, CID):
        """Measure the items. Returns (max_width, max_height, avg_height).
        
        avg_height exists because slot budgeting used to divide the available
        space by the TALLEST item, which silently assumes every row is the same
        height. One tall row then shrank the whole list: eleven 48px consoles
        with a single 96px one showed six rows and left half the box empty.
        
        For a UNIFORM list avg == max, so every existing listbox budgets exactly
        as it did before. Only a list with genuinely varying rows changes."""
    def clear_selection_locks (self):
        ...
    def convert_value (self, item):
        ...
    def default_item_template (self, item):
        ...
    def default_title_template (self):
        ...
    def get_selected (self):
        ...
    def get_selected_index (self):
        ...
    def get_selection_hint (self):
        """An OPAQUE token describing where this listbox is looking.
        
        Hand it to the next clone after a repaint, so the row under the user's
        mouse stays under it:
        
            on change lb.value:
                saved = lb.get_selection_hint()
                jump repaint
            ...
            lb = gui_list_box(items, style, select=True, reveal=True, hint=saved)
        
        Do not inspect it. `selected_index` is in UNFILTERED space because that
        is what set_selected_index takes; `slot` is a DISPLAY position, recorded
        for a future resize policy and not used to restore today. Mixing those
        two spaces is what broke this twice."""
    def get_value (self):
        ...
    def invalidate_regions (self):
        ...
    @property
    def items (self):
        ...
    @items.setter
    def items (self, items):
        ...
    def on_carousel_click (self, event):
        ...
    def on_click (self, event):
        ...
    def on_collapse_header (self, event):
        ...
    def on_message (self, event):
        ...
    def on_scroll (self, event):
        ...
    def present (self, event):
        ...
    def redraw_if_showing (self):
        """Redraw if this is already one screen.
        Since sub_region is used if you present too early it will confuse the gui."""
    def remember_alias_props (self, alias, props):
        """Hold what gui_update() wrote to a row, so the next draw can re-apply it.
        
        Without this the update lasts only until the list next draws -- the template
        rebuilds the row from the item data and the change is gone. Cleared whenever
        `items` is replaced, since new data makes old overrides meaningless."""
    def represent (self, event):
        ...
    def select_all (self):
        ...
    def select_none (self):
        ...
    def set_col_width (self, width):
        ...
    def set_item_gap (self, gap):
        """The spacing BETWEEN items. This is what `row-height` used to mean here."""
    def set_read_only (self, v):
        ...
    def set_row_height (self, height):
        """The height of ONE item row - what `row-height` means everywhere else.
        
        A FLOOR, not a cap: a template that needs more space grows past it, so a
        two-line row is never clipped into a one-line click region."""
    def set_selected_index (self, i, set_cur=True):
        ...
    def set_selection_lock (self, o, lock):
        ...
    def set_selection_lock_index (self, i, lock):
        ...
    def set_value (self, value):
        ...
    def update (self, props):
        ...
    @property
    def value (self):
        ...
    @value.setter
    def value (self, v):
        ...
class SubPage(object):
    """A class for use with the layout listbox to make using the procedural gui function work
        """
    def __init__ (self, tag_prefix, region_tag, task, client_id, owner=None, register=True) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def add_alias (self, layout_item, runtime_node=None):
        """Register an author's `tag:` name for a widget built inside this sub-page.
        
        Same idiom as StoryPage.add_alias: an extra key in the same tag_map, which
        the owner then merges into the real page. The engine tag stays the
        slot-namespaced one this shim hands out, so the owner's
        `sub_tag.startswith(tag_prefix)` routing keeps working (LM #349)."""
    def add_content (self, layout_item, runtime_node):
        ...
    def add_row (self):
        ...
    def add_tag (self, layout_item, runtime_node):
        ...
    def get_pending_row (self):
        ...
    def get_tag (self):
        ...
    def next_slot (self, slot, section):
        ...
    def pop_sub_section (self, add, is_rebuild):
        ...
    def present (self, event):
        ...
    def push_sub_section (self, style, layout_item, is_rebuild):
        ...
