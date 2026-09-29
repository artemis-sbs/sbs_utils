from ...helpers import FrameContext
from ..style import apply_control_styles
from .update import gui_represent

def gui_section(style=None):
    """Create a top-level GUI layout section at a specific screen area.

    Sections are the primary way to position content on screen. The ``area``
    style property sets the region (left, top, right, bottom as percentages).
    Content added after this call is placed inside the section until the next
    ``gui_section`` or the frame ends.

    Args:
        style (str, optional): CSS-like style string. Use ``area:`` to position
            the section, e.g. ``"area:10,10,90,90;"``. Defaults to None.

    Returns:
        Layout: The layout object for this section.

    Example:
        gui_section(style="area:5,5,95,50;")
        gui_text("Top half of screen")
        gui_section(style="area:5,50,95,95;")
        gui_text("Bottom half of screen")
    """

    page = FrameContext.page
    task = FrameContext.task
    if page is None:
        return None
    
    page.add_section()
    layout_item = page.get_pending_layout() 
    apply_control_styles(".section", style, layout_item, task)
    # Same as gui_row: a section is not add_content'ed, so register its `tag:` name
    # here or it is unreachable (LM #349).
    add_alias = getattr(page, "add_alias", None)
    if add_alias is not None:
        add_alias(layout_item)
    return layout_item

class PageSubSection:
    def __init__(self, style) -> None:
        page = FrameContext.page
        self.sub_section = None
        if page is None:
            return None
        self.page = page
        self.style = style
        self.add = True

    @property
    def tag(self):
        if self.sub_section is not None:
            return self.sub_section.tag
        return None
    
    @property
    def click_tag(self):
        if self.sub_section is not None:
            return self.sub_section.click_tag
        return None
    
    @click_tag.setter
    def click_tag(self, v):
        if self.sub_section is not None:
            self.sub_section.click_tag = v

    @property
    def on_message_cb(self):
        # Without this forward, gui_message_callback / gui_message_label on a
        # gui_sub_section() landed on this wrapper, which nothing reads -- the
        # example in gui_message_label's own docstring was a silent no-op.
        if self.sub_section is not None:
            return self.sub_section.on_message_cb
        return None

    @on_message_cb.setter
    def on_message_cb(self, v):
        if self.sub_section is not None:
            self.sub_section.on_message_cb = v
    
    def is_message_for(self, event):
        """Used by MessageTrigger i.e. gui_message to know if message is for this object

        Args:
            event (EVENT): the engine event

        Returns:
            bool: if the gui_message MessageTrigger should be True
        """
        return event.sub_tag == self.sub_section.tag or event.sub_tag == self.sub_section.click_tag

    def __enter__(self):
        # Allow reentering
        self.sub_section = self.page.push_sub_section(self.style, self.sub_section, False)
        

    # Pythons expects 4 args, mast only 1
    # Python's are exception related
    def __exit__(self, ex=None, value=None, tb=None):
        self.page.pop_sub_section(self.add, False)
        self.add = False
        if ex:
            return False
        return True

    def represent(self, event):
        if self.sub_section is not None:
            self.sub_section.represent(event)

    def show(self, _show):
        # `sub_section` is the Layout, and it does not exist until the `with`
        # block has run -- so every forward here has to tolerate being called
        # before the sub-section was ever built. A no-op is the right answer,
        # not an error: Dirty.mark_dirty already returns silently for a layout
        # that has no client_id yet, so there is nothing to act on either way.
        if self.sub_section is not None:
            # Layout.show() marks itself dirty, so unlike PageRegion this needs
            # no second mark_visual_dirty(). It marks only ITSELF, though: the
            # siblings reclaim the space on the PARENT's next layout pass, since
            # calc() filters is_hidden_by_script out of the width split.
            self.sub_section.show(_show)

    @property
    def is_hidden(self):
        if self.sub_section is None:
            # Not built yet is not visible.
            return True
        return self.sub_section.is_hidden


def gui_sub_section(style=None):
    """Create a nested layout sub-section, used as a context manager.

    Sub-sections let you group and style a subset of content within the current
    section. Use with Python's ``with`` statement in MAST via the ``with``
    keyword. The sub-section is added to the current layout when the ``with``
    block exits.

    The returned object can be hidden and restored after it is built, with
    ``gui_hide`` / ``gui_show`` or its own ``show()``. Hiding takes the whole
    sub-tree off screen, and its siblings reclaim the space on the next layout
    pass. Hold on to the object to do that - hiding one before its ``with``
    block has run is a no-op, since the layout it stands for does not exist yet.

    Args:
        style (str, optional): CSS-like style string controlling the column
            width, row height, background, etc. of the sub-section.
            Defaults to None.

    Returns:
        PageSubSection: Context manager object with ``show()`` and
            ``is_hidden``. Use with ``with``.

    Example:
        gui_row(style="row-height:3em;")
        with gui_sub_section(style="col-width:30%;"):
            gui_text("Left column")
        right = gui_sub_section()
        with right:
            gui_text("Right column")
        gui_hide(right)     # and gui_show(right) to bring it back
    """
    return PageSubSection(style)

from ...pages.layout.layout import RegionType


def _control_tags(layout):
    """The tags of every Control (text area, listbox) in a layout's CURRENT tree - each
    one is its own engine sub-region, `<tag>$$`."""
    from ...pages.widgets.control import Control
    out = set()

    def walk(node):
        for row in getattr(node, "rows", None) or []:
            for col in getattr(row, "columns", None) or []:
                if isinstance(col, Control) and col.tag is not None:
                    out.add(str(col.tag))
                walk(col)
    walk(layout)
    return out


class PageRegion:
    """A re-drawable area. REBUILDING ONE REUSES ITS TAGS.

    ENGINE-SEEN 2026-09-29 (xESS Act): a text area or listbox is its OWN engine
    sub-region, and clearing the parent region does not take old child sub-regions with
    it. Every rebuild made new ones under the next build-order tags, so the old ones
    stayed on screen underneath - the transcript was drawn once per rebuild, stacked, at
    whatever scroll each had. So after `rebuild()`, the next fill hands out tags derived
    from this region's own (stable) tag: each rebuild reuses the same sub-regions, which
    clear themselves before drawing. One the new fill no longer uses is blanked.
    """

    def __init__(self, style) -> None:
        page = FrameContext.page
        if page is None:
            return None
        self.page = page
        self.style = style
        self.sub_section = None
        self._rebuilding = False
        self._previous = set()
        self._issued = set()
        # Create  top level layout        
        self.sub_section  = gui_section(style)
 
    @property
    def tag(self):
        if self.sub_section is not None:
            return self.sub_section.tag
        return None
    
    @property
    def click_tag(self):
        if self.sub_section is not None:
            return self.sub_section.click_tag
        return None      

    def __enter__(self):
        # Allow reentering
        self.sub_section = self.page.push_sub_section(self.style, self.sub_section, self.sub_section.region)
        self.sub_section.region_type = RegionType.REGION_ABSOLUTE
        if self._rebuilding:
            self._stable_tags_on()

    # Pythons expects 4 args, mast only 1
    # Python's are exception related
    def __exit__(self, ex=None, value=None, tb=None):
        if self._rebuilding:
            self._stable_tags_off()
        self.page.pop_sub_section(False, self.sub_section.region)
        if self.sub_section.region:
            gui_represent(self.sub_section)

    def _stable_tags_on(self):
        prefix = "r%s-" % self.sub_section.tag
        count = [0]
        issued = self._issued = set()

        def get_tag():
            count[0] += 1
            tag = "%s%d" % (prefix, count[0])
            issued.add(tag)
            return tag
        self.page.get_tag = get_tag            # shadows the class method, this page only

    def _stable_tags_off(self):
        if "get_tag" in self.page.__dict__:
            del self.page.get_tag
        self._rebuilding = False
        # Blank what the last fill had and this one does not - with a placeholder,
        # because an empty buffer is never swapped forward.
        cid = getattr(self.page, "client_id", None)
        ctx = FrameContext.context
        if cid is None or ctx is None:
            return
        for tag in sorted(self._previous - self._issued):
            region = tag + "$$"
            ctx.sbs.send_gui_clear(cid, region)
            ctx.sbs.send_gui_text(cid, region, tag + "-blank", "$text: ;", 0, 0, 1, 1)
            ctx.sbs.send_gui_complete(cid, region)
        self._previous = set()

    def show(self, _show):
        self.sub_section.show(_show)
        # Avoid cascade?
        self.sub_section.mark_visual_dirty()

    def rebuild(self):
        """Empty the region for a fresh fill - which reuses the last fill's tags."""
        self._previous = _control_tags(self.sub_section)
        self._rebuilding = True
        self.sub_section.rebuild()
        return self

    @property
    def is_hidden(self):
        return self.sub_section.is_hidden

    def represent(self, e):
        self.sub_section.represent(e)




def gui_region(style=None):
    """Create a re-representable GUI region pinned to an absolute screen area.

    Unlike ``gui_sub_section``, a region uses absolute positioning (the ``area``
    style property) and can be redrawn independently with ``region.represent()``.
    Use it for UI panels that update without redrawing the entire page.
    Also a context manager — content inside the ``with`` block is placed in
    the region.

    Args:
        style (str, optional): CSS-like style string. The ``area:`` property
            sets the absolute screen position (left, top, right, bottom %).
            Defaults to None.

    Returns:
        PageRegion: Context manager object with ``show()``, ``rebuild()``,
            and ``represent()`` methods.

    Example:
        hud = gui_region(style="area:0,0,100,10;")
        with hud:
            gui_text("HUD content here")
        ~~ hud.represent(event) ~~   # refresh just this region later
    """
    return PageRegion(style)

