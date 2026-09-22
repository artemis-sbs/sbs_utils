"""A faithful-enough model of the engine's GUI display list, for headless tests.

WHY THIS EXISTS. `cosmos_dev/mock/sbs.py`'s `send_gui_*` are no-ops, and the mockgui
browser keeps a display list but with the WRONG rule: an out-of-rebuild send that it
cannot match by tag is silently DISCARDED. The engine creates a new widget instead. So
a re-send addressed to the wrong region - or under a tag nothing on screen is wearing -
looks like a clean in-place update headless, and puts a duplicate on a real bridge.

That cost three engine round trips on one defect ("two buttons after a press", then
"multiple buttons, and they don't work"), because every headless measurement agreed
with code that could not work.

THE ENGINE'S RULE, from the user, 2026-09-22:

    "If the tag and region tag are the same, it should replace the existing object."

So identity is the PAIR (region_tag, tag), not the tag alone:

* a send whose (region, tag) is already on screen REPLACES it - this is the in-place
  update the dirty system is built on, and it works;
* a send whose pair is NOT on screen CREATES a widget - including a re-send that names
  a different region than the one the widget was built into;
* `send_gui_clear(region)` wipes that region's BACK buffer and opens a rebuild;
  sends during a rebuild fill the back buffer; `send_gui_complete(region)` swaps it
  forward. The swap only fires when the back buffer holds something - completing an
  empty one leaves the old content up (see
  memory/reference_region_buffer_swap_needs_content).

This models the display list only - no geometry, no rendering. It answers the one
question the mock could not: HOW MANY widgets are on screen, and under what tags.
"""


class GuiDisplay:
    """One client's display list: regions, each with a front and back buffer."""

    def __init__(self):
        self.clear_all()

    def clear_all(self):
        # region tag -> {"front": {tag: props}, "back": {...}, "open": bool}
        # "" is the root region, which always exists.
        self._regions = {"": {"front": {}, "back": {}, "open": False}}

    # --- the engine calls ----------------------------------------------------
    def region(self, tag):
        r = self._regions.get(tag)
        if r is None:
            r = {"front": {}, "back": {}, "open": False}
            self._regions[tag] = r
        return r

    def send(self, kind, parent, tag, props=None):
        """A widget send. `parent` is the region tag; "" is root."""
        region = self.region(parent or "")
        item = {"kind": kind, "props": props, "region": parent or ""}
        if region["open"]:
            # Inside a rebuild: fills the back buffer.
            region["back"][tag] = item
            return "back"
        # Outside a rebuild: replace when this exact (region, tag) is showing,
        # otherwise CREATE. The create branch is the one the browser gets wrong.
        if tag in region["front"]:
            region["front"][tag] = item
            return "replaced"
        region["front"][tag] = item
        return "created"

    def sub_region(self, parent, tag):
        """Establish a child region. Registering it is enough for this model."""
        self.region(tag)
        self.region(parent or "")

    def clear(self, tag):
        """Wipe the region's BACK buffer and open a rebuild on it."""
        region = self.region(tag or "")
        region["back"] = {}
        region["open"] = True

    def complete(self, tag):
        """Swap back -> front, but only if the back buffer holds something."""
        region = self.region(tag or "")
        region["open"] = False
        if not region["back"]:
            return False
        region["front"] = region["back"]
        region["back"] = {}
        return True

    # --- what a test asks ----------------------------------------------------
    def showing(self, region_tag=None):
        """{tag: item} on screen - in one region, or every region merged."""
        if region_tag is not None:
            return dict(self.region(region_tag)["front"])
        out = {}
        for tag, region in self._regions.items():
            for wtag, item in region["front"].items():
                out[f"{tag}|{wtag}"] = item
        return out

    def count(self, kind=None, region_tag=None):
        """How many widgets are on screen, optionally of one kind."""
        items = self.showing(region_tag).values()
        return len([i for i in items if kind is None or i["kind"] == kind])

    def tags(self, kind=None, region_tag=None):
        return sorted(k for k, i in self.showing(region_tag).items()
                      if kind is None or i["kind"] == kind)


#: client id -> GuiDisplay. Reset by `gui_display_clear()`; the mission runner and
#: tests both call it, so nothing survives into the next mission.
_DISPLAYS = {}


def gui_display(client_id):
    d = _DISPLAYS.get(client_id)
    if d is None:
        d = GuiDisplay()
        _DISPLAYS[client_id] = d
    return d


def gui_display_clear(client_id=None):
    """Forget one client's display list, or every client's."""
    if client_id is None:
        _DISPLAYS.clear()
    else:
        _DISPLAYS.pop(client_id, None)
