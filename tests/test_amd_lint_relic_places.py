"""Lint for what a place in a ruin says.

Found by the lesson "Places that speak". Both of these were lint clean and silent in play:

  * `Scene:` on a room, a set piece or the ruin itself. A scene opens when someone ARRIVES,
    and a route only ends at a `Point:` - so it was read, kept, and never opened.
  * The place's scene (or the beat that calls the ship) typed in the Relics section, right
    under its place. The relic reader takes it for a ruin with no rooms, and the dialogue
    and quest loaders never see it.

    python -m unittest tests.test_amd_lint_relic_places
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.procedural.amd_lint import amd_lint

RUIN = """# [Mission](mission)

## [Relics](relics)

### [The Hollow](hollow)
---
Loc: 0, 0, 20000
Walls: rock
---
Older than anyone who could have built it.

### [The Vault](vault)
---
Relic: hollow
Chamber: 0, 0, 0, 900
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

### [The Altar](altar)
---
Relic: hollow
Point: 0, 0, 0
Roles: altar
Scene: altar_look
Scan: A stone table, cut from the floor.
---

## [Dialogue](dialogue)

### [At the altar](altar_look)
% The table is cut from the floor of the room.

- [Step back]()

## [Quests](quests)

### [Marker One](marker_one)
---
Beat
Starts when: reach altar 600
Done when: signal altar_heard
---
"""

MINE = ("relic-field-wrong-record", "relic-section-stray")
SCENE = "### [At the altar](altar_look)\n% The table is cut from the floor of the room.\n\n- [Step back]()\n"
BEAT = ("### [Marker One](marker_one)\n---\nBeat\nStarts when: reach altar 600\n"
        "Done when: signal altar_heard\n---\n")


def found(text):
    return [f for f in amd_lint(file_path="mission.amd", content=text, cross_file=False)
            if f.code in MINE]


def moved(record, after="Scan: A stone table, cut from the floor.\n---\n"):
    """`record` taken out of its own section and typed under the altar."""
    assert RUIN.count(record) == 1 and RUIN.count(after) == 1
    return RUIN.replace(record, "").replace(after, after + "\n" + record)


class SceneOnTheWrongRecord(unittest.TestCase):
    def test_the_lesson_as_written_is_clean(self):
        self.assertEqual(found(RUIN), [])

    def test_scene_on_a_room_a_set_piece_or_the_ruin(self):
        for anchor in ("Chamber: 0, 0, 0, 900\n", "Dress: generic-torus 4\n", "Walls: rock\n"):
            with self.subTest(anchor=anchor):
                text = RUIN.replace(anchor, anchor + "Scene: altar_look\n")
                got = found(text)
                self.assertEqual([f.code for f in got], ["relic-field-wrong-record"])
                self.assertIn("`Point:`", got[0].message)

    def test_scan_on_a_room_is_what_it_is_for(self):
        text = RUIN.replace("Chamber: 0, 0, 0, 900\n", "Chamber: 0, 0, 0, 900\nScan: A dome.\n")
        self.assertEqual(found(text), [])


class ARecordThatIsNotARelic(unittest.TestCase):
    def test_the_places_scene_typed_under_the_place(self):
        got = found(moved(SCENE))
        self.assertEqual([f.code for f in got], ["relic-section-stray"])
        self.assertIn("a scene", got[0].message)
        self.assertIn("Dialogue", got[0].message)

    def test_the_beat_typed_under_the_place(self):
        got = found(moved(BEAT))
        self.assertEqual([f.code for f in got], ["relic-section-stray"])
        self.assertIn("a quest", got[0].message)
        self.assertIn("Quests", got[0].message)

    def test_a_ruin_with_a_note_and_no_fields_but_loc_is_left_alone(self):
        text = RUIN + "\n"
        text = text.replace("## [Dialogue](dialogue)",
                            "### [The Annex](annex)\n---\nLoc: 9000, 0, 0\n---\n"
                            "A second ruin, not built yet - no rooms.\n\n## [Dialogue](dialogue)")
        self.assertEqual(found(text), [])


if __name__ == "__main__":
    unittest.main()
