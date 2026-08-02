"""Phase 4 — the rundown and the director punch.

A rundown is not a cutscene: a cutscene plays itself, a rundown is a set of
*available* shots a person chooses between live. So these tests are about the desk
— program vs preview, take, tally — and about the one rule that keeps a rundown
honest: **suggest never punches.**
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from cosmos_dev.mock import sbs as mock_sbs
from sbs_utils.delete_queue import DeleteQueue
from sbs_utils.helpers import FrameContext, Context
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.tickdispatcher import TickDispatcher
from sbs_utils.gui import GuiClient
from sbs_utils.mast_sbs.maststorypage import StoryPage
from sbs_utils.procedural.query import to_object
from sbs_utils.procedural.gui.camera import camera_anchor, _MOVES
from sbs_utils.procedural.gui.rundown import (
    rundown_add, rundown_remove, rundown_clear, rundown_shots, rundown_get,
    rundown_program, rundown_preview, rundown_live, rundown_staged,
    rundown_punch, rundown_stage, rundown_take, rundown_release,
    rundown_excitement, rundown_suggest, rundown_tiles, _SHOTS, _DESK)


class FakeEvent:
    client_id = 0
    tag = ""
    sub_tag = ""
    origin_id = 0
    selected_id = 0
    parent_id = 0
    value_tag = ""
    extra_tag = ""
    extra_extra_tag = ""
    sub_float = 0.0
    source_point = None
    event_time = 0


class _FakeMain:
    def __init__(self, page):
        self.page = page


class _FakeGuiTask:
    def __init__(self, page):
        self.main = _FakeMain(page)
        self.vars = {}

    def set_variable(self, name, value):
        self.vars[name] = value

    def get_variable(self, name, default=None):
        return self.vars.get(name, default)

    def compile_and_format_string(self, s):
        return s

    def format_string(self, s):
        return s


PGM = 0x8000000000000001      # program
PVW = 0x8000000000000002      # preview (the director's own console)


class RundownBase(unittest.TestCase):
    def setUp(self):
        mock_sbs.create_new_sim()
        SpaceObject.clear()
        TickDispatcher.clear()
        mock_sbs._cinematic.clear()
        _MOVES.clear()
        rundown_clear()
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent())
        self.pages = {}
        for cid in (PGM, PVW):
            page = StoryPage()
            page.pending_gui = False
            page.client_id = cid
            page.gui_task = _FakeGuiTask(page)
            client = GuiClient(cid)
            client.page_stack.append(page)
            self.pages[cid] = page
        FrameContext.page = self.pages[PGM]
        rundown_program(PGM)
        rundown_preview(PVW)

    def tearDown(self):
        TickDispatcher.clear()
        _MOVES.clear()
        rundown_clear()
        DeleteQueue.clear()
        FrameContext.page = None
        FrameContext.context = None

    def dolly(self, cid):
        state = mock_sbs._cinematic.get(cid)
        return None if state is None else state["dolly_id"]

    def excite(self, obj_id, value):
        to_object(obj_id).data_set.set("exciting", value)


class TestTheDesk(RundownBase):
    def test_punch_puts_a_shot_on_program(self):
        a = camera_anchor(0, 0, 0)
        rundown_add("wide", a, lens=(0, 4000, -9000))
        self.assertTrue(rundown_punch("wide"))
        self.assertEqual(self.dolly(PGM), a)

    def test_the_tally_says_what_is_live(self):
        # Without it a punch is ambiguous the moment two shots look alike.
        a = camera_anchor(0, 0, 0)
        b = camera_anchor(5000, 0, 0)
        rundown_add("wide", a, lens=(0, 4000, -9000))
        rundown_add("hero", b, lens=(5000, 120, -420))
        self.assertIsNone(rundown_live())
        rundown_punch("hero")
        self.assertEqual(rundown_live(), "hero")

    def test_staging_does_not_touch_program(self):
        a = camera_anchor(0, 0, 0)
        b = camera_anchor(5000, 0, 0)
        rundown_add("wide", a, lens=(0, 4000, -9000))
        rundown_add("hero", b, lens=(5000, 120, -420))
        rundown_punch("wide")
        rundown_stage("hero")
        self.assertEqual(rundown_staged(), "hero")
        self.assertEqual(self.dolly(PGM), a, "staging leaked onto the live feed")
        self.assertEqual(self.dolly(PVW), b, "preview did not show the staged shot")

    def test_take_promotes_preview_to_program(self):
        a = camera_anchor(0, 0, 0)
        b = camera_anchor(5000, 0, 0)
        rundown_add("wide", a, lens=(0, 4000, -9000))
        rundown_add("hero", b, lens=(5000, 120, -420))
        rundown_punch("wide")
        rundown_stage("hero")
        self.assertEqual(rundown_take(), "hero")
        self.assertEqual(self.dolly(PGM), b)
        self.assertEqual(rundown_live(), "hero")

    def test_take_with_nothing_staged_is_a_no_op(self):
        self.assertIsNone(rundown_take())

    def test_punching_an_unknown_shot_changes_nothing(self):
        a = camera_anchor(0, 0, 0)
        rundown_add("wide", a, lens=(0, 4000, -9000))
        rundown_punch("wide")
        self.assertFalse(rundown_punch("typo"))
        self.assertEqual(rundown_live(), "wide", "a typo took the feed down")

    def test_with_no_program_desk_a_punch_declines(self):
        rundown_clear()
        a = camera_anchor(0, 0, 0)
        rundown_add("wide", a, lens=(0, 0, -900))
        self.assertFalse(rundown_punch("wide"))


class TestFurniture(RundownBase):
    def test_a_punch_clears_the_previous_shots_furniture(self):
        # Otherwise the last shot's lower third sits over the new one.
        a = camera_anchor(0, 0, 0)
        b = camera_anchor(5000, 0, 0)
        rundown_add("one", a, lens=(0, 0, -900),
                    overlay={"kind": "lower_third", "name": "A", "line": "x"})
        rundown_add("two", b, lens=(5000, 0, -900))
        rundown_punch("one")
        self.assertIsNotNone(self.pages[PGM].overlays.slots["lower_third"].content)
        rundown_punch("two")
        self.assertIsNone(self.pages[PGM].overlays.slots["lower_third"].content)

    def test_preview_shows_framing_not_furniture(self):
        # A director already knows what the tile says; duplicating the lower third
        # onto their screen tells them nothing and hides the framing.
        a = camera_anchor(0, 0, 0)
        rundown_add("one", a, lens=(0, 0, -900),
                    overlay={"kind": "lower_third", "name": "A", "line": "x"})
        rundown_stage("one")
        region = self.pages[PVW].overlays.slots.get("lower_third")
        self.assertTrue(region is None or region.content is None)
        self.assertEqual(self.dolly(PVW), a)

    def test_release_hands_program_back_and_clears_the_tally(self):
        a = camera_anchor(0, 0, 0)
        rundown_add("one", a, lens=(0, 0, -900),
                    overlay={"kind": "lower_third", "name": "A", "line": "x"})
        rundown_punch("one")
        rundown_release()
        self.assertEqual(mock_sbs._cinematic[PGM]["script"], 0)
        self.assertIsNone(rundown_live())
        self.assertIsNone(self.pages[PGM].overlays.slots["lower_third"].content)


class TestSuggest(RundownBase):
    """Director assist, never autopilot."""

    def test_it_ranks_by_the_engines_own_excitement(self):
        a = camera_anchor(0, 0, 0)
        b = camera_anchor(5000, 0, 0)
        rundown_add("wide", a, lens=(0, 4000, -9000))
        rundown_add("hero", b, lens=(5000, 120, -420))
        self.excite(b, 500)
        self.assertEqual(rundown_suggest(), "hero")
        self.excite(a, 900)
        self.assertEqual(rundown_suggest(), "wide")

    def test_it_does_not_suggest_what_is_already_live(self):
        a = camera_anchor(0, 0, 0)
        b = camera_anchor(5000, 0, 0)
        rundown_add("wide", a, lens=(0, 0, -900))
        rundown_add("hero", b, lens=(5000, 0, -900))
        self.excite(a, 900)
        self.excite(b, 100)
        rundown_punch("wide")
        self.assertEqual(rundown_suggest(), "hero",
                         "it suggested the shot already on air")

    def test_suggesting_never_punches(self):
        # The whole point of a rundown is that a person chooses.
        a = camera_anchor(0, 0, 0)
        rundown_add("wide", a, lens=(0, 0, -900))
        self.excite(a, 900)
        self.assertEqual(rundown_suggest(), "wide")
        self.assertIsNone(rundown_live(), "suggest took the feed by itself")

    def test_nothing_exciting_means_no_suggestion(self):
        a = camera_anchor(0, 0, 0)
        rundown_add("wide", a, lens=(0, 0, -900))
        self.assertIsNone(rundown_suggest())

    def test_a_dead_subject_scores_zero_rather_than_raising(self):
        from sbs_utils.procedural.space_objects import delete_object
        a = camera_anchor(0, 0, 0)
        rundown_add("wide", a, lens=(0, 0, -900))
        self.excite(a, 900)
        delete_object(a)
        self.assertEqual(rundown_excitement("wide"), 0.0)


class TestTiles(RundownBase):
    def test_tiles_carry_what_a_console_needs(self):
        a = camera_anchor(0, 0, 0)
        b = camera_anchor(5000, 0, 0)
        rundown_add("wide", a, lens=(0, 0, -900), label="Wide - station")
        rundown_add("hero", b, lens=(5000, 0, -900))
        self.excite(b, 400)
        rundown_punch("wide")
        rundown_stage("hero")
        tiles = {t["name"]: t for t in rundown_tiles()}
        self.assertEqual(tiles["wide"]["label"], "Wide - station")
        self.assertTrue(tiles["wide"]["live"])
        self.assertTrue(tiles["hero"]["staged"])
        self.assertTrue(tiles["hero"]["suggested"])
        self.assertEqual(tiles["hero"]["excitement"], 400)

    def test_tiles_keep_rundown_order(self):
        a = camera_anchor(0, 0, 0)
        for name in ("one", "two", "three"):
            rundown_add(name, a, lens=(0, 0, -900))
        self.assertEqual([t["name"] for t in rundown_tiles()],
                         ["one", "two", "three"])

    def test_a_label_defaults_to_the_name(self):
        a = camera_anchor(0, 0, 0)
        rundown_add("wide", a, lens=(0, 0, -900))
        self.assertEqual(rundown_tiles()[0]["label"], "wide")


class TestBookkeeping(RundownBase):
    def test_removing_the_live_shot_clears_the_tally_but_not_the_feed(self):
        # Pulling a shot out of a list is not a directing decision.
        a = camera_anchor(0, 0, 0)
        rundown_add("wide", a, lens=(0, 0, -900))
        rundown_punch("wide")
        rundown_remove("wide")
        self.assertIsNone(rundown_live())
        self.assertEqual(self.dolly(PGM), a, "removing a shot cut the feed")

    def test_add_replaces_by_name(self):
        a = camera_anchor(0, 0, 0)
        b = camera_anchor(5000, 0, 0)
        rundown_add("wide", a, lens=(0, 0, -900))
        rundown_add("wide", b, lens=(5000, 0, -900))
        self.assertEqual(len(rundown_shots()), 1)
        self.assertEqual(rundown_get("wide")["subject"], b)

    def test_it_is_registered_and_cleared_on_reset(self):
        from sbs_utils.handlerhooks import _RESET_PROBES, reset_mission_audit
        self.assertIn("rundown shots", _RESET_PROBES)
        a = camera_anchor(0, 0, 0)
        rundown_add("wide", a, lens=(0, 0, -900))
        self.assertEqual(reset_mission_audit().get("rundown shots"), 1)
        rundown_clear()
        self.assertNotIn("rundown shots", reset_mission_audit())

    def test_clear_empties_the_desks_too(self):
        # A stale program audience would aim the next mission's punches at dead
        # client ids - the reused-interpreter trap.
        a = camera_anchor(0, 0, 0)
        rundown_add("wide", a, lens=(0, 0, -900))
        rundown_punch("wide")
        rundown_clear()
        self.assertIsNone(_DESK["program"])
        self.assertIsNone(_DESK["live"])
        self.assertEqual(len(_SHOTS), 0)


if __name__ == "__main__":
    unittest.main()
