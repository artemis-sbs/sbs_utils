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
)
from sbs_utils.procedural.volume import (
    volume_contains, volume_depth, volume_path, volume_get, volume_clear,
    volume_watching, volume_watch,
)

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
