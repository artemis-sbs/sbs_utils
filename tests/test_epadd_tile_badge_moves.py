"""A tile's badge that does not fit beside its title moves to a line of its own.

Seen in the engine (author course 3, lesson 1, 1280x960): the handheld's Boarding Party
tile read "Boardin" / "Party" - the word cut - because its badge, the visit's place title
"Ferrow Landing", took the room on the title's row. A badge can be a mission's words, and
the title row is one line by construction, so the badge MOVES to a line under the title.
A count (`3 new`) still fits and stays beside its title.

    python -m unittest tests.test_epadd_tile_badge_moves
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

import cosmos_dev.mock.sbs as sbs          # registers the bare `sbs` shim
from sbs_utils.helpers import Context, FakeEvent, FrameContext, props_display_text
from sbs_utils.gui import GuiClient
from sbs_utils.agent import clear_shared
from sbs_utils.vec import Vec3
from sbs_utils.mast_sbs.maststorypage import StoryPage
from sbs_utils.mast_sbs.story_nodes.gui_app_decorator_label import GuiAppDecoratorLabel
from sbs_utils.procedural.gui.epadd import gui_app_register, gui_app_home

ENGI = 0x8000000000000007


class _FakeSim:
    time_tick_counter = 0


class _Main:
    def __init__(self, page):
        self.page = page


class _Task:
    def __init__(self):
        self.main = None

    def jump(self, label):
        pass

    def tick_in_context(self):
        pass

    def set_variable(self, *a, **k):
        pass

    def get_variable(self, *a, **k):
        return None

    def compile_and_format_string(self, s):
        return s

    def format_string(self, s):
        return s

    def eval_code_checked(self, code):
        return True


def _page():
    page = StoryPage()
    page.pending_gui = False
    page.client_id = ENGI
    page.console = "normal_engi"
    page.gui_task = _Task()
    page.gui_task.main = _Main(page)
    return page


def _walk(item, out):
    out.append(item)
    for attr in ("rows", "columns"):
        for child in getattr(item, attr, None) or ():
            _walk(child, out)


def _items(page):
    out = []
    for layout in page.pending_layouts:
        _walk(layout, out)
    if page.pending_row is not None:
        _walk(page.pending_row, out)
    return out


def _text_of(item):
    return (props_display_text(getattr(item, "value", None)) or "").strip()


class TileBadgeTests(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(ENGI, "test"))
        FrameContext.page = None
        FrameContext.task = None
        clear_shared()
        GuiAppDecoratorLabel.clear()
        GuiClient(0)
        GuiClient(ENGI)
        self.saved = dict(FrameContext.aspect_ratios)
        FrameContext.aspect_ratios[ENGI] = Vec3(1280, 960, 0)
        for p in ("boarding_party", "messages"):
            GuiAppDecoratorLabel(p)
        # LegendaryMissions' own registrations, with c3-01's badges.
        gui_app_register("boarding_party", title="Boarding Party", icon="epadd.boarding",
                         group="Ship", sort=1,
                         description="Join the boarding party, or come back",
                         status=lambda: "Ferrow Landing")
        gui_app_register("messages", title="Messages", icon="epadd.messages",
                         group="Ship", sort=3, description="From the crew, and from home",
                         status=lambda: "3 new")

    def tearDown(self):
        FrameContext.aspect_ratios.clear()
        FrameContext.aspect_ratios.update(self.saved)
        FrameContext.page = None
        FrameContext.task = None
        FrameContext.context = None
        GuiAppDecoratorLabel.clear()

    def tile_rows(self, tab):
        """The text on each row of one tile, top to bottom."""
        page = _page()
        FrameContext.page = page
        FrameContext.task = page.gui_task
        gui_app_home()
        tile = next(i for i in _items(page)
                    if str(getattr(i, "_click_tag", "")) == f"epadd-app-{tab}")
        rows = []
        for row in getattr(tile, "rows", None) or ():
            found = []
            _walk(row, found)
            words = [_text_of(i) for i in found if _text_of(i)]
            if words:
                rows.append(words)
        return rows

    def test_a_place_title_gets_its_own_line(self):
        rows = self.tile_rows("boarding_party")
        title_row = next(r for r in rows if "Boarding Party" in r)
        self.assertNotIn("Ferrow Landing", title_row)
        self.assertIn(["Ferrow Landing"], rows)
        # Under the title, above the description.
        self.assertLess(rows.index(title_row), rows.index(["Ferrow Landing"]))

    def test_a_count_still_sits_beside_its_title(self):
        rows = self.tile_rows("messages")
        self.assertIn(["Messages", "3 new"], rows)


if __name__ == "__main__":
    unittest.main()
