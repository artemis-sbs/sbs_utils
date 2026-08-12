"""Tests for procedural.amd_relics - relics authored as AMD instead of buried YAML.

Parses a real AMD document rather than hand-built dicts: the point of the feature is that
an author's text becomes a volume, so a test that skips the text tests nothing.
"""

import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.procedural.amd import amd_parse_facts
from sbs_utils.procedural.amd_doc import amd_document, amd_section
from sbs_utils.procedural.amd_relics import (
    relics_from_section, relics_register, relic_record, relic_keys, relic_pos,
    relic_volume, relics_clear, relics_count, amd_relic_data, amd_relic_facts,
)
from sbs_utils.procedural.volume import (
    volume_contains, volume_depth, volume_path, volume_get, volume_clear,
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
