"""Phase 3 — shots and cutscenes as data.

The phase adds no drawing: the furniture is existing overlay kinds and the camera
work is Phase 2's mover. What it contributes is SEQUENCING, so these tests are about
order, timing, skip and teardown - and they assert against the mock's `_cinematic`
state and the page's overlay slots, which are what the engine call actually sets.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from cosmos_dev.mock import sbs as mock_sbs
from sbs_utils.delete_queue import DeleteQueue
from sbs_utils.helpers import FrameContext, Context
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.procedural.space_objects import delete_object
from sbs_utils.tickdispatcher import TickDispatcher
from sbs_utils.gui import GuiClient
from sbs_utils.mast_sbs.maststorypage import StoryPage
from sbs_utils.procedural.gui.camera import camera_anchor, _MOVES
from sbs_utils.procedural.gui.cutscene import (
    cutscene_define, cutscene_play, cutscene_skip, cutscene_stop,
    cutscene_playing, cutscene_get, _CUTSCENES, _PLAYING)


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


C1 = 0x8000000000000001


class CutsceneBase(unittest.TestCase):
    def setUp(self):
        mock_sbs.create_new_sim()
        SpaceObject.clear()
        TickDispatcher.clear()
        mock_sbs._cinematic.clear()
        _MOVES.clear()
        _CUTSCENES.clear()
        _PLAYING.clear()
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent())
        # A page for the console, so overlays have somewhere to land.
        self.page = StoryPage()
        self.page.pending_gui = False
        self.page.client_id = C1
        self.page.gui_task = _FakeGuiTask(self.page)
        client = GuiClient(C1)
        client.page_stack.append(self.page)
        FrameContext.page = self.page

    def tearDown(self):
        TickDispatcher.clear()
        _MOVES.clear()
        _CUTSCENES.clear()
        _PLAYING.clear()
        DeleteQueue.clear()     # deferred deletes leak across modules; ids recycle
        FrameContext.page = None
        FrameContext.context = None

    def advance(self, seconds):
        from cosmos_dev.mock.sbs import TICKS_PER_SECOND
        for _ in range(int(seconds * TICKS_PER_SECOND) + 1):
            TickDispatcher.dispatch_tick()
            mock_sbs.sim._time_tick_counter += 1

    def dolly(self):
        state = mock_sbs._cinematic.get(C1)
        return None if state is None else state["dolly_id"]

    def slot_content(self, slot):
        region = self.page.overlays.slots.get(slot)
        return None if region is None else region.content


class TestSequencing(CutsceneBase):
    def test_the_first_shot_starts_immediately(self):
        # Not a tick later: a cutscene that begins on the next frame begins on the
        # OLD shot, which reads as a late cut.
        a = camera_anchor(0, 0, 0)
        cutscene_play([{"subject": a, "eye": (0, 100, -900), "seconds": 3}], to=C1)
        self.assertEqual(self.dolly(), a)

    def test_shots_run_in_order(self):
        a = camera_anchor(0, 0, 0)
        b = camera_anchor(5000, 0, 0)
        cutscene_play([
            {"subject": a, "eye": (0, 0, -900), "seconds": 2},
            {"subject": b, "eye": (5000, 0, -900), "seconds": 2},
        ], to=C1)
        self.assertEqual(self.dolly(), a)
        self.advance(2.5)
        self.assertEqual(self.dolly(), b)

    def test_it_resolves_when_the_last_shot_ends(self):
        a = camera_anchor(0, 0, 0)
        prom = cutscene_play([{"subject": a, "eye": (0, 0, -900), "seconds": 2}],
                             to=C1)
        self.advance(1.0)
        self.assertFalse(prom.done())
        self.advance(2.0)
        self.assertTrue(prom.done())
        self.assertFalse(prom.result()["skipped"])

    def test_a_move_shot_drives_the_lens(self):
        a = camera_anchor(0, 0, 0)
        cutscene_play([{"subject": a, "move": [(0, 0, -4000), (0, 0, -500)],
                        "seconds": 3, "ease": "linear"}], to=C1)
        first = mock_sbs._cinematic[C1]["dolly_off"][2]
        self.advance(1.5)
        mid = mock_sbs._cinematic[C1]["dolly_off"][2]
        self.assertGreater(mid, first, "the lens did not travel")

    def test_a_named_cutscene_can_be_replayed(self):
        a = camera_anchor(0, 0, 0)
        cutscene_define("intro", [{"subject": a, "eye": (0, 0, -900), "seconds": 1}])
        self.assertIsNotNone(cutscene_get("intro"))
        for _ in range(2):
            prom = cutscene_play("intro", to=C1)
            self.advance(2.0)
            self.assertTrue(prom.done())

    def test_an_unknown_name_resolves_rather_than_hanging(self):
        prom = cutscene_play("no-such-scene", to=C1)
        self.advance(1.0)
        self.assertTrue(prom.done(), "a typo must not hang the story forever")

    def test_no_audience_resolves(self):
        a = camera_anchor(0, 0, 0)
        prom = cutscene_play([{"subject": a, "eye": (0, 0, -1), "seconds": 1}], to=[])
        self.assertTrue(prom.done())


class TestFurniture(CutsceneBase):
    def test_the_letterbox_is_up_during_and_gone_after(self):
        a = camera_anchor(0, 0, 0)
        cutscene_play([{"subject": a, "eye": (0, 0, -900), "seconds": 2}], to=C1)
        self.assertIsNotNone(self.slot_content("fullscreen"))
        self.advance(3.0)
        self.assertIsNone(self.slot_content("fullscreen"))

    def test_letterbox_can_be_turned_off(self):
        a = camera_anchor(0, 0, 0)
        cutscene_play([{"subject": a, "eye": (0, 0, -900), "seconds": 1}],
                      to=C1, letterbox=False)
        self.assertIsNone(self.slot_content("fullscreen"))

    def test_a_shot_can_carry_an_overlay(self):
        a = camera_anchor(0, 0, 0)
        cutscene_play([{
            "subject": a, "eye": (0, 0, -900), "seconds": 2,
            "overlay": {"kind": "lower_third", "name": "Phoenix", "line": "Standing by."},
        }], to=C1)
        content = self.slot_content("lower_third")
        self.assertIsNotNone(content)
        self.assertEqual(content.get("name"), "Phoenix")

    def test_teardown_clears_only_what_the_cutscene_put_up(self):
        # It remembers the slots it used, so it cannot wipe furniture a console had
        # of its own.
        from sbs_utils.procedural.gui.overlay import overlay_toast
        a = camera_anchor(0, 0, 0)
        overlay_toast("mine", to=C1)
        cutscene_play([{
            "subject": a, "eye": (0, 0, -900), "seconds": 1,
            "overlay": {"kind": "lower_third", "name": "P", "line": "x"},
        }], to=C1)
        self.advance(2.0)
        self.assertIsNone(self.slot_content("lower_third"))
        self.assertIsNotNone(self.slot_content("corner_toast"),
                             "it cleared a slot that was not its own")


class TestSkip(CutsceneBase):
    def test_skip_ends_it_and_says_so(self):
        a = camera_anchor(0, 0, 0)
        prom = cutscene_play([{"subject": a, "eye": (0, 0, -900), "seconds": 30}],
                             to=C1)
        self.advance(0.5)
        self.assertEqual(cutscene_skip(C1), 1)
        self.assertTrue(prom.done())
        self.assertTrue(prom.result()["skipped"])

    def test_skip_tears_the_furniture_down_too(self):
        a = camera_anchor(0, 0, 0)
        cutscene_play([{
            "subject": a, "eye": (0, 0, -900), "seconds": 30,
            "overlay": {"kind": "lower_third", "name": "P", "line": "x"},
        }], to=C1)
        cutscene_skip(C1)
        self.assertIsNone(self.slot_content("lower_third"))
        self.assertIsNone(self.slot_content("fullscreen"))

    def test_an_unskippable_cutscene_ignores_it(self):
        a = camera_anchor(0, 0, 0)
        prom = cutscene_play([{"subject": a, "eye": (0, 0, -900), "seconds": 10}],
                             to=C1, skippable=False)
        self.assertEqual(cutscene_skip(C1), 0)
        self.assertFalse(prom.done())

    def test_stop_overrides_unskippable(self):
        # The teardown path - a mission ending must not be blocked by a scene that
        # declared itself unskippable to the crew.
        a = camera_anchor(0, 0, 0)
        prom = cutscene_play([{"subject": a, "eye": (0, 0, -900), "seconds": 10}],
                             to=C1, skippable=False)
        self.assertEqual(cutscene_stop(C1), 1)
        self.assertTrue(prom.done())

    def test_skipping_nothing_is_harmless(self):
        self.assertEqual(cutscene_skip(C1), 0)
        self.assertFalse(cutscene_playing(C1))


class TestRecovery(CutsceneBase):
    def test_a_dead_subject_ends_that_shot_early(self):
        # Engine-observed: a deleted dolly drops the view to the engine default, so
        # holding out the remaining seconds would sit on a frame already thrown away.
        a = camera_anchor(0, 0, 0)
        b = camera_anchor(5000, 0, 0)
        cutscene_play([
            {"subject": a, "move": [(0, 0, -3000), (0, 0, -500)], "seconds": 30},
            {"subject": b, "eye": (5000, 0, -900), "seconds": 5},
        ], to=C1)
        self.advance(1.0)
        self.assertEqual(self.dolly(), a)
        delete_object(a)
        self.advance(1.0)
        self.assertEqual(self.dolly(), b, "it did not move on from the dead shot")

    def test_a_second_cutscene_replaces_the_first(self):
        a = camera_anchor(0, 0, 0)
        b = camera_anchor(5000, 0, 0)
        first = cutscene_play([{"subject": a, "eye": (0, 0, -900), "seconds": 30}],
                              to=C1)
        second = cutscene_play([{"subject": b, "eye": (5000, 0, -900), "seconds": 2}],
                               to=C1)
        self.assertTrue(first.done(), "the first must not keep driving")
        self.assertEqual(self.dolly(), b)
        self.advance(3.0)
        self.assertTrue(second.done())

    def test_it_leaves_nothing_behind(self):
        a = camera_anchor(0, 0, 0)
        cutscene_play([{"subject": a, "eye": (0, 0, -900), "seconds": 1}], to=C1)
        self.advance(2.0)
        self.assertEqual(len(_PLAYING), 0)
        self.assertEqual(len(_MOVES), 0)
        self.assertFalse(cutscene_playing(C1))

    def test_the_camera_is_released_at_the_end(self):
        # Before the caller deletes its scene, not after.
        a = camera_anchor(0, 0, 0)
        cutscene_play([{"subject": a, "eye": (0, 0, -900), "seconds": 1}], to=C1)
        self.advance(2.0)
        self.assertEqual(mock_sbs._cinematic[C1]["script"], 0)

    def test_release_can_be_declined(self):
        a = camera_anchor(0, 0, 0)
        cutscene_play([{"subject": a, "eye": (0, 0, -900), "seconds": 1}],
                      to=C1, release=False)
        self.advance(2.0)
        self.assertEqual(mock_sbs._cinematic[C1]["script"], 1)


class TestResetLedger(CutsceneBase):
    def test_both_containers_are_registered_and_cleared(self):
        from sbs_utils.handlerhooks import _RESET_PROBES, reset_mission_audit
        self.assertIn("cutscenes", _RESET_PROBES)
        self.assertIn("cutscenes playing", _RESET_PROBES)
        a = camera_anchor(0, 0, 0)
        cutscene_define("x", [{"subject": a, "eye": (0, 0, -1), "seconds": 9}])
        cutscene_play("x", to=C1)
        audit = reset_mission_audit()
        self.assertEqual(audit.get("cutscenes"), 1)
        self.assertEqual(audit.get("cutscenes playing"), 1)


if __name__ == "__main__":
    unittest.main()
