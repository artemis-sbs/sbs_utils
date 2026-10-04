"""Dressing a ruin: the mistakes that built a ruin, ran clean, and looked wrong.

Found by the lesson "Dressing a ruin". Each of these linted clean and left
`mast.runtime.log` empty:

  * `Atmosphere: Purple` (a capital) was a RANDOM color - green on one run, white on the
    next - because the word was handed to the nebula spawner as written. A misspelled
    color was the same, and lint said it "falls back to yellow".
  * `Plate: 20` on one ordinary box made 20,092 objects.
  * `Dress: generic-tortus 4` placed nothing and said nothing.
  * `Gaps:` on a room, `Walls:` on a point, `Seed: abc`, `Gaps: 2`, `Hidden: maybe`, two
    `entrance` points, a place written outside every room: all silent.

    python -m unittest tests.test_relic_dressing
"""
import logging
import os
import tempfile
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # noqa: F401
from cosmos_dev.mock import sbs
from tests.reset_helper import reset_mock

from sbs_utils.delete_queue import DeleteQueue
from sbs_utils.procedural.amd_lint import amd_lint
from sbs_utils.procedural.amd_relics import (
    RELIC_PLATE_MAX, RELIC_PLATE_MIN, relic_atmos_role, relic_atmosphere_colors,
    relic_plate_size, relic_wall_role, relics_spawn,
)
from sbs_utils.procedural.roles import role

RUIN = """# [Mission](mission)

## [Relics](relics)

### [The Hollow](hollow)
---
Loc: 0, 0, 20000
Walls: rock
Seed: 11
Debris: 30
Gaps: 0.2
Atmosphere: purple
---
Older than anyone who could have built it.

### [The Mouth](mouth)
---
Relic: hollow
Chamber: 0, 0, 0, 900
---

### [The Gallery](gallery)
---
Relic: hollow
Box: 1400, 0, 0, 600, 400, 800
Walls: blocks
---

### [The Ring](ring)
---
Relic: hollow
Prop: 400, 0, 0
Dress: generic-torus 4
---

### [The Way In](way_in)
---
Relic: hollow
Point: -700, 0, 0
Roles: entrance
---

### [The Niche](niche)
---
Relic: hollow
Point: 1400, 0, 500
Roles: cache
Hidden: yes
---
"""

CODES = ("relic-walls-word", "relic-dial-range", "relic-field-wrong-record",
         "relic-prop-no-dress", "relic-dress-on-room", "relic-unknown-dress",
         "relic-hidden-value", "relic-role-near-entrance", "relic-two-entrances",
         "relic-point-outside", "relic-short-part", "relic-unknown-atmosphere")


def _found(text):
    return [f for f in amd_lint(content=text, cross_file=False) if f.code in CODES]


def _codes(text):
    return [f.code for f in _found(text)]


def _swap(old, new, text=RUIN):
    assert text.count(old) == 1, old
    return text.replace(old, new)


class TheLessonsRuinIsCleanTests(unittest.TestCase):
    def test_nothing_is_reported(self):
        self.assertEqual([f.code for f in amd_lint(content=RUIN, cross_file=False)], [])


class WallStyleTests(unittest.TestCase):
    def test_a_near_miss_is_named(self):
        found = _found(_swap("Walls: rock", "Walls: plats"))
        self.assertEqual([f.code for f in found], ["relic-walls-word"])
        self.assertIn("plates", found[0].message)

    def test_a_near_miss_inside_a_chain(self):
        self.assertIn("relic-walls-word", _codes(_swap("Walls: blocks", "Walls: bloks, plates")))

    def test_a_file_name(self):
        self.assertIn("relic-walls-word",
                      _codes(_swap("Walls: blocks", "Walls: torgoth.zip, plates")))

    def test_a_kit_name_before_a_built_in_is_fine(self):
        self.assertEqual(_codes(_swap("Walls: blocks", "Walls: torgoth, plates")), [])


class DialTests(unittest.TestCase):
    def test_every_unreadable_value(self):
        for old, new in (("Seed: 11", "Seed: abc"), ("Debris: 30", "Debris: lots"),
                         ("Gaps: 0.2", "Gaps: 20%"), ("Gaps: 0.2", "Gaps: 2"),
                         ("Debris: 30", "Debris: -5"), ("Seed: 11", "Seed: 1.5")):
            self.assertIn("relic-dial-range", _codes(_swap(old, new)), new)

    def test_a_plate_the_game_would_clamp(self):
        text = _swap("Gaps: 0.2", "Gaps: 0.2\nPlate: 20")
        self.assertIn("relic-dial-range", _codes(text))

    def test_good_values_are_quiet(self):
        text = _swap("Gaps: 0.2", "Gaps: 0\nPlate: 400")
        self.assertEqual(_codes(text), [])

    def test_the_plate_is_clamped_at_both_ends(self):
        self.assertEqual(relic_plate_size(20), RELIC_PLATE_MIN)
        self.assertEqual(relic_plate_size(99999), RELIC_PLATE_MAX)
        self.assertEqual(relic_plate_size(400), 400.0)
        self.assertEqual(relic_plate_size(0), 0.0)          # 0 = work it out
        self.assertEqual(relic_plate_size(-300), 0.0)
        self.assertEqual(relic_plate_size("many"), 0.0)


class AFieldOnTheWrongRecordTests(unittest.TestCase):
    def test_a_ruin_dial_on_a_room(self):
        text = _swap("Box: 1400, 0, 0, 600, 400, 800", "Box: 1400, 0, 0, 600, 400, 800\nGaps: 0.5")
        self.assertIn("relic-field-wrong-record", _codes(text))

    def test_walls_on_a_place(self):
        text = _swap("Roles: entrance", "Roles: entrance\nWalls: plates")
        self.assertIn("relic-field-wrong-record", _codes(text))

    def test_walls_on_a_room_is_what_it_is_for(self):
        self.assertNotIn("relic-field-wrong-record", _codes(RUIN))


class SetPieceTests(unittest.TestCase):
    def test_a_key_with_its_file_extension(self):
        found = _found(_swap("Dress: generic-torus 4", "Dress: generic-torus.obj 4"))
        self.assertEqual([f.code for f in found], ["relic-unknown-dress"])
        self.assertIn("generic-torus", found[0].message)

    def test_dress_on_a_room(self):
        text = _swap("Walls: blocks", "Walls: blocks\nDress: generic-torus 4")
        self.assertIn("relic-dress-on-room", _codes(text))

    def test_a_prop_with_nothing_to_put_there(self):
        self.assertIn("relic-prop-no-dress", _codes(_swap("Dress: generic-torus 4\n", "")))

    def test_a_prop_with_two_numbers(self):
        self.assertIn("relic-short-part", _codes(_swap("Prop: 400, 0, 0", "Prop: 400, 0")))


class PlaceTests(unittest.TestCase):
    def test_hidden_maybe(self):
        self.assertIn("relic-hidden-value", _codes(_swap("Hidden: yes", "Hidden: maybe")))

    def test_two_entrances(self):
        found = _found(_swap("Roles: cache", "Roles: entrance"))
        mine = [f for f in found if f.code == "relic-two-entrances"]
        self.assertEqual(len(mine), 1)
        self.assertIn("The Way In", mine[0].message)

    def test_entrance_misspelled(self):
        self.assertIn("relic-role-near-entrance",
                      _codes(_swap("Roles: entrance", "Roles: entrence")))

    def test_a_place_in_the_rock(self):
        found = _found(_swap("Point: 1400, 0, 500", "Point: 1400, 4000, 500"))
        mine = [f for f in found if f.code == "relic-point-outside"]
        self.assertEqual(len(mine), 1)
        want = _swap("Point: 1400, 0, 500", "Point: 1400, 4000, 500").splitlines().index(
            "Point: 1400, 4000, 500") + 1
        self.assertEqual(mine[0].line, want)

    def test_a_way_in_on_the_wall_is_inside_enough(self):
        self.assertNotIn("relic-point-outside", _codes(_swap("Point: -700, 0, 0", "Point: -900, 0, 0")))

    def test_a_way_in_stands_outside_on_purpose(self):
        """Every shipped ruin puts its `entrance` in open space outside the mouth."""
        self.assertNotIn("relic-point-outside", _codes(_swap("Point: -700, 0, 0", "Point: -4000, 0, 0")))


class FacingTests(unittest.TestCase):
    RING = "Dress: generic-torus 4"

    def test_a_key_that_is_not_there(self):
        text = _swap(self.RING, self.RING + "\nFacing: naive")
        self.assertIn("relic-facing-unknown",
                      [f.code for f in amd_lint(content=text, cross_file=False)])

    def test_a_part_or_a_direction_is_fine(self):
        for facing in ("mouth", "way_in", "1, 0, 0"):
            text = _swap(self.RING, self.RING + "\nFacing: " + facing)
            self.assertNotIn("relic-facing-unknown",
                             [f.code for f in amd_lint(content=text, cross_file=False)], facing)


class AFieldBelowTheFenceTests(unittest.TestCase):
    """A writer told to "add a line" adds it at the end - below the closing `---`, where
    it is part of the note. The record parsed and lint was clean."""

    def codes(self, text):
        return [f.code for f in amd_lint(content=text, cross_file=False)
                if f.code == "field-below-fence"]

    def test_a_relic_field_in_the_note(self):
        text = _swap("Point: -700, 0, 0\nRoles: entrance\n---\n",
                     "Point: -700, 0, 0\n---\nRoles: entrance\n")
        self.assertEqual(self.codes(text), ["field-below-fence"])

    def test_prose_with_a_colon_is_left_alone(self):
        text = _swap("Older than anyone who could have built it.",
                     "Note to self: older than anyone who could have built it.")
        self.assertEqual(self.codes(text), [])

    def test_a_field_word_later_in_the_prose_is_left_alone(self):
        text = _swap("Older than anyone who could have built it.",
                     "Older than anyone who could have built it.\nWalls: nobody knows what.")
        self.assertEqual(self.codes(text), [])

    def test_a_quest_field_in_the_note(self):
        quest = ("# [M](m)\n\n## [Quests](quests)\n\n### [Go](go)\n---\nScope: shared\n"
                 "Starts when: at once\n---\nDone when: reach derelict 500\nGo and look.\n")
        self.assertEqual(self.codes(quest), ["field-below-fence"])


class AtmosphereTests(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)
        DeleteQueue.clear()
        fd, self.path = tempfile.mkstemp(suffix=".amd")
        os.close(fd)
        self.addCleanup(os.remove, self.path)
        self.heard = []
        heard = self.heard

        class _Listen(logging.Handler):
            def emit(self, record):
                heard.append(record.getMessage())

        handler = _Listen()
        logging.getLogger("mast.runtime").addHandler(handler)
        self.addCleanup(logging.getLogger("mast.runtime").removeHandler, handler)

    def spawn(self, text):
        with open(self.path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        return relics_spawn(self.path)

    def cloud_colors(self):
        from sbs_utils.procedural.query import to_object
        out = set()
        for oid in role(relic_atmos_role("hollow")):
            obj = to_object(oid)
            if obj is not None:
                out.add(obj.get_inventory_value("cluster_color", None))
        return out

    def test_the_fixture_asks_for_a_real_color(self):
        self.assertIn("purple", relic_atmosphere_colors())

    def test_a_capital_letter_is_the_same_color(self):
        self.spawn(_swap("Atmosphere: purple", "Atmosphere: Purple"))
        self.assertGreater(len(role(relic_atmos_role("hollow"))), 0)
        self.assertEqual(self.heard, [])

    def test_a_word_that_is_not_a_color_makes_no_cloud_and_says_so(self):
        self.spawn(_swap("Atmosphere: purple", "Atmosphere: violet"))
        self.assertEqual(len(role(relic_atmos_role("hollow"))), 0)
        self.assertEqual(len([l for l in self.heard if "violet" in l]), 1, self.heard)

    def test_lint_says_the_same_before_the_game_is_started(self):
        found = _found(_swap("Atmosphere: purple", "Atmosphere: violet"))
        self.assertEqual([f.code for f in found], ["relic-unknown-atmosphere"])
        self.assertIn("no cloud", found[0].message)

    def test_a_set_piece_that_names_nothing_is_said(self):
        self.spawn(_swap("Dress: generic-torus 4", "Dress: generic-tortus 4"))
        self.assertEqual(len([l for l in self.heard if "generic-tortus" in l]), 1, self.heard)

    def test_wall_art_the_game_does_not_have_is_said_once(self):
        self.spawn(_swap("Chamber: 0, 0, 0, 900", "Chamber: 0, 0, 0, 900\nArt: plain_astroid_9"))
        said = [l for l in self.heard if "plain_astroid_9" in l]
        self.assertEqual(len(said), 1, self.heard)
        self.assertIn("'mouth'", said[0])

    def test_wall_art_the_game_has_is_quiet(self):
        self.spawn(_swap("Chamber: 0, 0, 0, 900", "Chamber: 0, 0, 0, 900\nArt: plain_asteroid_9"))
        self.assertEqual(self.heard, [])

    def test_a_tiny_plate_does_not_run_away(self):
        self.spawn(_swap("Gaps: 0.2", "Gaps: 0\nPlate: 20").replace("Walls: rock", "Walls: plates"))
        self.assertLess(len(role(relic_wall_role("hollow"))), 2500)


if __name__ == "__main__":
    unittest.main()
