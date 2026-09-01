"""The ePADD app registry: scoping, ordering, adoption, and staying off by default.

Two properties matter more than the rest and each has a test that fails loudly:

- **Off by default.** A mission that never calls `gui_app_mode()` must be untouched.
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
from sbs_utils.mast_sbs.story_nodes.gui_tab_decorator_label import GuiTabDecoratorLabel
from sbs_utils.procedural.gui.epadd import (
    gui_app_register, gui_app_unregister, gui_app_is_registered, gui_app_list,
    gui_app_groups, gui_app_mode, gui_app_mode_is_on, gui_app_adopt_record,
    gui_app_adopted, epadd_console_name)

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
    return GuiTabDecoratorLabel(path, if_exp)


class EpaddBase(unittest.TestCase):
    def setUp(self):
        FrameContext.context = Context(_FakeSim(), sbs, FakeEvent(SERVER, "test"))
        FrameContext.page = None
        FrameContext.task = None
        # set_inventory_value on an id with no Agent is a SILENT no-op, so the clients
        # have to exist before anything can be stored against them.
        clear_shared()
        GuiTabDecoratorLabel.clear()
        for cid in (SERVER, ENGI, HELM):
            GuiClient(cid)

    def tearDown(self):
        FrameContext.page = None
        FrameContext.task = None
        FrameContext.context = None
        GuiTabDecoratorLabel.clear()

    def titles(self, console=None, client_id=None):
        return [a["title"] for a in gui_app_list(console, client_id)]


class TestMode(EpaddBase):
    def test_mode_is_OFF_until_asked(self):
        """The whole opt-in promise. Nothing else in this file matters if this fails."""
        self.assertFalse(gui_app_mode_is_on(ENGI))
        self.assertFalse(gui_app_mode_is_on(HELM))

    def test_mode_is_per_client(self):
        """One console can run ePADD while the bridge next to it runs the old strip."""
        FrameContext.page = _Page(ENGI)
        gui_app_mode()
        self.assertTrue(gui_app_mode_is_on(ENGI))
        self.assertFalse(gui_app_mode_is_on(HELM))

    def test_mode_can_be_turned_back_off(self):
        FrameContext.page = _Page(ENGI)
        gui_app_mode()
        gui_app_mode(False)
        self.assertFalse(gui_app_mode_is_on(ENGI))


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


class TestAdoption(EpaddBase):
    """Turning ePADD on must not hide anything."""

    def setUp(self):
        super().setUp()
        FrameContext.page = _Page(ENGI, console="normal_engi")
        route("cargo")
        route("mystery")            # some addon's tab, registered by nobody
        gui_app_register("cargo", title="Cargo", consoles="engineering", group="Ship")

    def test_an_unregistered_tab_is_adopted(self):
        gui_app_adopt_record({"cargo", "mystery"}, back_tab="engineering")
        self.assertIn("Mystery", self.titles("engineering", ENGI))

    def test_it_lands_in_Other(self):
        gui_app_adopt_record({"mystery"}, back_tab="engineering")
        groups = dict(gui_app_groups("engineering", ENGI))
        self.assertIn("Other", groups)
        self.assertEqual([a["title"] for a in groups["Other"]], ["Mystery"])
        self.assertTrue(groups["Other"][0]["adopted"])

    def test_a_registered_tab_is_not_adopted_twice(self):
        gui_app_adopt_record({"cargo", "mystery"}, back_tab="engineering")
        self.assertEqual(self.titles("engineering", ENGI).count("Cargo"), 1)

    def test_the_back_tab_is_not_an_app(self):
        """It is how you leave the PADD, not something to open inside it."""
        route("engineering")
        gui_app_adopt_record({"cargo", "engineering"}, back_tab="engineering")
        self.assertNotIn("engineering", gui_app_adopted(ENGI))

    def test_epadd_itself_is_never_an_app(self):
        route("epadd")
        gui_app_adopt_record({"epadd", "cargo"}, back_tab="engineering")
        self.assertNotIn("epadd", gui_app_adopted(ENGI))
        self.assertNotIn("Epadd", self.titles("engineering", ENGI))

    def test_an_adopted_tab_still_obeys_its_route_condition(self):
        route("devonly", if_exp="IS_DEV")
        gui_app_adopt_record({"devonly"}, back_tab="engineering")
        FrameContext.task = _FakeTask(answer=False)
        self.assertNotIn("Devonly", self.titles("engineering", ENGI))

    def test_adoption_is_per_client(self):
        """Engineering's enabled set is not Helm's."""
        gui_app_adopt_record({"mystery"}, back_tab="engineering")
        self.assertEqual(gui_app_adopted(HELM), set())

    def test_unregistering_falls_back_to_adoption_rather_than_vanishing(self):
        gui_app_adopt_record({"cargo"}, back_tab="engineering")
        gui_app_unregister("cargo")
        self.assertFalse(gui_app_is_registered("cargo"))
        self.assertIn("Cargo", self.titles("engineering", ENGI))


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

    def test_groups_come_out_in_declared_order_with_Other_last(self):
        gui_app_adopt_record({"mystery"}, back_tab="engineering")
        self.assertEqual([g for g, _ in gui_app_groups("engineering", ENGI)],
                         ["Ship", "Mission", "Systems", "Other"])

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
