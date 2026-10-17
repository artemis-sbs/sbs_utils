"""Prefabs by TYPE - the one create path AMD content goes through (procedural/prefab.py).

Drives REAL compiled MAST prefab labels through prefab_create / landmark_spawn: the
metadata type lookup, a MAST label overriding a library default, `Data:` arguments
reaching the prefab body, key-role idempotency, a prefab that awaits (pending, never
double-spawned), and creation with no task context (a tick callback).

Run: python -m unittest tests.test_prefab_resolve
"""
import types
import unittest
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # noqa: F401  import first to break a circular import
from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext
from sbs_utils.gui import GuiClient
from sbs_utils.mast.maststory import MastStory
from sbs_utils.mast.mast_globals import MastGlobals
from sbs_utils.mast_sbs.maststoryscheduler import StoryScheduler
from tests.reset_helper import reset_mock

for _m in ("spawn", "inventory", "query", "timers", "execution"):
    MastGlobals.import_python_module("sbs_utils.procedural." + _m)

from sbs_utils.procedural import prefab as P
from sbs_utils.procedural import amd_landmarks as L
from sbs_utils.procedural.amd_doc import amd_document, amd_section
from sbs_utils.procedural.amd import amd_parse_facts
from sbs_utils.procedural.inventory import get_inventory_value
from sbs_utils.procedural.query import to_id, to_object
from sbs_utils.procedural.roles import has_role
from sbs_utils.procedural.space_objects import delete_object


STORY = '''
->END

=== prefab_test_box
metadata: ``` yaml
type: prefab/test/box
display_text: Test Box
color: red
```
    obj = npc_spawn(START_X, START_Y, START_Z, NAME, "tsn", "starbase_1", "behav_station")
    set_inventory_value(obj, "color", color)
    yield result to_id(obj)

=== prefab_amb_one
metadata: ``` yaml
type: prefab/amb/one
```
    yield result 0

=== prefab_amb_two
metadata: ``` yaml
type: prefab/amb/two
```
    yield result 0

=== prefab_mission_station
metadata: ``` yaml
type: prefab/station
```
    obj = npc_spawn(START_X, START_Y, START_Z, NAME, "tsn, mission_station", "starbase_1", "behav_station")
    yield result to_id(obj)

=== prefab_slow
metadata: ``` yaml
type: prefab/test/slow
```
    await delay_app(5)
    obj = npc_spawn(0, 0, 0, "Slow", "tsn", "starbase_1", "behav_station")
    yield result to_id(obj)
'''


class PrefabResolveTests(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)     # incl. DeleteQueue: a deferred delete from the last test
                            # would otherwise land on this test's recycled id
        self.story = MastStory()
        errors = self.story.compile(STORY, "prefab_test", self.story)
        self.assertEqual(errors, [])
        FrameContext.mast = self.story
        self.sched = StoryScheduler(self.story)
        self.page = types.SimpleNamespace(story=self.story, gui_task=None)
        self.page.gui_task = self.sched.run(0, self.page, "main", None, None, True)
        self.server = GuiClient(0)
        self.server.page_stack.append(self.page)
        FrameContext.page = self.page

    def tearDown(self):
        FrameContext.task = None
        FrameContext.page = None
        FrameContext.mast = None
        reset_mock(sbs)

    # -- resolution ---------------------------------------------------------------

    def test_type_exact_prefix_and_name(self):
        self.assertEqual(P.prefab_resolve("test/box").name, "prefab_test_box")
        self.assertEqual(P.prefab_resolve("prefab/test/box").name, "prefab_test_box")
        self.assertEqual(P.prefab_resolve("prefab_test_box").type, "test/box")
        # `test/slow` and `test/box` are both under test/, so `test` alone is ambiguous
        self.assertIsNone(P.prefab_resolve("test"))
        self.assertIsNone(P.prefab_resolve("amb"))
        self.assertEqual(P.prefab_resolve("amb/one").name, "prefab_amb_one")

    def test_exact_default_beats_a_mast_prefix(self):
        # `test/box` and `test/slow` are MAST prefabs under `test/`; a default named
        # exactly `test` must still win, as the library's `npc` does in LM.
        P.prefab_register("test", lambda d: None)
        try:
            self.assertTrue(P.prefab_resolve("test").is_default)
        finally:
            P._DEFAULTS.pop("test", None)

    def test_unknown_is_none_not_a_guess(self):
        self.assertIsNone(P.prefab_resolve("test/bxo"))

    def test_mast_label_overrides_default(self):
        self.assertFalse(P.prefab_resolve("station").is_default)
        self.assertTrue(P.prefab_resolve("derelict").is_default)

    def test_args_are_the_metadata(self):
        args = P.prefab_args("test/box")
        self.assertEqual(args.get("color"), "red")
        self.assertNotIn("type", args)
        self.assertIn("art", P.prefab_args("derelict"))

    def test_catalog_lists_both(self):
        types_ = [r.type for r in P.prefab_catalog()]
        self.assertIn("test/box", types_)
        self.assertIn("derelict", types_)
        self.assertEqual(types_.count("station"), 1)   # the MAST one, not both

    # -- arguments ----------------------------------------------------------------

    def test_data_normalizes_and_drops_reserved(self):
        d = P.prefab_data({"Fleet Difficulty": 4, "range": 9, "self": 1, "Color": "blue"},
                          aliases={"color": "tint"})
        self.assertEqual(d, {"fleet_difficulty": 4, "tint": "blue"})

    def test_argument_overrides_metadata_default(self):
        r = P.prefab_create("test/box", {"NAME": "B", "color": "blue"})
        self.assertEqual(get_inventory_value(to_id(r), "color"), "blue")
        r2 = P.prefab_create("test/box", {"NAME": "C"})
        self.assertEqual(get_inventory_value(to_id(r2), "color"), "red")

    # -- identity -----------------------------------------------------------------

    def test_keyed_create_is_idempotent_and_recreates(self):
        a = P.prefab_create("test/box", {"NAME": "A"}, family="t", key="a")
        b = P.prefab_create("test/box", {"NAME": "A"}, family="t", key="a")
        self.assertEqual(to_id(a), to_id(b))
        self.assertTrue(has_role(to_id(a), P.prefab_key_role("t", "a")))
        delete_object(to_id(a))
        c = P.prefab_create("test/box", {"NAME": "A"}, family="t", key="a")
        self.assertNotEqual(to_id(c), to_id(a))

    def test_awaiting_prefab_is_pending_not_doubled(self):
        t1 = P.prefab_create("test/slow", {}, family="t", key="slow")
        t2 = P.prefab_create("test/slow", {}, family="t", key="slow")
        self.assertIs(t1, t2)
        self.assertFalse(t1.done())
        self.assertEqual(P.prefab_pending_count(), 1)

    def test_no_task_context_uses_the_server_task(self):
        FrameContext.task = None
        FrameContext.page = None     # a tick callback: no page either
        r = P.prefab_create("test/box", {"NAME": "Tick"})
        self.assertIsNotNone(to_object(to_id(r)))

    # -- landmarks through it ------------------------------------------------------

    def _section(self, body):
        doc = amd_document("# [Root](root)\n## [Landmarks](landmarks)\n" + body,
                           data_parser=lambda t: amd_parse_facts(t, L.amd_landmark_facts()))
        return amd_section(doc, "landmarks")

    def test_landmark_data_block_reaches_the_prefab(self):
        sec = self._section("### [Kessel](kessel)\n---\nPrefab: test/box\nLoc: 100, 0, 200\n"
                            "Data:\n  Color: green\n---\n")
        objs = L.landmarks_spawn(sec)
        self.assertEqual(len(objs), 1)
        o = to_object(to_id(objs[0]))
        self.assertEqual(o.name, "Kessel")
        self.assertAlmostEqual(o.pos.x, 100, delta=1)
        self.assertEqual(get_inventory_value(o.id, "color"), "green")
        self.assertIsNotNone(L.landmark_object("kessel"))

    def test_landmark_default_and_override(self):
        sec = self._section(
            "### [Hulk](hulk)\n---\nPrefab: derelict\nArt: wreck\n---\n"
            "### [Base](base)\n---\nPrefab: station\n---\n"
            "### [Zone](zone)\n---\nPrefab: point\nLoc: 5, 0, 5\n---\n"
            "### [Nothing](nothing)\n---\nSide: tsn\n---\n")
        objs = L.landmarks_spawn(sec)
        self.assertEqual(len(objs), 2)            # point and the prefab-less record place nothing
        base = L.landmark_object("base")
        self.assertTrue(has_role(base.id, "mission_station"))   # the MAST prefab won

    def test_nothing_placed_reaches_the_runtime_log(self):
        # A wreck with no Art: places nothing. The author reads mast.runtime.log, not the
        # console, so the warning must land there (course c5-05: it only reached stderr).
        sec = self._section("### [The Tern](the_tern)\n---\nPrefab: wreck\n---\n"
                            "### [Ghost](ghost)\n---\nPrefab: no_such_prefab_xyz\n---\n")
        with self.assertLogs("mast.runtime", level="WARNING") as cm:
            self.assertEqual(L.landmarks_spawn(sec), [])
        text = "\n".join(cm.output)
        self.assertIn("the_tern", text)
        self.assertIn("needs Art:", text)
        self.assertIn("no_such_prefab_xyz", text)

    # -- the other families --------------------------------------------------------

    def test_inline_spec_shapes(self):
        self.assertEqual(P.amd_prefab_spec("fleet/raider x2")["count"], 2)
        self.assertEqual(P.amd_prefab_spec("torgoth 3")["words"], ["3"])
        nested = P.amd_prefab_spec({"Prefab": "Fleet/Raider", "Count": 2,
                                    "Data": {"Race": "torgoth"}})
        self.assertEqual((nested["prefab"], nested["count"], nested["args"]),
                         ("fleet/raider", 2, {"Race": "torgoth"}))
        self.assertIsNone(P.amd_prefab_spec(""))

    def test_relic_spawn_phrase_reads_old_and_new(self):
        from sbs_utils.procedural.amd_relics import _relic_spawn_spec
        old = _relic_spawn_spec("ximni x2")         # the `x` in ximni is not a count
        self.assertEqual((old["prefab"], old["count"], old["args"]),
                         ("npc/ship", 2, {"side_value": "ximni"}))
        self.assertEqual(_relic_spawn_spec("skaraan 4")["count"], 4)
        new = _relic_spawn_spec("test/box x3")
        self.assertEqual((new["prefab"], new["count"]), ("test/box", 3))

    def test_pickup_prefab_makes_the_body_and_it_is_still_an_item(self):
        from sbs_utils.procedural.items import item_spawn
        from sbs_utils.mast.core_nodes.label import Label
        lbl = Label("prefab_item_widget")
        lbl.apply_metadata({"type": "item/misc", "key": "widget", "pickup": "test/box"})
        self.story.labels["prefab_item_widget"] = lbl
        obj = item_spawn("widget", 10, 0, 10)
        self.assertEqual(get_inventory_value(obj.id, "item_key"), "widget")
        self.assertEqual(get_inventory_value(obj.id, "color"), "red")   # test/box made it

    def test_theater_names_its_fleet_prefab(self):
        from sbs_utils.procedural import amd_theater as T
        T.theater_declare_text("# [Test](t)\n---\nFactions: kralien\n"
                               "Fleets: kralien=test/box\n---\n")
        self.assertEqual(T.theater_fleet_prefab("kralien", key="t").name, "prefab_test_box")
        # no entry for the race, and no LM prefab_fleet_raider in this story
        self.assertIsNone(T.theater_fleet_prefab("arvonian", key="t"))

    def test_a_side_naming_a_landmark_prefab_is_still_a_side(self):
        from sbs_utils.procedural.amd_sides import sides_declare
        from sbs_utils.mast.mast_node import MastDataObject
        rec = MastDataObject({"key": "cutter", "name": "Breaker Cutter", "prefab": "ship",
                              "args": {}, "leans": {}})
        ids = sides_declare([rec])
        self.assertTrue(ids.get("cutter"))          # declared as amd/side, not spawned

    def test_overlay_card_and_old_kind(self):
        from sbs_utils.procedural.amd_overlay import amd_overlays, overlay_amd_clear
        overlay_amd_clear()
        recs = amd_overlays({"children": [
            {"key": "a", "display_text": "A", "data": {"card": "toast"}, "description": "x"},
            {"key": "b", "display_text": "B", "data": {"kind": "lower_third"}, "description": "y"}]})
        self.assertEqual((recs["a"]["kind"], recs["b"]["kind"]), ("toast", "lower_third"))
        self.assertNotIn("card", recs["a"]["fields"])
        overlay_amd_clear()

    def test_wall_pieces_come_from_the_walls_prefab(self):
        from unittest import mock
        from sbs_utils.procedural import volume_dress as VD
        made = []

        def one_piece(volume, **kw):
            made.append(VD._piece_spawn(5, 0, 5, "", "#,relic_wall", "wreck", "behav_asteroid"))
            return 1
        with mock.patch.object(VD, "_volume_dress", one_piece):
            VD.volume_dress(None, prefab={"prefab": "test/box", "count": 1,
                                          "args": {"Color": "blue"}})
            VD.volume_dress(None)                       # no prefab: plain terrain_spawn
        self.assertEqual(get_inventory_value(to_id(made[0]), "color"), "blue")
        self.assertIsNone(get_inventory_value(to_id(made[1]), "color", None))
        self.assertIsNone(VD._PIECE[0])                 # put back after the build

    def test_cast_record_names_its_prefab(self):
        from sbs_utils.procedural.amd_lifeforms import lifeform_from_record
        from sbs_utils.mast.mast_node import MastDataObject
        rec = MastDataObject({"key": "doc", "name": "Doc", "face": None, "roles": "crew",
                              "color": "green", "prefab": None, "args": {}})
        doc = lifeform_from_record(rec)
        self.assertEqual(doc.name, "Doc")                       # amd/lifeform default
        self.assertIs(lifeform_from_record(rec), doc)           # still keyed


if __name__ == "__main__":
    unittest.main()
