"""The ground fields a writer types that used to do nothing unless a mission wired them.

`Opens with: signal X` and `Hidden until: X` were stored and never looked at: the only
door a signal ever opened was Dawnline's, because Dawnline's own Python called
`boarding_props_signal`. `Scan:` reached the parsed record and was dropped on the way to
the table the xESS reads. `Blocks` / `Once` / `Calm` were free text read by two parsers.

Every test here goes through the REAL readers: the AMD document reader, the prop and
hostile declarers, `signal_emit`, and `sbs lint`'s own field check.

    python -m unittest tests.test_boarding_ground_fields
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

import sbs_utils.mast_sbs.story_nodes  # noqa: F401  (import first: circular import)
import cosmos_dev.mock.sbs as sbs
from tests.reset_helper import reset_mock

from sbs_utils.handlerhooks import reset_mission_state
from sbs_utils.procedural import tilemap as T
from sbs_utils.procedural import boarding_props as P
from sbs_utils.procedural import boarding_combat as K
from sbs_utils.procedural import signal as S
from sbs_utils.procedural.amd_doc import amd_document, amd_section
from sbs_utils.procedural.amd_mission import amd_mission_data
from sbs_utils.procedural.signal import signal_emit

AREA = """area: yard
title: The Yard
tileset: gf
entry: pad
legend:
  .: dirt
  #: rock
  P: dirt @pad
  D: dirt @door
  C: dirt @cache
  N: dirt @nest
---
############
#..........#
#.P....C...#
#........N.#
#######D####
#..........#
############
"""

KINDS = {"dirt": {"cell": "g:dirt"}, "rock": {"cell": "g:rock", "walk": False}}

WORLD = """# [Mission](mission)

## [Props](props)

### [Yard gate](gate)
---
Area: yard
Mark: door
Sprite: prop:door
Opens with: signal power_on
Blocks: yes
Scan: Mag-locked. No power on this side.
---
A rusted gate.

### [Buried cache](cache)
---
Area: yard
Mark: cache
Sprite: prop:crate
Hidden until: cache_found
Item: coil
Blocks: no
Once: yes
---

### [Loose plate](plate)
---
Area: yard
At: 3, 5
Blocks: true
---
A plate.

## [Hostiles](hostiles)

### [Glassback](glassback)
---
Area: yard
Mark: nest
Hidden until: nest_woken
Scan: Silicate carapace. It hunts heat.
---
It clicks.

### [Warden](warden)
---
Area: yard
At: 3, 3
Calm: yes
---

### [Stray](stray)
---
Area: yard
At: 5, 3
Calm: no
---
"""


class _Base(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)
        self.addCleanup(reset_mission_state)
        T.tilemap_tileset("gf", KINDS)
        T.tilemap_load(AREA)
        T._WATCH["task"] = object()         # no tick task in a unit test
        K._WATCH["task"] = object()
        self.doc = amd_document(WORLD, data_parser=amd_mission_data)
        P.boarding_props_declare(amd_section(self.doc, "props"))
        P.boarding_props_place()
        K.boarding_hostiles_declare(amd_section(self.doc, "hostiles"))
        K.boarding_hostiles_place()


class OpensWithSignalTests(_Base):
    def test_the_signal_opens_the_door_with_no_mission_code(self):
        self.assertFalse(P.boarding_prop_is_open("gate"))
        self.assertFalse(T.tilemap_is_open("yard", 7, 4))
        signal_emit("power_on")
        self.assertTrue(P.boarding_prop_is_open("gate"))
        self.assertTrue(T.tilemap_is_open("yard", 7, 4))

    def test_another_signal_does_not(self):
        signal_emit("power_off")
        signal_emit("cache_found")
        self.assertFalse(P.boarding_prop_is_open("gate"))


class HiddenUntilTests(_Base):
    def test_a_hidden_prop_is_not_on_the_map_until_its_signal(self):
        self.assertIsNone(P.boarding_prop("cache")["id"])
        self.assertIsNone(P.boarding_prop_at("yard", 7, 2))
        signal_emit("cache_found")
        self.assertEqual(P.boarding_prop_at("yard", 7, 2), "cache")

    def test_a_hidden_person_arrives_on_their_signal(self):
        self.assertIsNone(K.boarding_hostile("glassback")["id"])
        signal_emit("nest_woken")
        rec = K.boarding_hostile("glassback")
        self.assertIsNotNone(rec["id"])
        self.assertEqual(T.tilemap_where(rec["id"]), ("yard", 9, 3))

    def test_the_signal_name_is_matched_whatever_its_capitals(self):
        signal_emit("Cache_Found")
        self.assertEqual(P.boarding_prop_at("yard", 7, 2), "cache")


class NothingIsLeftListeningTests(_Base):
    def test_the_reset_stops_the_library_listening(self):
        self.assertIn(P._on_ground_signal, S._signal_observers)
        self.assertIn(K._on_ground_signal, S._signal_observers)
        P.boarding_props_clear()
        K.boarding_combat_clear()
        self.assertNotIn(P._on_ground_signal, S._signal_observers)
        self.assertNotIn(K._on_ground_signal, S._signal_observers)

    def test_a_signal_after_the_reset_touches_nothing(self):
        P.boarding_props_clear()
        K.boarding_combat_clear()
        signal_emit("power_on")
        signal_emit("nest_woken")
        self.assertEqual(P.boarding_props_count(), 0)
        self.assertEqual(K.boarding_combat_count(), 0)

    def test_a_mission_with_no_such_field_registers_nothing(self):
        P.boarding_props_clear()
        K.boarding_combat_clear()
        P.boarding_prop_add("crate", "yard", "5, 5", desc="A crate.")
        self.assertNotIn(P._on_ground_signal, S._signal_observers)


class AHostileGoingDownIsAQuestMilestoneTests(_Base):
    def test_the_quest_driver_is_told_by_the_name_a_quest_waits_on(self):
        """`Done when: signal hostile_down_stray`. The raw signal alone reaches no quest:
        the driver hears `quest_signal`, as it does for a scene's `; signal x`."""
        from sbs_utils.procedural.signal import signal_observe, signal_unobserve
        seen = []
        obs = lambda name, data: seen.append((name, dict(data or {})))
        signal_observe(obs)
        self.addCleanup(signal_unobserve, obs)
        self.assertEqual(K._hostile_hit(K.boarding_hostile("stray"), "full"), "down")
        self.assertIn(("hostile_down_stray", {"BOARDING_HOSTILE": "stray"}), seen)
        self.assertIn(("quest_signal", {"SIGNAL_NAME": "hostile_down_stray"}), seen)


class ScanTests(_Base):
    def test_a_props_scan_reaches_the_record_the_xess_reads(self):
        self.assertEqual(P.boarding_prop("gate").get("scan"),
                         "Mag-locked. No power on this side.")

    def test_a_persons_scan_reaches_the_record_the_xess_reads(self):
        self.assertEqual(K.boarding_hostile("glassback").get("scan"),
                         "Silicate carapace. It hunts heat.")

    def test_without_one_the_description_is_still_what_it_falls_back_to(self):
        rec = P.boarding_prop("plate")
        self.assertFalse(rec.get("scan"))
        self.assertEqual(rec.get("desc"), "A plate.")


class YesNoTests(_Base):
    def test_what_reads_as_yes_today_still_does(self):
        self.assertTrue(P.boarding_prop("gate")["blocks"])
        self.assertTrue(P.boarding_prop("plate")["blocks"])          # `true`
        self.assertTrue(P.boarding_prop("cache")["once"])
        self.assertTrue(K.boarding_hostile("warden")["calm"])
        self.assertEqual(K.boarding_hostile_state("warden"), "calm")

    def test_what_reads_as_no_today_still_does(self):
        self.assertFalse(P.boarding_prop("cache")["blocks"])
        self.assertFalse(P.boarding_prop("gate")["once"])            # not written
        self.assertFalse(K.boarding_hostile("stray")["calm"])
        self.assertFalse(K.boarding_hostile("glassback")["calm"])    # not written
        self.assertEqual(K.boarding_hostile_state("stray"), "idle")

    def test_the_schema_reads_the_field_as_a_real_yes_or_no(self):
        """What the editor and the linter are told the field IS."""
        from sbs_utils.procedural.amd_schema import amd_read_field
        self.assertEqual(amd_read_field("Blocks", "yes", "prop"), ("blocks", True))
        self.assertEqual(amd_read_field("Blocks", "no", "prop"), ("blocks", False))
        self.assertEqual(amd_read_field("Once", "Yes", "prop"), ("once", True))
        self.assertEqual(amd_read_field("Calm", "yes", "hostile"), ("calm", True))
        self.assertEqual(amd_read_field("Calm", "yse", "hostile"), ("calm", False))
        # Left blank decides nothing - it was `no` before it was typed, and still is.
        self.assertEqual(amd_read_field("Blocks", "", "prop"), ("blocks", False))

    def test_the_older_flags_read_exactly_as_they_did(self):
        from sbs_utils.procedural.amd_schema import amd_read_field
        for word, want in (("true", True), ("yes", True), ("on", True), ("1", True),
                           ("", True), ("false", False), ("no", False), ("maybe", False)):
            self.assertEqual(amd_read_field("Required", word, "quest"), ("required", want), word)

    def test_there_is_one_parser(self):
        from sbs_utils.procedural.amd_schema import amd_yes
        for word in ("yes", "Yes", "true", "1", "on", True):
            self.assertTrue(amd_yes(word), word)
        for word in ("no", "false", "0", "off", "yse", "", None, False):
            self.assertFalse(amd_yes(word), word)
        self.assertTrue(amd_yes("", default=True))
        # The same words through the fields' own records, strings as a test or a
        # mission's Python would pass them.
        for word, want in (("yes", True), ("on", True), ("no", False), ("yse", False)):
            section = {"children": [{"key": "k", "display_text": "K", "description": "",
                                     "data": {"area": "yard", "at": "2, 5", "blocks": word,
                                              "once": word, "calm": word}}]}
            self.assertIs(P.boarding_prop_records(section)[0]["blocks"], want, word)
            self.assertIs(P.boarding_prop_records(section)[0]["once"], want, word)
            self.assertIs(K.boarding_hostile_records(section)[0]["calm"], want, word)


class LintTests(unittest.TestCase):
    def lint(self, text):
        from sbs_utils.procedural.amd_core import parse
        from sbs_utils.procedural.amd_lint import amd_lint_field_values
        return amd_lint_field_values(parse(text))

    def test_a_typo_in_calm_is_reported(self):
        found = self.lint(WORLD.replace("Calm: yes", "Calm: yse"))
        self.assertEqual([f.code for f in found], ["unknown-enum-value"])
        self.assertIn("Calm: yse", found[0].message)

    def test_a_typo_in_blocks_and_once_is_reported(self):
        found = self.lint(WORLD.replace("Blocks: no", "Blocks: nope")
                          .replace("Once: yes", "Once: yess"))
        self.assertEqual(sorted(f.message.split("`")[1] for f in found),
                         ["Blocks: nope", "Once: yess"])

    def test_every_spelling_that_reads_is_clean(self):
        self.assertEqual(self.lint(WORLD), [])
        for word in ("yes", "no", "true", "false", "on", "off", "1", "0", "Yes", "NO"):
            self.assertEqual(self.lint(WORLD.replace("Calm: yes", "Calm: " + word)), [], word)

    def test_the_older_yes_no_fields_are_as_lenient_as_they_were(self):
        """`Win:` carries its sentence; it must not start being a typo."""
        quest = ("# [M](m)\n\n## [Quests](quests)\n\n### [Hold](hold)\n---\n"
                 "Done when: signal held\nWin: The line held.\nRequired: maybe\n---\n")
        self.assertEqual(self.lint(quest), [])


STORY = '''shared MISSION_DOC = None

@map/away "Away"
    shared MISSION_DOC = document_get_amd_file(get_mission_dir_filename("mission.amd"), data_parser=amd_mission_data)
    quest_grant_amd(SHARED, amd_section(MISSION_DOC, "quests"))
    boarding_ground_load(MISSION_DOC)
    ->END
'''

WIRED = WORLD + """
## [Quests](quests)

### [Clear the yard](clear)
---
Scope: shared
Starts when: at once
Done when: signal hostile_down_stray
---
Put it down.

## [Scenes](scenes)

### [A switch](switch)
% A switch.

- [Throw it]() ; signal power_on
- [Dig]() ; signal cache_found
- [Shout]() ; signal nest_woken
"""


class LintKnowsWhatTheLibraryHearsTests(unittest.TestCase):
    """The signals the ground wires itself have no route in the story and no line that
    sends them - which is exactly what the two signal checks look for."""

    def found(self, text):
        from sbs_utils.procedural.amd_lint import amd_lint
        return sorted((f.code, f.message.split("`")[3]) for f in amd_lint(
            file_path="mission.amd", content=text, mast_sources=[STORY], cross_file=True)
            if f.code in ("signal-no-route", "unfired-signal"))

    def test_a_signal_a_door_or_a_hidden_thing_waits_on_needs_no_route(self):
        self.assertEqual(self.found(WIRED), [])

    def test_a_signal_nothing_waits_on_is_still_reported(self):
        text = WIRED.replace("; signal power_on", "; signal power_onn")
        self.assertEqual(self.found(text), [("signal-no-route", "power_onn")])

    def test_a_hostile_going_down_is_a_signal_somebody_sends(self):
        text = WIRED.replace("signal hostile_down_stray", "signal hostile_down_stary")
        self.assertEqual(self.found(text), [("unfired-signal", "hostile_down_stary")])


if __name__ == "__main__":
    unittest.main()
