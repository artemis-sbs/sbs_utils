"""Declarative cutscenes and rundowns — a shot is a RECORD.

One heading per shot, grouped by ``Scene:`` or ``Rundown:``, which is what makes a
rundown shot and a cutscene shot the same thing and lets both phases share one
loader. The hard part is that a shot names a LIVE object and no object exists when
the ``.amd`` loads, so ``Subject:`` resolves late: cast first, then a role, and a
shot that resolves to neither is dropped with a reason NAMING it.
"""
import unittest
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs as mock_sbs
from sbs_utils.delete_queue import DeleteQueue
from sbs_utils.helpers import FrameContext, Context
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.tickdispatcher import TickDispatcher
from sbs_utils.gui import GuiClient
from sbs_utils.mast_sbs.maststorypage import StoryPage
from sbs_utils.procedural.amd_doc import amd_document, amd_root_node
from sbs_utils.procedural.gui.camera import camera_anchor, _MOVES
from sbs_utils.procedural.gui.cutscene import _CUTSCENES, _PLAYING, cutscene_get
from sbs_utils.procedural.gui.rundown import rundown_clear, rundown_shots, rundown_get
from sbs_utils.procedural.amd_cutscene import (
    amd_cutscenes, cutscene_amd, rundown_amd, cutscene_cast, amd_cutscene_clear,
    CUTSCENE_AMD, RUNDOWN_AMD, _vec, _move)


DOC = (
    # A wrapper root, because amd_records() yields a node's CHILDREN - so the bed
    # has to be a record alongside its shots, not the document root itself.
    "# [Cinematics](cine)\n"
    "## [Chapter One](intro)\n"
    "---\n"
    "Kind: cutscene\n"
    "Letterbox: yes\n"
    "Skippable: no\n"
    "---\n"
    "## [Establish Phoenix](intro_1)\n"
    "---\n"
    "Scene: intro\n"
    "Subject: station\n"
    "Eye: 0, 900, -4000\n"
    "Seconds: 4\n"
    "Overlay: lower_third\n"
    "Name: Phoenix Control\n"
    "---\n"
    "All quiet on the belt.\n"
    "## [Push in on Artemis](intro_2)\n"
    "---\n"
    "Scene: intro\n"
    "Subject: hero\n"
    "Move: 0,400,-3000 -> 0,120,-600\n"
    "Seconds: 6\n"
    "Ease: linear\n"
    "---\n"
    "## [Wide of the belt](pat_1)\n"
    "---\n"
    "Rundown: patrol\n"
    "Subject: station\n"
    "Eye: 0, 4000, -9000\n"
    "Label: Wide - belt\n"
    "---\n"
    "## [On the hero](pat_2)\n"
    "---\n"
    "Rundown: patrol\n"
    "Subject: hero\n"
    "Eye: 0, 120, -420\n"
    "---\n"
)


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


class AmdCutsceneBase(unittest.TestCase):
    def setUp(self):
        mock_sbs.create_new_sim()
        SpaceObject.clear()
        TickDispatcher.clear()
        mock_sbs._cinematic.clear()
        _MOVES.clear()
        _CUTSCENES.clear()
        _PLAYING.clear()
        rundown_clear()
        amd_cutscene_clear()
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent())
        self.page = StoryPage()
        self.page.pending_gui = False
        self.page.client_id = C1
        self.page.gui_task = _FakeGuiTask(self.page)
        client = GuiClient(C1)
        client.page_stack.append(self.page)
        FrameContext.page = self.page
        self.doc = amd_document(DOC)

    def tearDown(self):
        TickDispatcher.clear()
        _MOVES.clear()
        _CUTSCENES.clear()
        _PLAYING.clear()
        rundown_clear()
        amd_cutscene_clear()
        DeleteQueue.clear()
        FrameContext.page = None
        FrameContext.context = None

    def load(self):
        # amd_records() yields a node's CHILDREN, so the root is the section
        # here and every heading under it is a record.
        return amd_cutscenes(amd_root_node(self.doc))

    def advance(self, seconds):
        from cosmos_dev.mock.sbs import TICKS_PER_SECOND
        for _ in range(int(seconds * TICKS_PER_SECOND) + 1):
            TickDispatcher.dispatch_tick()
            mock_sbs.sim._time_tick_counter += 1


class TestParsing(unittest.TestCase):
    def test_a_vector_parses(self):
        self.assertEqual(_vec("0, 900, -4000"), (0.0, 900.0, -4000.0))
        self.assertEqual(_vec("1;2;3"), (1.0, 2.0, 3.0))

    def test_a_bad_vector_is_none_not_an_exception(self):
        # A typo in a fence must not take the mission down at load.
        self.assertIsNone(_vec("0, 900"))
        self.assertIsNone(_vec("over there"))
        self.assertIsNone(_vec(None))

    def test_a_move_parses_both_arrows(self):
        self.assertEqual(_move("0,0,-3000 -> 0,0,-600"),
                         [(0.0, 0.0, -3000.0), (0.0, 0.0, -600.0)])
        self.assertEqual(_move("0,0,-3000 to 0,0,-600"),
                         [(0.0, 0.0, -3000.0), (0.0, 0.0, -600.0)])

    def test_a_half_written_move_is_none(self):
        self.assertIsNone(_move("0,0,-3000 ->"))
        self.assertIsNone(_move("0,0,-3000"))


class TestLoading(AmdCutsceneBase):
    def test_shots_group_into_their_scene(self):
        self.load()
        self.assertIn("intro", CUTSCENE_AMD)
        self.assertEqual(len(CUTSCENE_AMD["intro"]["shots"]), 2)

    def test_shots_group_into_their_rundown(self):
        self.load()
        self.assertIn("patrol", RUNDOWN_AMD)
        self.assertEqual(len(RUNDOWN_AMD["patrol"]), 2)

    def test_the_bed_comes_from_the_cutscene_record(self):
        self.load()
        bed = CUTSCENE_AMD["intro"]["bed"]
        self.assertTrue(bed["letterbox"])
        self.assertFalse(bed["skippable"])

    def test_document_order_is_the_shot_order(self):
        self.load()
        self.assertEqual([s["key"] for s in CUTSCENE_AMD["intro"]["shots"]],
                         ["intro_1", "intro_2"])

    def test_an_explicit_order_wins(self):
        doc = amd_document(
            "# [S](s)\n"
            "## [B](b)\n---\nScene: s\nSubject: x\nEye: 0,0,-1\nOrder: 1\n---\n"
            "## [A](a)\n---\nScene: s\nSubject: x\nEye: 0,0,-1\nOrder: 0\n---\n")
        amd_cutscenes(amd_root_node(doc))
        self.assertEqual([s["key"] for s in CUTSCENE_AMD["s"]["shots"]], ["a", "b"])

    def test_a_shots_overlay_fields_ride_beside_it(self):
        self.load()
        shot = CUTSCENE_AMD["intro"]["shots"][0]
        self.assertEqual(shot["overlay"]["kind"], "lower_third")
        self.assertEqual(shot["overlay"]["name"], "Phoenix Control")
        # the body is the kind's PRIMARY field, exactly as in amd_overlay
        self.assertEqual(shot["overlay"]["line"], "All quiet on the belt.")

    def test_geometry_is_parsed_at_load(self):
        self.load()
        a, b = CUTSCENE_AMD["intro"]["shots"]
        self.assertEqual(a["eye"], (0.0, 900.0, -4000.0))
        self.assertEqual(b["move"][0], (0.0, 400.0, -3000.0))
        self.assertEqual(b["ease"], "linear")
        self.assertEqual(b["seconds"], 6)


class TestSubjectResolution(AmdCutsceneBase):
    """Cast first, then a role - the object does not exist when the .amd loads."""

    def test_a_cast_name_resolves(self):
        self.load()
        station = camera_anchor(0, 0, 0)
        hero = camera_anchor(5000, 0, 0)
        cutscene_cast("station", station)
        cutscene_cast("hero", hero)
        cutscene_amd("intro", to=C1)
        self.assertEqual(mock_sbs._cinematic[C1]["dolly_id"], station)

    def test_a_role_is_the_fallback(self):
        self.load()
        obj = SpaceObject.get(camera_anchor(0, 0, 0))
        obj.add_role("station")
        hero = camera_anchor(5000, 0, 0)
        cutscene_cast("hero", hero)
        cutscene_amd("intro", to=C1)
        self.assertEqual(mock_sbs._cinematic[C1]["dolly_id"], obj.id)

    def test_the_cast_wins_over_a_role(self):
        self.load()
        by_role = SpaceObject.get(camera_anchor(0, 0, 0))
        by_role.add_role("station")
        cast = camera_anchor(9000, 0, 0)
        cutscene_cast("station", cast)
        cutscene_cast("hero", camera_anchor(5000, 0, 0))
        cutscene_amd("intro", to=C1)
        self.assertEqual(mock_sbs._cinematic[C1]["dolly_id"], cast)

    def test_an_unresolvable_shot_is_dropped_not_fatal(self):
        # The rest of the scene still plays - a missing actor should not take the
        # whole cutscene down.
        self.load()
        cutscene_cast("hero", camera_anchor(5000, 0, 0))
        cutscene_amd("intro", to=C1)          # "station" is neither cast nor a role
        self.assertEqual(len(cutscene_get("intro")["shots"]), 1)

    def test_the_same_scene_replays_with_a_different_cast(self):
        # The point of a cast: the script says "hero", production decides who.
        self.load()
        cutscene_cast("station", camera_anchor(0, 0, 0))
        first = camera_anchor(5000, 0, 0)
        cutscene_cast("hero", first)
        cutscene_amd("intro", to=C1)
        self.assertEqual(cutscene_get("intro")["shots"][1]["subject"], first)
        second = camera_anchor(7000, 0, 0)
        cutscene_cast("hero", second)
        cutscene_amd("intro", to=C1)
        self.assertEqual(cutscene_get("intro")["shots"][1]["subject"], second)


class TestPlaying(AmdCutsceneBase):
    def test_it_plays_in_order_with_its_bed(self):
        self.load()
        station = camera_anchor(0, 0, 0)
        hero = camera_anchor(5000, 0, 0)
        cutscene_cast("station", station)
        cutscene_cast("hero", hero)
        prom = cutscene_amd("intro", to=C1)
        self.assertEqual(mock_sbs._cinematic[C1]["dolly_id"], station)
        self.assertIsNotNone(self.page.overlays.slots["fullscreen"].content)
        self.advance(4.5)
        self.assertEqual(mock_sbs._cinematic[C1]["dolly_id"], hero)
        self.advance(7.0)
        self.assertTrue(prom.done())

    def test_the_bed_can_be_overridden_per_play(self):
        self.load()
        cutscene_cast("station", camera_anchor(0, 0, 0))
        cutscene_cast("hero", camera_anchor(5000, 0, 0))
        cutscene_amd("intro", to=C1, letterbox=False)
        self.assertIsNone(self.page.overlays.slots.get("fullscreen").content
                          if self.page.overlays.slots.get("fullscreen") else None)

    def test_an_unknown_cutscene_returns_none(self):
        self.load()
        self.assertIsNone(cutscene_amd("no-such-scene", to=C1))


class TestRundownLoading(AmdCutsceneBase):
    def test_it_loads_declared_shots_into_the_rundown(self):
        self.load()
        cutscene_cast("station", camera_anchor(0, 0, 0))
        cutscene_cast("hero", camera_anchor(5000, 0, 0))
        self.assertEqual(rundown_amd("patrol"), 2)
        self.assertEqual(len(rundown_shots()), 2)

    def test_the_label_carries_through_for_the_director_tile(self):
        self.load()
        cutscene_cast("station", camera_anchor(0, 0, 0))
        cutscene_cast("hero", camera_anchor(5000, 0, 0))
        rundown_amd("patrol")
        self.assertIsNotNone(rundown_get("Wide - belt"))

    def test_an_unknown_rundown_loads_nothing(self):
        self.assertEqual(rundown_amd("nope"), 0)


class TestResetLedger(AmdCutsceneBase):
    def test_everything_is_registered_and_clearable(self):
        from sbs_utils.handlerhooks import _RESET_PROBES, reset_mission_audit
        for name in ("amd cutscenes", "amd rundowns", "cutscene cast"):
            self.assertIn(name, _RESET_PROBES)
        self.load()
        cutscene_cast("station", camera_anchor(0, 0, 0))
        audit = reset_mission_audit()
        self.assertEqual(audit.get("amd cutscenes"), 1)
        self.assertEqual(audit.get("amd rundowns"), 1)
        self.assertEqual(audit.get("cutscene cast"), 1)
        amd_cutscene_clear()
        audit = reset_mission_audit()
        self.assertNotIn("amd cutscenes", audit)
        self.assertNotIn("cutscene cast", audit)


if __name__ == "__main__":
    unittest.main()
