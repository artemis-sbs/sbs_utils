"""Tests for procedural.amd_relics - relics authored as AMD instead of buried YAML.

Parses a real AMD document rather than hand-built dicts: the point of the feature is that
an author's text becomes a volume, so a test that skips the text tests nothing.
"""

import io
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.procedural.amd import amd_parse_facts
from sbs_utils.procedural.amd_doc import amd_document, amd_section
from sbs_utils.procedural.amd_relics import (
    relics_from_section, relics_register, relic_record, relic_keys, relic_pos,
    relic_volume, relics_clear, relics_count, amd_relic_data, amd_relic_facts,
    relics_load, relic_reload, relics_reload_all, relic_volume_name, relic_contain,
    relic_point, relic_points, relic_point_roles,
    relic_contents, relic_contents_arm, relic_contents_can_trigger,
    relic_contents_clear, relic_contents_state,
    relic_place, relic_release,
)
# The live half of these tests needs a sim: markers are real objects and `reach` is a
# real distance between them.
from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.delete_queue import DeleteQueue
from sbs_utils.procedural.roles import role
from sbs_utils.procedural.query import to_object_list, to_object
from sbs_utils.procedural.spawn import player_spawn
from sbs_utils.procedural.space_objects import set_pos


class FakeEvent:
    """The minimum an event needs to be: a client id and empty tags."""
    client_id = 0
    tag = ""
    sub_tag = ""
    value_tag = ""
    origin_id = 0
    selected_id = 0
    parent_id = 0
    sub_float = 0.0


from sbs_utils.procedural.volume import (
    volume_contains, volume_depth, volume_path, volume_get, volume_clear,
    volume_watching, volume_watch,
)

NL = chr(10)

DOC = """
# [Test Relics](testrelics)

## [Relics](relics)

### [The Ossuary](ossuary)
---
Loc: 10000, 0, -5000
Atmosphere: purple
Containment: tractor
Scrape band: 120
Margin: 60
Forbid jump: yes
---
An ancient thing, hollow, and not built by anyone still alive.

### [hub](hub)
---
Relic: ossuary
Chamber: 0, 0, 0, 900
---

### [gallery](gallery)
---
Relic: ossuary
Chamber: 3000, 0, 0, 700
Passage to: hub 300
---

### [shaft](shaft)
---
Relic: ossuary
Chamber: 0, 2200, 0, 600
Passage to: hub 240
---

### [the hall](hall)
---
Relic: ossuary
Box: 3600, 0, 2900, 900, 260, 380
---

### [the core](core)
---
Relic: ossuary
Solid: sphere, 0, 0, 0, 320
---
"""


def _doc(content):
    """Parse AMD with the relic fence handler wired in - the same shape
    test_amd_landmarks.py uses. Without the data_parser the fences stay unread."""
    return amd_document(content,
                        data_parser=lambda t: amd_parse_facts(t, amd_relic_facts()))


def _section(content=None):
    return amd_section(_doc(content or DOC), "relics")


class TestParsing(unittest.TestCase):
    def setUp(self):
        relics_clear()
        volume_clear()

    def test_one_relic_and_its_parts(self):
        relics = relics_from_section(_section())
        self.assertEqual(len(relics), 1)          # parts are NOT separate relics
        r = relics[0]
        self.assertEqual(r.get("key"), "ossuary")
        self.assertEqual(r.get("name"), "The Ossuary")

    def test_parts_are_sorted_into_their_kinds(self):
        r = relics_from_section(_section())[0]
        self.assertEqual(sorted(r.get("chambers")), ["gallery", "hub", "shaft"])
        self.assertEqual(sorted(r.get("boxes")), ["hall"])
        self.assertEqual(len(r.get("solids")), 1)
        self.assertEqual(len(r.get("passages")), 2)

    def test_relic_fields_are_read(self):
        r = relics_from_section(_section())[0]
        self.assertEqual(r.get("loc"), [10000.0, 0.0, -5000.0])
        self.assertEqual(r.get("atmosphere"), "purple")
        self.assertEqual(r.get("containment"), "tractor")
        self.assertEqual(r.get("margin"), 60)
        self.assertEqual(r.get("scrape_band"), 120)
        self.assertTrue(r.get("forbid_jump"))

    def test_prose_survives_as_the_description(self):
        # A relic is a place; its body text is the thing an author actually cares about.
        r = relics_from_section(_section())[0]
        self.assertIn("hollow", r.get("desc"))

    def test_passage_pairs(self):
        data = amd_relic_data("Relic: x\nPassage to: hub 300, gallery 240\n")
        self.assertEqual(data["passage_to"], [("hub", 300.0), ("gallery", 240.0)])

    def test_passage_without_a_radius_is_left_for_a_default(self):
        # Guessing a radius here would hide a missing number; None lets the caller decide.
        data = amd_relic_data("Relic: x\nPassage to: hub\n")
        self.assertEqual(data["passage_to"], [("hub", None)])

    def test_solid_keeps_its_kind_word(self):
        data = amd_relic_data("Relic: x\nSolid: capsule, 0, -100, 0, 0, 100, 0, 60\n")
        self.assertEqual(data["solid"][0], "capsule")
        self.assertEqual(data["solid"][1:], [0.0, -100.0, 0.0, 0.0, 100.0, 0.0, 60.0])

    def test_a_part_naming_no_relic_would_be_a_relic(self):
        # The bed/shot discriminator: `Relic:` is what makes a record a PART.
        relics = relics_from_section(_section("""
# [R](r)

## [Relics](relics)

### [lonely](lonely)
---
Chamber: 0, 0, 0, 100
---
"""))
        self.assertEqual(len(relics), 1)
        self.assertEqual(relics[0].get("key"), "lonely")
        self.assertEqual(relics[0].get("chambers"), {})

    def test_a_part_naming_an_unknown_relic_is_skipped_not_fatal(self):
        # Growth rule: a dangling reference is a lint finding, never a crash.
        relics = relics_from_section(_section("""
# [R](r)

## [Relics](relics)

### [a](a)
---
Loc: 0, 0, 0
---

### [b](b)
---
Relic: typo
Chamber: 0, 0, 0, 100
---
"""))
        self.assertEqual(len(relics), 1)
        self.assertEqual(relics[0].get("chambers"), {})


class TestBuildsAVolume(unittest.TestCase):
    """The whole point: authored text becomes a navigable volume."""

    def setUp(self):
        relics_clear()
        volume_clear()
        self.rec = relics_from_section(_section())[0]
        relic_volume(self.rec)

    def test_the_volume_exists_under_the_relic_key(self):
        self.assertIsNotNone(volume_get("ossuary"))

    def test_coordinates_are_relative_to_loc(self):
        # Authored at 0,0,0 but placed at 10000,0,-5000 - this is what lets one layout
        # be dropped twice.
        self.assertTrue(volume_contains("ossuary", (10000, 0, -5000 + 400)))
        self.assertFalse(volume_contains("ossuary", (0, 0, 400)))

    def test_passages_connect_the_chambers(self):
        self.assertTrue(volume_contains("ossuary", (10000 + 1500, 0, -5000)))
        self.assertTrue(volume_contains("ossuary", (10000, 1500, -5000)))

    def test_the_box_hall_is_navigable_including_a_corner(self):
        self.assertTrue(volume_contains("ossuary", (10000 + 3600, 0, -5000 + 2900)))
        self.assertTrue(volume_contains("ossuary", (10000 + 4400, 240, -5000 + 3200)))

    def test_the_subtracted_core_is_solid(self):
        self.assertFalse(volume_contains("ossuary", (10000, 0, -5000)))

    def test_the_navmesh_routes(self):
        self.assertEqual(volume_path("ossuary", "gallery", "shaft"),
                         ["gallery", "hub", "shaft"])

    def test_placed_twice_is_congruent(self):
        moved = relics_from_section(_section())[0]
        moved.loc = [0.0, 0.0, 0.0]
        relic_volume(moved, name="ossuary_at_origin")
        for p in ((0, 0, 400), (1500, 0, 0), (0, 1500, 0), (0, 0, 0)):
            here = volume_contains("ossuary_at_origin", p)
            there = volume_contains("ossuary", (p[0] + 10000, p[1], p[2] - 5000))
            self.assertEqual(here, there, f"{p}")


class TestRegistry(unittest.TestCase):
    def setUp(self):
        relics_clear()
        volume_clear()

    def test_register_remembers_without_building(self):
        # A story beat reveals a relic on cue; registering must not spawn a volume.
        relics_register(_section())
        self.assertEqual(relic_keys(), ["ossuary"])
        self.assertIsNotNone(relic_record("ossuary"))
        self.assertIsNone(volume_get("ossuary"))

    def test_pos_defaults_to_the_origin(self):
        rec = relics_from_section(_section())[0]
        rec.loc = None
        self.assertEqual(relic_pos(rec), [0.0, 0.0, 0.0])

    def test_clear_empties_the_registry(self):
        relics_register(_section())
        self.assertEqual(relics_count(), 1)
        relics_clear()
        self.assertEqual(relics_count(), 0)


class TestReloadFromFile(unittest.TestCase):
    """A relic can be rebuilt from the file it came from - the live-preview contract.

    Until this existed, nothing in the library remembered a relic's SOURCE, so a reload
    had to be written per mission: the mission held the file path in a constant, tore its
    own relic down and rebuilt it. That is ~35 lines of teardown per relic mission, and it
    is exactly where `sim.delete_object` (a method that does not exist) and the identity
    guards bit. The editor's Preview button can only ring a doorbell over the debug
    channel; the rebuild has to happen inside the running mission, so it belongs here.
    """

    def setUp(self):
        relics_clear()
        volume_clear()
        import tempfile, os
        fd, self.path = tempfile.mkstemp(suffix=".amd")
        os.close(fd)
        self._write(DOC)

    def tearDown(self):
        import os
        relics_clear()
        volume_clear()
        try:
            os.remove(self.path)
        except OSError:
            pass

    def _write(self, text):
        with io.open(self.path, "w", encoding="utf-8") as f:
            f.write(text)

    def test_a_loaded_record_remembers_where_it_came_from(self):
        relics_load(self.path)
        rec = relic_record("ossuary")
        self.assertEqual(rec.get("source"), self.path)
        self.assertEqual(rec.get("section"), "relics")

    def test_a_record_remembers_which_volume_it_built(self):
        relics_load(self.path)
        rec = relic_record("ossuary")
        self.assertIsNone(rec.get("volume"), "nothing is built until relic_volume runs")
        relic_volume(rec, name="relic")
        self.assertEqual(rec.get("volume"), "relic")
        self.assertEqual(relic_volume_name(rec), "relic")

    def test_reload_picks_up_an_edit_to_the_file(self):
        relics_load(self.path)
        relic_volume(relic_record("ossuary"))
        self.assertEqual(volume_get("ossuary").chambers["hub"][3], 900.0)
        self._write(DOC.replace("Chamber: 0, 0, 0, 900", "Chamber: 0, 0, 0, 1450"))
        out = relic_reload("ossuary")
        self.assertEqual(out["key"], "ossuary")
        self.assertEqual(volume_get("ossuary").chambers["hub"][3], 1450.0)

    def test_reload_rebuilds_under_the_MISSION_S_volume_name(self):
        # A mission may build a relic under a name of its own. A reload that used the
        # record's key instead would leave the live volume untouched and quietly build a
        # second one beside it - the relic would look frozen, not broken.
        relics_load(self.path)
        relic_volume(relic_record("ossuary"), name="relic")
        self._write(DOC.replace("Chamber: 0, 0, 0, 900", "Chamber: 0, 0, 0, 1450"))
        out = relic_reload("ossuary")
        self.assertEqual(out["volume"], "relic")
        self.assertIsNone(volume_get("ossuary"), "reload built a stray second volume")
        self.assertEqual(volume_get("relic").chambers["hub"][3], 1450.0)

    def _mock_sim(self):
        from cosmos_dev.mock import sbs
        from tests.reset_helper import reset_mock
        return reset_mock(sbs)

    def test_reload_re_applies_the_AUTHORED_containment(self):
        # volume_watch keys on the NAME, so an untouched watcher would go on enforcing the
        # old margin against the new geometry - and an edit to `Margin:` would do nothing.
        self._mock_sim()
        relics_load(self.path)
        rec = relic_record("ossuary")
        relic_volume(rec)
        relic_contain(rec)
        self.assertTrue(volume_watching("ossuary"))
        relic_reload("ossuary")
        self.assertTrue(volume_watching("ossuary"))

    def test_a_watcher_SURVIVES_a_rebuild_and_follows_the_new_geometry(self):
        """Measured, not assumed - and it is why reload never unwatches.

        A watcher is keyed by volume NAME and re-resolves the volume every tick, so a
        rebuild slides the new geometry underneath it with margin, hold and block_jump
        intact. Tearing it down and re-arming would drop the tractor and fire a spurious
        `volume_recovered` at every ship inside the relic.
        """
        from sbs_utils.procedural.volume import _WATCHERS, volume_depth
        self._mock_sim()
        relics_load(self.path)
        relic_volume(relic_record("ossuary"))
        volume_watch("ossuary", margin=60, block_jump=True)
        before = _WATCHERS.get("ossuary")
        self._write(DOC.replace("Chamber: 0, 0, 0, 900", "Chamber: 0, 0, 0, 4000"))
        relic_reload("ossuary")
        after = _WATCHERS.get("ossuary")
        self.assertIs(before, after, "the rebuild replaced the watcher")
        self.assertEqual(after.margin, 60.0)
        self.assertLess(volume_depth("ossuary", (10000, 0, -5000 + 3000)), 0,
                        "the surviving watcher is judging the OLD geometry")

    def test_editing_the_authored_margin_goes_LIVE(self):
        """The whole promise of authoring containment declaratively.

        `Margin:` is as much part of the relic as a chamber radius, so an edit to it must
        take effect on the same Preview - otherwise half the file is live and half needs
        a restart, with nothing saying which half.
        """
        from sbs_utils.procedural.volume import _WATCHERS
        self._mock_sim()
        relics_load(self.path)
        rec = relic_record("ossuary")
        relic_volume(rec)
        relic_contain(rec)
        self.assertEqual(_WATCHERS["ossuary"].margin, 60.0)
        self._write(DOC.replace("Margin: 60", "Margin: 250"))
        relic_reload("ossuary")
        self.assertEqual(_WATCHERS["ossuary"].margin, 250.0)

    def test_a_HAND_TUNED_watch_is_left_alone(self):
        # The mission said margin=200 in its own code. Re-applying the authored fields
        # over that would be the library quietly winning an argument the author did not
        # know they were having.
        self._mock_sim()
        relics_load(self.path)
        relic_volume(relic_record("ossuary"))
        volume_watch("ossuary", margin=200.0)
        relic_reload("ossuary")
        from sbs_utils.procedural.volume import _WATCHERS
        self.assertEqual(_WATCHERS["ossuary"].margin, 200.0)

    def test_an_unwatched_relic_is_not_watched_BY_a_reload(self):
        # Preview rebuilds geometry; it does not decide that a relic should start holding
        # ships in. That is the mission's call and it may not have made it yet.
        self._mock_sim()
        relics_load(self.path)
        relic_volume(relic_record("ossuary"))
        relic_reload("ossuary")
        self.assertFalse(volume_watching("ossuary"))

    def test_a_relic_built_in_CODE_has_nothing_to_reload(self):
        doc = amd_document(DOC, data_parser=lambda t: amd_parse_facts(t, amd_relic_facts()))
        relics_register(amd_section(doc, "relics"))       # no source
        self.assertIsNone(relic_reload("ossuary"))
        self.assertEqual(relics_reload_all(), [])

    def test_reload_all_covers_every_relic_read_from_a_file(self):
        relics_load(self.path)
        relic_volume(relic_record("ossuary"))
        out = relics_reload_all()
        self.assertEqual([o["key"] for o in out], ["ossuary"])
        self.assertEqual(out[0]["chambers"], len(volume_get("ossuary").chambers))

    def test_an_unknown_key_reloads_nothing(self):
        relics_load(self.path)
        self.assertIsNone(relic_reload("no_such_relic"))

    def test_a_rebuild_needs_NO_mission_route(self):
        """The whole point of moving this into the library.

        A mission that authored a relic in AMD and wrote nothing else gets its geometry
        rebuilt: the file is re-read, the volume replaced. `relic_rebuilt` is emitted for
        a mission that wants to re-scatter its props, and NOTHING listening to it is a
        perfectly good outcome - the walls simply stay as they were.
        """
        from sbs_utils.mast.mast import Mast
        from sbs_utils.helpers import FrameContext

        class _RecordingMast(Mast):
            def __init__(self):
                super().__init__()
                self.delivered = []

            def signal_emit(self, name, sender_task, data):
                self.delivered.append((name, data))
                return super().signal_emit(name, sender_task, data)

        mast = _RecordingMast()
        self.assertEqual(mast.compile('logger(var="out")\n', "no_relic_route", mast), [])
        relics_load(self.path)
        relic_volume(relic_record("ossuary"))
        self._write(DOC.replace("Chamber: 0, 0, 0, 900", "Chamber: 0, 0, 0, 1450"))
        FrameContext.mast = mast
        try:
            out = relic_reload("ossuary")
        finally:
            FrameContext.mast = None
        self.assertEqual(volume_get("ossuary").chambers["hub"][3], 1450.0)
        self.assertEqual([n for n, _ in mast.delivered], ["relic_rebuilt"])
        self.assertEqual(mast.delivered[0][1]["volume"], "ossuary")
        self.assertEqual(out["chambers"], len(volume_get("ossuary").chambers))

    def test_a_rebuild_with_no_MAST_context_still_rebuilds(self):
        # A probe, a unit test, a bare tick loop. `signal_emit` no-ops without a context
        # by design, so the geometry half must not depend on one.
        from sbs_utils.helpers import FrameContext
        FrameContext.mast = None
        relics_load(self.path)
        relic_volume(relic_record("ossuary"))
        self._write(DOC.replace("Chamber: 0, 0, 0, 900", "Chamber: 0, 0, 0, 1450"))
        self.assertIsNotNone(relic_reload("ossuary"))
        self.assertEqual(volume_get("ossuary").chambers["hub"][3], 1450.0)


class TestPoints(unittest.TestCase):
    """`Point:` - a named place inside a relic, for an item, a spawn, or the way in.

    It is a part like any other, so it lives in the file with the geometry it belongs to,
    is authored RELATIVE to the relic's `Loc:`, and is drawn by the editor. That relative
    coordinate is the whole argument for it: a landmark is the existing named-place
    concept, but a landmark's `Loc:` is absolute, so moving a relic would leave its cache,
    its entrance and its ambush behind.

    A point adds no navigable space and subtracts none. What it is FOR is `Roles:`, which
    only the mission interprets.
    """

    DOC = NL.join([
        "# [Doc](doc)", "",
        "## [Relics](relics)", "",
        "### [The Ossuary](ossuary)", "---", "Loc: 10000, 0, -5000", "---", "",
        "### [hub](hub)", "---", "Relic: ossuary", "Chamber: 0, 0, 0, 900", "---", "",
        "### [the cache](cache)", "---", "Relic: ossuary",
        "Point: 120, 0, -300", "Roles: item, quest", "---", "",
        "### [the mouth](mouth)", "---", "Relic: ossuary",
        "Point: -900, 0, 0", "Roles: entrance", "---", "",
        "### [unmarked](plain_point)", "---", "Relic: ossuary", "Point: 5, 6, 7", "---",
    ])

    def setUp(self):
        relics_clear()
        volume_clear()
        doc = amd_document(self.DOC,
                           data_parser=lambda t: amd_parse_facts(t, amd_relic_facts()))
        relics_register(amd_section(doc, "relics"))

    def tearDown(self):
        relics_clear()
        volume_clear()

    def test_a_point_resolves_to_a_world_position(self):
        self.assertEqual(relic_point("ossuary", "cache"), (10120.0, 0.0, -5300.0))

    def test_it_moves_with_the_relic(self):
        # The reason a point is a relic part and not a landmark.
        rec = relic_record("ossuary")
        setattr(rec, "loc", [0.0, 0.0, 0.0])
        self.assertEqual(relic_point("ossuary", "cache"), (120.0, 0.0, -300.0))

    def test_every_point_at_once(self):
        pts = relic_points("ossuary")
        self.assertEqual(sorted(pts), ["cache", "mouth", "plain_point"])

    def test_narrowing_by_role(self):
        self.assertEqual(list(relic_points("ossuary", "entrance")), ["mouth"])
        self.assertEqual(list(relic_points("ossuary", "item")), ["cache"])
        self.assertEqual(relic_points("ossuary", "nosuchrole"), {})

    def test_roles_are_matched_lowercased(self):
        self.assertEqual(list(relic_points("ossuary", "ENTRANCE")), ["mouth"])

    def test_a_point_needs_no_roles(self):
        self.assertEqual(relic_point_roles("ossuary", "plain_point"), [])
        self.assertIn("plain_point", relic_points("ossuary"))

    def test_a_point_is_not_geometry(self):
        # It must not add navigable space, or an author would be building rooms by
        # accident every time they marked a spot.
        relic_volume(relic_record("ossuary"))
        v = volume_get("ossuary")
        self.assertEqual(len(v.chambers), 1)
        self.assertEqual((len(v.boxes), len(v.solids), len(v.passages)), (0, 0, 0))

    def test_an_unknown_name_or_relic_is_None_not_an_error(self):
        self.assertIsNone(relic_point("ossuary", "nope"))
        self.assertIsNone(relic_point("no_such_relic", "cache"))
        self.assertEqual(relic_points("no_such_relic"), {})

    def _relic_findings(self, text):
        # Through `amd_lint`, the way the linter is actually run - it builds the typed
        # document itself, which is what the rules read.
        from sbs_utils.procedural.amd_lint import amd_lint
        return [f for f in amd_lint(content=text) if str(f.code).startswith("relic-")]

    def test_lint_catches_a_short_point(self):
        bad = self.DOC.replace("Point: 120, 0, -300", "Point: 120, 0")
        self.assertIn("relic-short-point", [f.code for f in self._relic_findings(bad)])

    def test_a_good_point_lints_clean(self):
        self.assertEqual([f.code for f in self._relic_findings(self.DOC)], [])


class TestSchemaIsRegistered(unittest.TestCase):
    """R0 rides on this: the linter and the LSP both read the schema, so registering it
    is what gives an author completion, hover and diagnostics for free."""

    def test_section_names_resolve(self):
        from sbs_utils.procedural.amd_schema import archetype_for_section
        for name in ("Relics", "Relic", "Ruins", "Interiors"):
            self.assertEqual(archetype_for_section(name), "relic", name)

    def test_fields_are_declared(self):
        from sbs_utils.procedural.amd_schema import amd_is_declared
        for label in ("Chamber", "Passage to", "Box", "Solid", "Loc", "Atmosphere",
                      "Containment", "Margin", "Scrape band", "Forbid jump", "Relic"):
            self.assertTrue(amd_is_declared(label, "relic", None), label)

    def test_an_unknown_field_is_not_declared(self):
        from sbs_utils.procedural.amd_schema import amd_is_declared
        self.assertFalse(amd_is_declared("Vestibule", "relic", None))

    def test_containment_is_an_enum_the_editor_can_offer(self):
        from sbs_utils.procedural.amd_schema import enum_values
        self.assertEqual(sorted(enum_values("Containment", "relic")),
                         ["clamp", "none", "tractor"])

    def test_kind_is_not_used(self):
        # `Kind:` infers LANDMARK - the trap that already cost the cutscene design a
        # redesign. Relics must be named by their section, never by Kind:.
        from sbs_utils.procedural.amd_schema import record_schema
        self.assertNotIn("kind", record_schema("relic").get("fields", {}))


class TestLint(unittest.TestCase):
    """Relic-specific findings. Everything a relic gets WRONG is silent at runtime -
    a dropped part or an unbuilt corridor reads as a pathfinding bug, not a typo."""

    BAD = """
# [R](r)

## [Relics](relics)

### [The Ossuary](ossuary)
---
Loc: 0, 0, 0
---

### [hub](hub)
---
Relic: ossuary
Chamber: 0, 0, 0, 0
---

### [gallery](gallery)
---
Relic: ossuary
Chamber: 3000, 0, 0
Passage to: hubb 300
---

### [orphan](orphan)
---
Relic: nosuchrelic
Chamber: 0, 0, 0, 100
---
"""

    def _relic_findings(self, text):
        from sbs_utils.procedural.amd_lint import amd_lint
        return [f for f in amd_lint(content=text) if str(f.code).startswith("relic-")]

    def test_a_good_relic_is_clean(self):
        self.assertEqual(self._relic_findings(DOC), [])

    def test_every_fault_is_caught_once(self):
        codes = sorted(f.code for f in self._relic_findings(self.BAD))
        self.assertEqual(codes, ["relic-bad-radius", "relic-dangling-parent",
                                 "relic-dangling-passage", "relic-short-part"])

    def test_findings_point_at_the_offending_line(self):
        for f in self._relic_findings(self.BAD):
            self.assertGreater(f.line, 0)

    def test_relic_faults_are_warnings_not_errors(self):
        # Structural problems are ERRORs; a relic fault still loads, so it must not
        # hard-fail a build.
        for f in self._relic_findings(self.BAD):
            self.assertEqual(f.severity, "warning", f.code)


if __name__ == "__main__":
    unittest.main()


CONTENTS_DOC = """
# [Contents Test](contentstest)

## [Relics](relics)

### [The Ossuary](ossuary)
---
Loc: 1000, 0, 2000
---

### [vault](vault)
---
Relic: ossuary
Chamber: 400, 0, 0, 300
---

### [the reliquary](cache)
---
Relic: ossuary
Point: 400, 0, 0
Item: red_beacon
Qty: 2
Starts when: reach vault_door 900
---

### [the vault door](vaultmark)
---
Relic: ossuary
Point: 100, 0, 0
Roles: vault_door
---

### [the shaft floor](floor)
---
Relic: ossuary
Point: 0, -200, 0
Item: power_cell
---

### [the ambush](ambush)
---
Relic: ossuary
Point: 0, 0, 500
Spawn: raider x2
Starts when: signal woke_up
---
"""


class TestContentsParsing(unittest.TestCase):
    """The AMD side: what an author writes becomes content records on the relic."""

    def setUp(self):
        relics_clear()
        volume_clear()

    def _rec(self):
        relics_register(_section(CONTENTS_DOC))
        return relic_record("ossuary")

    def test_contents_hang_off_the_part_that_carries_them(self):
        self._rec()
        got = {c["part"]: c for c in relic_contents("ossuary")}
        self.assertEqual(sorted(got), ["ambush", "cache", "floor"])
        self.assertEqual(got["cache"]["item"], "red_beacon")
        self.assertEqual(got["cache"]["qty"], 2)
        self.assertEqual(got["ambush"]["spawn"], ["raider x2"])
        # A part with neither is not a content record at all.
        self.assertNotIn("vaultmark", got)

    def test_a_position_is_resolved_relative_to_the_relic(self):
        # The whole reason contents belong to the relic: move the ruin and its loot
        # moves with it. Loc is 1000, 0, 2000 and the point is 400, 0, 0.
        self._rec()
        got = {c["part"]: c for c in relic_contents("ossuary")}
        self.assertEqual(tuple(got["cache"]["pos"]), (1400.0, 0.0, 2000.0))

    def test_contents_may_hang_off_a_chamber_not_only_a_point(self):
        doc = CONTENTS_DOC.replace(
            "Chamber: 400, 0, 0, 300", "Chamber: 400, 0, 0, 300" + NL + "Item: torch")
        relics_register(_section(doc))
        got = {c["part"]: c for c in relic_contents("ossuary")}
        self.assertIn("vault", got)                       # a room, not a point
        self.assertEqual(tuple(got["vault"]["pos"]), (1400.0, 0.0, 2000.0))

    def test_a_trigger_is_stored_raw_and_absence_means_no_trigger(self):
        self._rec()
        got = {c["part"]: c for c in relic_contents("ossuary")}
        self.assertEqual(got["cache"]["starts_when"], "reach vault_door 900")
        self.assertIsNone(got["floor"]["starts_when"])


class TestTriggerVocabulary(unittest.TestCase):
    """What the watcher will and will not answer - the claim lint makes."""

    def test_the_phrases_a_relic_can_watch(self):
        for phrase in ("reach vault_door 900", "signal woke_up", "5 minutes"):
            self.assertTrue(relic_contents_can_trigger(phrase), phrase)

    def test_a_phrase_it_cannot_watch_is_reported_not_swallowed(self):
        # `accepted` is a QUEST concept - a thing sitting in a room is never accepted -
        # so it parses fine and would silently never fire. Lint refuses it.
        self.assertFalse(relic_contents_can_trigger("accepted"))
        self.assertFalse(relic_contents_can_trigger("destroy 6 raiders"))

    def test_no_phrase_at_all_is_fine(self):
        self.assertTrue(relic_contents_can_trigger(None))
        self.assertTrue(relic_contents_can_trigger(""))


class TestArming(unittest.TestCase):
    """Placement. The mock stands in for item_spawn/npc_spawn so the test is about WHEN
    a thing is placed, not about what the spawn call does."""

    def setUp(self):
        relics_clear()
        volume_clear()
        relic_contents_clear()
        self.placed = []
        self.marks = []
        import sbs_utils.procedural.amd_relics as R
        self.R = R
        self._place, self._marks = R._relic_place_contents, R._relic_place_role_markers
        R._relic_place_contents = lambda c: self.placed.append(c["part"])
        R._relic_place_role_markers = lambda rec, key, **kw: self.marks.append(key)
        R._ARM_TASK = None
        relics_register(_section(CONTENTS_DOC))

    def tearDown(self):
        self.R._relic_place_contents = self._place
        self.R._relic_place_role_markers = self._marks
        relic_contents_clear()

    def test_untriggered_contents_are_placed_at_once(self):
        # The common case - a ruin with things in it - and it needs no word in the file.
        waiting = relic_contents_arm("ossuary")
        self.assertEqual(self.placed, ["floor"])
        self.assertEqual(waiting, 2)

    def test_arming_twice_places_nothing_twice(self):
        # A live reload re-arms. Littering the ruin with a second beacon every time the
        # author saves is the failure this identity rule exists to prevent.
        relic_contents_arm("ossuary")
        relic_contents_arm("ossuary")
        self.assertEqual(self.placed, ["floor"])

    def test_a_signal_places_its_record_once_and_only_once(self):
        from sbs_utils.procedural.signal import signal_emit
        relic_contents_arm("ossuary")
        self.R._relic_contents_tick()
        self.assertNotIn("ambush", self.placed)      # nothing has happened yet
        signal_emit("woke_up")
        self.R._relic_contents_tick()
        self.assertIn("ambush", self.placed)
        self.R._relic_contents_tick()                # the signal is still remembered
        self.assertEqual(self.placed.count("ambush"), 1)

    def test_a_signal_between_two_ticks_is_not_missed(self):
        # Signals are observed, not polled. A signal emitted and gone inside one tick
        # interval would be invisible to a watcher that asked "is it firing now".
        from sbs_utils.procedural.signal import signal_emit
        relic_contents_arm("ossuary")
        signal_emit("woke_up")
        signal_emit("something_else")
        self.R._relic_contents_tick()
        self.assertIn("ambush", self.placed)

    def test_reach_places_nothing_until_a_player_is_inside_the_radius(self):
        relic_contents_arm("ossuary")
        rec = [v for k, v in self.R._ARMED.items()
               if not v.get("done") and v.get("content", {}).get("part") == "cache"][0]
        # No player and no marker: the trigger cannot fire, and must not.
        self.assertFalse(self.R._relic_trigger_fired(rec))


class TestContentsLint(unittest.TestCase):
    def _lint(self, content):
        # Lint reads the RAW document (amd_core.parse), not the fact-parsed one - it
        # reports line numbers, so it needs the text as written.
        from sbs_utils.procedural.amd_lint import amd_lint_relics
        from sbs_utils.procedural.amd_core import parse
        return amd_lint_relics(parse(content))

    def _look_doc(self, *lines):
        """A minimal relic whose fence carries whatever look fields are being tested."""
        head = ["# T", "", "## [Relics](relics)", "", "### [The Hole](hole)", "---"]
        return "\n".join(head + list(lines) + ["---", "A hole.", ""])

    def test_an_art_key_that_is_not_in_shipdata_is_flagged(self):
        # It does not fail at runtime - the engine renders the `unknown` question-mark
        # mesh - so a typo builds a ruin out of question marks and says nothing.
        doc = self._look_doc("Art: generic-rectangle, generic-nonsense")
        findings = {f.code: f.message for f in self._lint(doc)}
        self.assertIn("relic-unknown-art", findings)
        self.assertIn("generic-nonsense", findings["relic-unknown-art"])
        self.assertNotIn("generic-rectangle", findings["relic-unknown-art"],
                         "a key that IS in shipData must not be reported")

    def test_a_wall_style_nobody_defined_is_flagged(self):
        # Same shape of failure as a bad art key: it falls back to plain rock, so a
        # plated hall quietly is not one and nothing says why.
        codes = [f.code for f in self._lint(self._look_doc("Walls: plaits"))]
        self.assertIn("relic-unknown-walls", codes)

    def test_a_real_wall_style_is_quiet(self):
        doc = self._look_doc("Walls: plates") + "\n".join([
            "### [room](room)", "---", "Relic: hole", "Chamber: 0, 0, 0, 900",
            "Walls: ribs", "---", "A room.", ""])
        codes = [f.code for f in self._lint(doc)]
        self.assertNotIn("relic-unknown-walls", codes)

    def test_an_unwatchable_phrase_is_flagged_with_its_line(self):
        doc = CONTENTS_DOC.replace("Starts when: reach vault_door 900",
                                   "Starts when: accepted")
        codes = [f.code for f in self._lint(doc)]
        self.assertIn("relic-when-unwatchable", codes)

    def test_a_watchable_phrase_is_clean(self):
        codes = [f.code for f in self._lint(CONTENTS_DOC)]
        self.assertNotIn("relic-when-unwatchable", codes)

    def test_a_trigger_with_nothing_to_trigger_is_flagged(self):
        doc = CONTENTS_DOC.replace("Roles: vault_door",
                                   "Roles: vault_door" + NL + "Starts when: signal x")
        codes = [f.code for f in self._lint(doc)]
        self.assertIn("relic-when-without-contents", codes)


class TestContentsInTheWorld(unittest.TestCase):
    """The whole path with REAL objects: markers spawn, a ship flies in, the loot appears.

    The mocked TestArming above proves the WHEN; this proves the trigger can actually see
    the world - that `Roles:` on a point becomes something `reach` can measure against.
    That join is the piece an author never writes and would never think to check.
    """

    def setUp(self):
        sbs.create_new_sim()
        SpaceObject.clear()
        relics_clear()
        volume_clear()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        import sbs_utils.procedural.amd_relics as R
        self.R = R
        R._ARM_TASK = None
        # Item spawning is the items registry's job and is tested there. Here it only has
        # to record that something was placed AT ALL, and where.
        self.placed = []
        self._place = R._relic_place_contents
        R._relic_place_contents = lambda c: self.placed.append((c["part"], c["pos"]))
        relics_register(_section(CONTENTS_DOC))

    def tearDown(self):
        self.R._relic_place_contents = self._place
        relic_contents_clear()
        SpaceObject.clear()
        DeleteQueue.clear()
        FrameContext.context = None

    def test_a_point_with_roles_becomes_something_reach_can_measure(self):
        relic_contents_arm("ossuary")
        marks = to_object_list(role("vault_door"))
        self.assertEqual(len(marks), 1)
        # It stands where the author put it, in WORLD coordinates - Loc 1000,0,2000 plus
        # the point's 100,0,0. A marker at the relic's local origin would fire the
        # trigger in the wrong place, and nothing would look wrong until you flew there.
        self.assertAlmostEqual(marks[0].pos.x, 1100.0, places=3)
        self.assertAlmostEqual(marks[0].pos.z, 2000.0, places=3)

    def test_the_loot_appears_when_the_ship_arrives_and_not_before(self):
        relic_contents_arm("ossuary")
        ship = player_spawn(50000, 0, 50000, "Test", "tsn", "tsn_light_cruiser")
        self.placed.clear()
        self.R._relic_contents_tick()
        self.assertEqual(self.placed, [])              # 50,000u away: nothing

        # set_pos, not `.pos =`: on a mock playership the physics thread owns the
        # position and a bare attribute write does not survive to the next read.
        set_pos(ship.id, 1100.0 + 400.0, 0.0, 2000.0)  # 400u from the door, inside 900
        self.R._relic_contents_tick()
        self.assertEqual([p[0] for p in self.placed], ["cache"])
        # And it lands at the reliquary, not at the door that triggered it.
        self.assertAlmostEqual(self.placed[0][1][0], 1400.0, places=3)

        self.R._relic_contents_tick()                  # still inside the radius
        self.assertEqual(len(self.placed), 1)          # placed once, not every tick

    def test_arming_twice_leaves_one_marker_not_two(self):
        # A live reload re-arms. Two markers at the same spot is not a visible bug - the
        # relic looks right - it just leaks one object per save.
        relic_contents_arm("ossuary")
        relic_contents_arm("ossuary")
        self.assertEqual(len(to_object_list(role("vault_door"))), 1)


class TestPlaceAndRelease(unittest.TestCase):
    """Putting a relic somewhere the .amd could not know, and taking it away again.

    This is the galaxy case: an Open Universe cell has a transient world origin, is built
    on arrival and destroyed on departure, and the NEXT cell is already being built while
    the last one comes down. Whole-registry verbs are the wrong tools there.
    """

    def setUp(self):
        # A sim, because containment installs a real tick.
        sbs.create_new_sim()
        SpaceObject.clear()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        relics_clear()
        volume_clear()
        relics_register(_section(CONTENTS_DOC))

    def tearDown(self):
        relics_clear()
        volume_clear()
        SpaceObject.clear()
        DeleteQueue.clear()
        FrameContext.context = None

    def test_placing_moves_the_geometry(self):
        rec = relic_record("ossuary")
        relic_place(rec, 500000.0, 0.0, -250000.0)
        vol = relic_volume(rec)
        # The vault is authored at 400, 0, 0 with radius 300 - so it is navigable around
        # the NEW origin and nowhere near the authored one.
        self.assertTrue(volume_contains(vol, (500400.0, 0.0, -250000.0)))
        self.assertFalse(volume_contains(vol, (1400.0, 0.0, 2000.0)))

    def test_placing_moves_the_points_and_the_contents_with_it(self):
        # The whole reason this is one verb rather than a translated volume: a relic
        # placed by its geometry alone would leave its loot and its markers behind.
        relic_place("ossuary", 500000.0, 0.0, -250000.0)
        self.assertEqual(relic_point("ossuary", "cache"), (500400.0, 0.0, -250000.0))
        got = {c["part"]: c for c in relic_contents("ossuary")}
        self.assertEqual(tuple(got["cache"]["pos"]), (500400.0, 0.0, -250000.0))

    def test_placing_takes_a_key_as_well_as_a_record(self):
        self.assertIsNotNone(relic_place("ossuary", 1.0, 2.0, 3.0))
        self.assertIsNone(relic_place("no_such_relic", 1.0, 2.0, 3.0))

    def test_releasing_drops_the_volume_but_keeps_the_record(self):
        rec = relic_record("ossuary")
        relic_volume(rec)
        self.assertIsNotNone(volume_get("ossuary"))
        self.assertTrue(relic_release("ossuary"))
        self.assertIsNone(volume_get("ossuary"))
        # The mission still knows about this relic and will rebuild it on the next visit.
        self.assertIsNotNone(relic_record("ossuary"))
        self.assertFalse(relic_release("ossuary"))     # idempotent

    def test_releasing_one_relic_leaves_the_other_standing(self):
        # The failure this verb exists to prevent: tearing down a departed system taking
        # the relic the crew is currently inside.
        other = relics_register(_section(CONTENTS_DOC.replace("ossuary", "second")))
        relic_volume(relic_record("ossuary"))
        relic_volume(relic_record("second"))
        relic_release("ossuary")
        self.assertIsNone(volume_get("ossuary"))
        self.assertIsNotNone(volume_get("second"))
        self.assertEqual(len(other), 1)

    def test_releasing_forgets_only_that_relic_s_armed_contents(self):
        relics_register(_section(CONTENTS_DOC.replace("ossuary", "second")))
        import sbs_utils.procedural.amd_relics as R
        placed, marks = [], []
        keep_place, keep_marks = R._relic_place_contents, R._relic_place_role_markers
        R._relic_place_contents = lambda c: placed.append(c["part"])
        R._relic_place_role_markers = lambda rec, key, **kw: marks.append(key)
        R._ARM_TASK = None
        try:
            relic_contents_arm("ossuary")
            relic_contents_arm("second")
            self.assertEqual(relic_contents_state("ossuary", "floor"), "placed")
            self.assertEqual(relic_contents_state("second", "floor"), "placed")
            relic_release("ossuary")
            self.assertEqual(relic_contents_state("ossuary", "floor"), "unarmed")
            self.assertEqual(relic_contents_state("second", "floor"), "placed")
            # Re-arming a released relic places it again - which is what a return visit
            # to a rebuilt system has to do.
            relic_contents_arm("ossuary")
            self.assertEqual(placed.count("floor"), 3)
        finally:
            R._relic_place_contents = keep_place
            R._relic_place_role_markers = keep_marks
            relic_contents_clear()

    def test_releasing_stops_containment(self):
        rec = relic_record("ossuary")
        relic_volume(rec)
        relic_contain(rec)
        self.assertTrue(volume_watching("ossuary"))
        relic_release("ossuary")
        self.assertFalse(volume_watching("ossuary"))


class TestMarkersRevealAsYouReachThem(unittest.TestCase):
    """The ruin draws its own map, in the order you fly it.

    Visible from the start hands the crew a floor plan and the location of the loot before
    they have flown anything; invisible for good leaves them with no record of where they
    have been, in a structure whose whole problem is that every room looks like the last.
    So a marker is dark until a ship reaches it, and then it stays lit.
    """

    def setUp(self):
        sbs.create_new_sim()
        SpaceObject.clear()
        relics_clear()
        volume_clear()
        relic_contents_clear()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        import sbs_utils.procedural.amd_relics as R
        self.R = R
        R._ARM_TASK = None
        relics_register(_section(CONTENTS_DOC))
        relic_contents_arm("ossuary")

    def tearDown(self):
        relic_contents_clear()
        SpaceObject.clear()
        DeleteQueue.clear()
        FrameContext.context = None

    def _post(self, part):
        return self.R._ARMED[("marker", "ossuary", part)]

    def _lit(self, part):
        obj = to_object(self._post(part).get("id"))
        return obj is not None and obj.data_set.get("unselectable", 0) == 0

    def test_a_marker_starts_dark(self):
        self.assertFalse(self._lit("vaultmark"))
        self.assertFalse(self._post("vaultmark")["shown"])

    def test_reaching_it_lights_it(self):
        ship = player_spawn(50000, 0, 50000, "Test", "tsn", "tsn_light_cruiser")
        self.R._relic_contents_tick()
        self.assertFalse(self._lit("vaultmark"))       # 50,000u away: still dark
        # The door is at Loc 1000,0,2000 + 100,0,0. Inside the reveal range, not on it.
        set_pos(ship.id, 1100.0 + 800.0, 0.0, 2000.0)
        self.R._relic_contents_tick()
        self.assertTrue(self._lit("vaultmark"))

    def test_it_stays_lit_when_you_leave(self):
        # The point of the map is that it is a RECORD. A marker that goes dark again
        # would tell the crew nothing about where they have already been.
        ship = player_spawn(1100.0 + 800.0, 0.0, 2000.0, "Test", "tsn", "tsn_light_cruiser")
        self.R._relic_contents_tick()
        self.assertTrue(self._lit("vaultmark"))
        set_pos(ship.id, 90000.0, 0.0, 90000.0)
        self.R._relic_contents_tick()
        self.assertTrue(self._lit("vaultmark"))

    def test_reaching_one_place_does_not_light_the_others(self):
        # The failure the whole design is against: arriving and being handed the floor
        # plan. Standing at the vault door says nothing about the reliquary.
        player_spawn(1100.0 + 800.0, 0.0, 2000.0, "Test", "tsn", "tsn_light_cruiser")
        self.R._relic_contents_tick()
        self.assertTrue(self._lit("vaultmark"))
        for other in ("cache", "floor", "ambush"):
            key = ("marker", "ossuary", other)
            if key in self.R._ARMED:
                self.assertFalse(self._lit(other), other)

    def test_a_mission_can_turn_the_whole_thing_off(self):
        relic_contents_clear()
        self.R._ARM_TASK = None
        relic_contents_arm("ossuary", reveal=0)
        player_spawn(1100.0, 0.0, 2000.0, "Test", "tsn", "tsn_light_cruiser")
        self.R._relic_contents_tick()
        self.assertFalse(self._lit("vaultmark"))


class TestPointInSolidLint(unittest.TestCase):
    """The mistake an author actually makes, and the one that only looks like it.

    A point buried in a subtracted mass is a place no ship can reach - so the item spawns
    inside rock and the `reach` trigger on it never fires, with nothing said. It is easy to
    make because the obvious place for a marker is the middle of a room and the obvious
    place for a pillar is also the middle of a room, and the plan view hides it: a solid is
    drawn as a hole, not as a wall.
    """

    def _lint(self, content):
        from sbs_utils.procedural.amd_lint import amd_lint_relics
        from sbs_utils.procedural.amd_core import parse
        return [f.code for f in amd_lint_relics(parse(content))]

    BASE = """# [T](t)

## [Relics](relics)

### [R](r)
---
Loc: 0,0,0
---

### [hub](hub)
---
Relic: r
Chamber: 0, 0, 0, 900
---

### [the core](core)
---
Relic: r
Solid: sphere, 0, 0, 0, 320
---

### [a place](spot)
---
Relic: r
Point: {point}
---
"""

    def test_a_point_inside_a_pillar_is_flagged(self):
        self.assertIn("relic-point-in-solid",
                      self._lint(self.BASE.format(point="100, 0, 0")))

    def test_a_point_beside_it_is_fine(self):
        self.assertNotIn("relic-point-in-solid",
                         self._lint(self.BASE.format(point="600, 0, 0")))

    def test_the_suspended_core_pattern_is_not_flagged(self):
        # A mass hanging in the middle of a room you fly around is CORRECT - it is what
        # the Ossuary does. Only the point matters, not the solid's position.
        codes = self._lint(self.BASE.format(point="600, 0, 0"))
        self.assertEqual(codes, [])

    def test_a_capsule_catches_it_too(self):
        doc = self.BASE.replace("Solid: sphere, 0, 0, 0, 320",
                                "Solid: capsule, 0, -900, 0, 0, 900, 0, 220")
        self.assertIn("relic-point-in-solid", self._lint(doc.format(point="100, 0, 0")))
        self.assertNotIn("relic-point-in-solid", self._lint(doc.format(point="600, 0, 0")))

    def test_a_box_catches_it_too(self):
        doc = self.BASE.replace("Solid: sphere, 0, 0, 0, 320",
                                "Solid: box, 0, 0, 0, 300, 200, 300")
        self.assertIn("relic-point-in-solid", self._lint(doc.format(point="100, 0, 100")))
        self.assertNotIn("relic-point-in-solid", self._lint(doc.format(point="600, 0, 0")))

    def test_the_shipped_relics_are_clean(self):
        # The four this rule was written for. All of them had a point in rock at some
        # stage of authoring; none of them may have one now.
        import io as _io, os
        from sbs_utils.fs import get_mission_dir_filename
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for name in ("voice", "lens", "ash_warren"):
            path = os.path.join(here, "..", "StormsBeacon", "relics", name + ".amd")
            if not os.path.exists(path):
                continue
            codes = self._lint(_io.open(path, encoding="utf-8").read())
            self.assertNotIn("relic-point-in-solid", codes, name)
