"""The ePADD app registry: scoping, ordering, adoption, and staying off by default.

Two properties matter more than the rest and each has a test that fails loudly:

- **The route is the opt-in.** A mission with no `//gui/app/epadd` route has no PADD;
  there is no separate on/off, because an app is not a tab and cannot fall back to one.
- **Nothing disappears.** Turning ePADD on must not hide a tab that no addon has
  registered as an app - it is ADOPTED instead, from what the console itself enabled.
  Without that, flipping the switch on a mission full of third-party addons silently
  removes their panels.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.gui import GuiClient
from sbs_utils.agent import Agent, clear_shared
from sbs_utils.procedural.inventory import set_inventory_value
from sbs_utils.mast_sbs.story_nodes.gui_app_decorator_label import GuiAppDecoratorLabel
from sbs_utils.procedural.gui.epadd import (
    gui_app_register, gui_app_unregister, gui_app_is_registered, gui_app_list,
    gui_app_groups,
    epadd_console_name)

from cosmos_dev.mock import sbs

ENGI = 7
HELM = 8
SERVER = 0


class _Page:
    """Only what the registry reads off a page.

    `gui_task` matters: FrameContext.task falls back to `page.gui_task` whenever a page
    is set and no task was pushed, so a page stub without one raises rather than
    answering None.
    """

    def __init__(self, client_id, console=None, gui_task=None):
        self.client_id = client_id
        self.console = console
        self.gui_task = gui_task


class _FakeSim:
    time_tick_counter = 0


class _FakeTask:
    """Stands in for the GUI task when a route carries an `if`."""

    def __init__(self, answer=True):
        self.answer = answer

    def eval_code_checked(self, code):
        return self.answer


def route(path, if_exp=None):
    """A real `//gui/tab/<path>` label, registered exactly as the compiler would."""
    return GuiAppDecoratorLabel(path, if_exp)


class EpaddBase(unittest.TestCase):
    def setUp(self):
        FrameContext.context = Context(_FakeSim(), sbs, FakeEvent(SERVER, "test"))
        FrameContext.page = None
        FrameContext.task = None
        # set_inventory_value on an id with no Agent is a SILENT no-op, so the clients
        # have to exist before anything can be stored against them.
        clear_shared()
        GuiAppDecoratorLabel.clear()
        for cid in (SERVER, ENGI, HELM):
            GuiClient(cid)

    def tearDown(self):
        FrameContext.page = None
        FrameContext.task = None
        FrameContext.context = None
        GuiAppDecoratorLabel.clear()

    def titles(self, console=None, client_id=None):
        return [a["title"] for a in gui_app_list(console, client_id)]


class TestScoping(EpaddBase):
    def setUp(self):
        super().setUp()
        route("cargo")
        route("help")
        gui_app_register("cargo", title="Cargo", consoles="engineering", group="Ship")
        gui_app_register("help", title="Help", consoles="*", group="Mission")

    def test_a_scoped_app_appears_on_its_console(self):
        self.assertIn("Cargo", self.titles("engineering"))

    def test_and_NOT_on_another(self):
        self.assertNotIn("Cargo", self.titles("helm"))

    def test_a_star_app_appears_everywhere(self):
        self.assertIn("Help", self.titles("helm"))
        self.assertIn("Help", self.titles("engineering"))

    def test_the_engine_console_name_matches_the_script_one(self):
        """`normal_engi` is what the engine calls it; scripts write `engineering`.
        The translation table sat unused inside gui_queue_console_tabs."""
        self.assertEqual(epadd_console_name("normal_engi"), "engineering")
        self.assertIn("Cargo", self.titles("normal_engi"))

    def test_a_multi_console_list_scopes_to_each(self):
        route("airwing")
        gui_app_register("airwing", title="Airwing", consoles="hangar, engineering")
        self.assertIn("Airwing", self.titles("hangar"))
        self.assertIn("Airwing", self.titles("engineering"))
        self.assertNotIn("Airwing", self.titles("helm"))

    def test_the_console_comes_off_the_page_when_not_given(self):
        FrameContext.page = _Page(ENGI, console="normal_engi")
        self.assertIn("Cargo", self.titles())


class TestRouteAuthority(EpaddBase):
    """The `//gui/tab/` route stays the authority on whether a panel exists at all."""

    def test_an_app_with_no_route_is_left_out(self):
        """A registration for a tab nobody defined must not draw a dead tile."""
        gui_app_register("ghost", title="Ghost")
        self.assertEqual(self.titles("engineering"), [])

    def test_a_route_whose_condition_is_false_is_left_out(self):
        route("casino", if_exp="CASINO_ENABLED")
        gui_app_register("casino", title="Casino")
        FrameContext.task = _FakeTask(answer=False)
        self.assertNotIn("Casino", self.titles("hangar"))

    def test_and_is_shown_when_it_is_true(self):
        route("casino", if_exp="CASINO_ENABLED")
        gui_app_register("casino", title="Casino")
        FrameContext.task = _FakeTask(answer=True)
        self.assertIn("Casino", self.titles("hangar"))


class TestAnAppNeedsItsOwnRoute(EpaddBase):
    """Apps are `//gui/app`, and a name can no longer be both.

    There used to be an ADOPTION bridge: a `//gui/tab` nobody registered showed up
    under "Other" so an addon that had never heard of ePADD kept working. It went when
    apps got their own route kind - so the failure it used to absorb, an app whose route
    does not exist, has to be REPORTED instead of silently leaving a gap.
    """

    def setUp(self):
        super().setUp()
        FrameContext.page = _Page(ENGI, console="normal_engi")
        route("cargo")
        gui_app_register("cargo", title="Cargo", consoles="engineering", group="Ship")

    def test_an_app_with_no_route_is_left_off(self):
        gui_app_register("ghost", title="Ghost", consoles="engineering", group="Ship")
        titles = [a["title"] for a in gui_app_list("engineering", ENGI)]
        self.assertIn("Cargo", titles)
        self.assertNotIn("Ghost", titles)

    def test_and_it_is_reported_by_name(self):
        """The whole failure mode of the migration, so it must not be silent."""
        from sbs_utils.procedural.gui import epadd as E
        E._MISSING_ROUTE_REPORTED.clear()
        import sbs_utils.procedural.execution as execution
        seen, orig = [], execution.log
        execution.log = lambda msg, *a, **k: seen.append(msg)
        try:
            gui_app_register("ghost", title="Ghost", consoles="engineering")
            gui_app_list("engineering", ENGI)
        finally:
            execution.log = orig
        self.assertTrue(any("ghost" in m for m in seen), seen)

    def test_the_padd_shell_is_not_a_tile_on_itself(self):
        route("epadd")
        gui_app_register("epadd", title="ePADD", consoles="engineering")
        self.assertNotIn("epadd", [a["tab"] for a in gui_app_list("engineering", ENGI)])


class TestScopingSurvivesThePadd(EpaddBase):
    """A console-scoped app must not vanish the moment you open the PADD.

    `gui_app_list` used to read `page.console` raw, and that is per BUILD - reset to ""
    at every swap - while the PADD's own screens declare no console at all. So once a
    player opened the PADD, `_scoped_here` saw "" and dropped Cargo and Fabricate
    (engineering) and Airwing and Casino (hangar). It also moved `gui_app_revision`,
    which re-entered home once on its own.

    The page already guarded this with its own `_console_identity`; the fix had been
    applied in one place only.
    """

    def setUp(self):
        super().setUp()
        route("cargo")
        route("help")
        gui_app_register("cargo", title="Cargo", consoles="engineering", group="Ship")
        gui_app_register("help", title="Help", group="Mission")
        set_inventory_value(ENGI, "CONSOLE_TYPE", "engineering")

    def titles(self):
        return sorted(a["title"] for a in gui_app_list(client_id=ENGI))

    def test_on_the_console_it_is_there(self):
        FrameContext.page = _Page(ENGI, console="normal_engi")
        self.assertEqual(self.titles(), ["Cargo", "Help"])

    def test_AND_IT_IS_STILL_THERE_INSIDE_THE_PADD(self):
        """The PADD's screens declare no console, so the page answers "" here."""
        FrameContext.page = _Page(ENGI, console="")
        self.assertEqual(self.titles(), ["Cargo", "Help"])


class TestGroupOrder(EpaddBase):
    def setUp(self):
        super().setUp()
        FrameContext.page = _Page(ENGI, console="normal_engi")
        for name, group in (("a", "Systems"), ("b", "Mission"), ("c", "Ship")):
            route(name)
            gui_app_register(name, title=name.upper(), group=group,
                             consoles="engineering")

    def test_declared_order_wins_over_alphabetical(self):
        self.assertEqual([g for g, _ in gui_app_groups("engineering", ENGI)],
                         ["Ship", "Mission", "Systems"])
class TestOrdering(EpaddBase):
    def setUp(self):
        super().setUp()
        FrameContext.page = _Page(ENGI, console="normal_engi")
        for p in ("cargo", "upgrades", "quests", "debug", "mystery", "fabricate"):
            route(p)
        gui_app_register("quests", title="Quests", group="Mission", sort=10)
        gui_app_register("cargo", title="Cargo", group="Ship", sort=20)
        gui_app_register("fabricate", title="Fabricate", group="Ship", sort=10)
        gui_app_register("upgrades", title="Upgrades", group="Ship", sort=20)
        gui_app_register("debug", title="Debug", group="Systems", sort=10)
    def test_sort_orders_within_a_group_and_title_breaks_the_tie(self):
        ship = dict(gui_app_groups("engineering", ENGI))["Ship"]
        self.assertEqual([a["title"] for a in ship],
                         ["Fabricate", "Cargo", "Upgrades"])

    def test_an_empty_group_is_not_returned_at_all(self):
        """Helm registers no ship apps, so it draws no empty Ship heading."""
        gui_app_register("cargo", title="Cargo", group="Ship", consoles="engineering")
        gui_app_register("fabricate", title="Fabricate", group="Ship",
                         consoles="engineering")
        gui_app_register("upgrades", title="Upgrades", group="Ship",
                         consoles="engineering")
        gui_app_register("debug", title="Debug", group="Systems",
                         consoles="engineering")
        self.assertEqual([g for g, _ in gui_app_groups("helm", HELM)], ["Mission"])

    def test_a_title_defaults_to_the_tab_name(self):
        route("comms_log")
        gui_app_register("comms_log")
        self.assertIn("Comms Log", self.titles("engineering", ENGI))


if __name__ == "__main__":
    unittest.main()


class TestTheAwayConsoleOptsIn(EpaddBase):
    """`"*"` is every SHIP console. An away team is not everywhere on the ship, it is
    somewhere else entirely, and a landing party carrying the fabricator is not a
    scoping bug anybody notices until it is on screen."""

    def setUp(self):
        super().setUp()
        for p in ("cargo", "messages", "surveying"):
            GuiAppDecoratorLabel(p)
        gui_app_register("cargo", title="Cargo", consoles="engineering")
        gui_app_register("messages", title="Messages", away=True)
        gui_app_register("surveying", title="Surveying", consoles="away")

    def test_a_star_app_does_NOT_follow_the_team_down(self):
        self.assertNotIn("Cargo", self.titles("away"))

    def test_an_app_that_opts_in_does(self):
        self.assertIn("Messages", self.titles("away"))

    def test_and_still_shows_on_the_ship(self):
        self.assertIn("Messages", self.titles("helm"))

    def test_an_away_only_app_stays_off_the_bridge(self):
        self.assertIn("Surveying", self.titles("away"))
        self.assertNotIn("Surveying", self.titles("helm"))
        self.assertNotIn("Surveying", self.titles("engineering"))