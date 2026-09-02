"""App badges, and the Status board that gathers them.

A badge is the number a crew reads WITHOUT opening anything, which is the whole reason
the apps carrying live state do not each need a panel on the bridge. Two properties
matter more than the rest:

- **A badge can never take the home screen down.** A provider is mission code doing
  arbitrary work at build time; one that raises must cost its own tile a badge and
  nothing else.
- **The board is a board, not a second launcher.** An app with nothing to say is left
  out, or it is just the app grid again with worse layout.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

import cosmos_dev.mock.sbs as sbs
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.gui import GuiClient
from sbs_utils.agent import clear_shared
from sbs_utils.mast_sbs.maststorypage import StoryPage
from sbs_utils.mast_sbs.story_nodes.gui_tab_decorator_label import GuiTabDecoratorLabel
from sbs_utils.procedural.gui.epadd import gui_app_register, gui_app_badge, gui_app_list, gui_app_revision
from sbs_utils.procedural.gui.status_gui import status_rows, gui_status_screen

ENGI = 7
SERVER = 0


class _Main:
    def __init__(self, page):
        self.page = page


class _Task:
    """The `_FakeGuiTask` shape test_gui_message_multi_handler settled on: enough for
    style parsing (`task.main.page.client_id`) and props formatting."""

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


class _Sim:
    time_tick_counter = 0


def _page(console="normal_engi"):
    page = StoryPage()
    page.pending_gui = False
    page.client_id = ENGI
    page.console = console
    page.gui_task = _Task()
    page.gui_task.main = _Main(page)
    return page


def _walk(item, out):
    out.append(item)
    for attr in ("rows", "columns"):
        for child in getattr(item, attr, None) or ():
            _walk(child, out)


def _all_items(page):
    out = []
    for layout in page.pending_layouts:
        _walk(layout, out)
    if page.pending_row is not None:
        _walk(page.pending_row, out)
    return out


class StatusBase(unittest.TestCase):
    def setUp(self):
        FrameContext.context = Context(_Sim(), sbs, FakeEvent(ENGI, "test"))
        FrameContext.page = None
        FrameContext.task = None
        clear_shared()
        GuiTabDecoratorLabel.clear()
        for cid in (SERVER, ENGI):
            GuiClient(cid)

    def tearDown(self):
        FrameContext.page = None
        FrameContext.task = None
        FrameContext.context = None
        GuiTabDecoratorLabel.clear()

    def app(self, tab, **kw):
        GuiTabDecoratorLabel(tab)
        gui_app_register(tab, **kw)

    def one(self, tab):
        return next(a for a in gui_app_list("engineering") if a["tab"] == tab)


class TestTheBadge(StatusBase):
    def test_a_callable_provider_is_called(self):
        self.app("cargo", title="Cargo", status=lambda: "42/60")
        self.assertEqual(gui_app_badge(self.one("cargo")), "42/60")

    def test_a_plain_string_works_too(self):
        self.app("cargo", title="Cargo", status="steady")
        self.assertEqual(gui_app_badge(self.one("cargo")), "steady")

    def test_no_provider_is_no_badge(self):
        self.app("cargo", title="Cargo")
        self.assertIsNone(gui_app_badge(self.one("cargo")))

    def test_an_empty_answer_is_no_badge(self):
        """A quiet app says nothing rather than '0', so the tile stays clean."""
        for said in ("", "   ", None):
            self.app("cargo", title="Cargo", status=lambda v=said: v)
            self.assertIsNone(gui_app_badge(self.one("cargo")), repr(said))

    def test_a_number_is_rendered_as_text(self):
        self.app("cargo", title="Cargo", status=lambda: 3)
        self.assertEqual(gui_app_badge(self.one("cargo")), "3")

    def test_A_PROVIDER_THAT_RAISES_COSTS_ONLY_ITS_OWN_BADGE(self):
        """The property that keeps mission code from taking the PADD down. A provider
        is arbitrary work run at build time; one that throws must lose its badge and
        nothing else."""
        def boom():
            raise RuntimeError("mission code did something silly")
        self.app("cargo", title="Cargo", status=boom)
        self.assertIsNone(gui_app_badge(self.one("cargo")))

    def test_and_the_screen_still_draws_the_others(self):
        def boom():
            raise RuntimeError("nope")
        self.app("cargo", title="Cargo", status=boom)
        self.app("quest", title="Quests", status=lambda: "3 running")
        rows = status_rows("engineering")
        self.assertEqual([r["title"] for r in rows], ["Quests"])


class TestTheBoard(StatusBase):
    def setUp(self):
        super().setUp()
        self.app("cargo", title="Cargo", group="Ship", sort=10,
                 consoles="engineering", status=lambda: "42/60")
        self.app("fabricate", title="Fabricate", group="Ship", sort=20,
                 consoles="engineering")                       # nothing to say
        self.app("quest", title="Quests", group="Mission", sort=10,
                 status=lambda: "3 running")

    def test_only_apps_that_report_are_on_it(self):
        """A board listing everything is a launcher, and the crew already have one."""
        self.assertEqual([r["title"] for r in status_rows("engineering")],
                         ["Cargo", "Quests"])

    def test_it_is_per_console(self):
        """Cargo is Engineering's; Helm should not be told about its hold."""
        self.assertEqual([r["title"] for r in status_rows("helm")], ["Quests"])

    def test_each_row_carries_the_badge_it_computed(self):
        """Not the provider - a caller that re-ran it could show one value and open on
        another, and a provider can be expensive."""
        rows = {r["title"]: r for r in status_rows("engineering")}
        self.assertEqual(rows["Cargo"]["badge"], "42/60")
        self.assertEqual(rows["Quests"]["badge"], "3 running")

    def test_a_row_still_knows_which_app_it_is(self):
        """Selecting a row opens that app, so the tab has to survive."""
        self.assertEqual({r["tab"] for r in status_rows("engineering")},
                         {"cargo", "quest"})

    def test_nothing_reporting_is_an_empty_board(self):
        clear_shared()
        GuiTabDecoratorLabel.clear()
        self.app("cargo", title="Cargo")
        self.assertEqual(status_rows("engineering"), [])


class TestTheScreen(StatusBase):
    def build(self, page=None):
        page = page or _page()
        FrameContext.page = page
        FrameContext.task = page.gui_task
        self.lb = gui_status_screen()
        return page

    def listboxes(self, page):
        from sbs_utils.pages.widgets.layout_listbox import LayoutListbox
        return [i for i in _all_items(page) if isinstance(i, LayoutListbox)]

    def test_it_draws_a_list_when_something_reports(self):
        self.app("cargo", title="Cargo", status=lambda: "42/60")
        page = self.build()
        self.assertTrue(self.listboxes(page))
        self.assertIsNotNone(self.lb)

    def test_it_says_so_when_nothing_does(self):
        """Rather than an empty panel, which reads as broken."""
        self.app("cargo", title="Cargo")
        page = self.build()
        self.assertEqual(self.listboxes(page), [])
        self.assertIsNone(self.lb)
        self.assertTrue(page.pending_layouts)      # the bar and the line still drew

    def test_the_list_holds_one_row_per_reporting_app(self):
        self.app("cargo", title="Cargo", status=lambda: "42/60")
        self.app("quest", title="Quests", status=lambda: "3 running")
        page = self.build()
        self.assertEqual(len(self.listboxes(page)[0].items), 2)


if __name__ == "__main__":
    unittest.main()


class TestTheHomeScreenKnowsToRepaint(StatusBase):
    """A signal does not wake `await gui()`, so the home screen polls - the same shape
    the inbox and the away console use. Without it the home was frozen at whatever it
    said when it was opened: mail arriving never moved the Messages badge, and an app
    whose route condition turned on never appeared."""

    def test_a_badge_changing_moves_it(self):
        count = [0]
        self.app("messages", title="Messages", status=lambda: f"{count[0]} new")
        before = gui_app_revision("engineering")
        count[0] = 3
        self.assertNotEqual(gui_app_revision("engineering"), before)

    def test_an_app_appearing_moves_it(self):
        """A route condition can turn an app on while the PADD is open - which is how
        the Away Team app shows up when a party forms."""
        self.app("cargo", title="Cargo")
        before = gui_app_revision("engineering")
        self.app("quest", title="Quests")
        self.assertNotEqual(gui_app_revision("engineering"), before)

    def test_an_app_disappearing_moves_it(self):
        from sbs_utils.procedural.gui.epadd import gui_app_unregister
        self.app("cargo", title="Cargo")
        self.app("quest", title="Quests")
        before = gui_app_revision("engineering")
        gui_app_unregister("quest")
        self.assertNotEqual(gui_app_revision("engineering"), before)

    def test_nothing_changing_leaves_it_alone(self):
        """Otherwise the console rebuilds five times a second for no reason."""
        self.app("cargo", title="Cargo", status=lambda: "42/60")
        self.assertEqual(gui_app_revision("engineering"),
                         gui_app_revision("engineering"))

    def test_it_is_per_console(self):
        self.app("cargo", title="Cargo", consoles="engineering", status=lambda: "42/60")
        self.assertNotEqual(gui_app_revision("engineering"),
                            gui_app_revision("helm"))
