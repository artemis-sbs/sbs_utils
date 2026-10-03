"""One call puts a file's ruins in the game - and the mistakes around it are no longer
silent.

Found by the lesson "A ruin is a place". A standalone mission needed a four-line recipe
card to build a ruin (`relics_build`, `relic_walls`, `relic_contents_arm`,
`marker_point`), and around that card:

  * only the FIRST relic in the file was built; a second was ignored without a word;
  * a `Passage to:` naming a room that was not there raised out of the map label, and a
    map label that dies spawns no players either;
  * `Passage to:` on a box, or pointing at one, did the same - though the plan view
    draws it, its connect gesture writes it, and lint was clean;
  * a section keyed `ruins` was typed, linted and drawn as relics, and not built;
  * a room with one hash too many, one too few, or no `Relic:` line was drawn by the
    plan and missing from the game, with lint clean;
  * a live reload moved the space and left the walls where the old space was.

    python -m unittest tests.test_relics_spawn
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
    relic_record, relic_reload, relic_spawn, relic_wall_role, relic_atmos_role,
    relics_load, relics_spawn,
)
from sbs_utils.procedural.roles import role
from sbs_utils.procedural.volume import volume_contains, volume_get, volume_watching

RUIN = """# [Mission](mission)

## [{section}]({section_key})

### [The Hollow](hollow)
---
Loc: 0, 0, 20000
---
Older than anyone who could have built it.

### [The Mouth](mouth)
---
Relic: hollow
Chamber: 0, 0, 0, 900
---
The way in.

### [The Nave](nave)
---
Relic: hollow
Chamber: 3000, 0, 0, 1100
Passage to: mouth 350
---
The big room.
"""

SECOND = """
### [The Cyst](cyst)
---
Loc: 40000, 0, 0
Atmosphere: purple
---
A second ruin, far off.

### [The Sac](sac)
---
Relic: cyst
Chamber: 0, 0, 0, 800
---
One room.
"""


def _ruin(section="Relics", section_key="relics"):
    return RUIN.format(section=section, section_key=section_key)


def _codes(text):
    return [f.code for f in amd_lint(content=text, cross_file=False)]


class _Base(unittest.TestCase):
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

    def write(self, text):
        with open(self.path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        return self.path

    def navpoints(self):
        return [n.text for n in sbs.sim.nav_points_by_id.values()]


class OneCallBuildsTheRuinTests(_Base):
    def test_space_walls_and_a_name_on_the_map(self):
        built = relics_spawn(self.write(_ruin()))
        self.assertEqual([r.key for r in built], ["hollow"])
        vol = volume_get("hollow")
        self.assertTrue(volume_contains(vol, (1500, 0, 20000)))     # in the passage
        self.assertGreater(len(role(relic_wall_role("hollow"))), 100)
        self.assertEqual(len(role("relic_wall")), len(role(relic_wall_role("hollow"))))
        self.assertIn("The Hollow", self.navpoints())
        self.assertEqual(self.heard, [])

    def test_walls_are_scenery_unless_containment_is_asked_for(self):
        relics_spawn(self.write(_ruin()))
        self.assertFalse(volume_watching("hollow"))

    def test_containment_on_request(self):
        relics_spawn(self.write(_ruin()), contain=True)
        self.assertTrue(volume_watching("hollow"))

    def test_every_relic_in_the_file(self):
        built = relics_spawn(self.write(_ruin() + SECOND))
        self.assertEqual([r.key for r in built], ["hollow", "cyst"])
        self.assertIsNotNone(volume_get("cyst"))
        self.assertGreater(len(role(relic_wall_role("cyst"))), 50)

    def test_a_nebula_only_where_the_file_asks_for_one(self):
        relics_spawn(self.write(_ruin() + SECOND))
        self.assertEqual(len(role(relic_atmos_role("hollow"))), 0)
        self.assertGreater(len(role(relic_atmos_role("cyst"))), 0)

    def test_a_file_with_no_ruin_is_not_an_error(self):
        self.assertEqual(relics_spawn(self.write("# [Mission](mission)\n\nNo ruins.\n")), [])
        self.assertEqual(self.heard, [])

    def test_twice_builds_nothing_twice(self):
        path = self.write(_ruin())
        relics_spawn(path)
        walls, marks = len(role("relic_wall")), len(self.navpoints())
        relics_spawn(path)
        self.assertEqual(len(role("relic_wall")), walls)
        self.assertEqual(len(self.navpoints()), marks)
        self.assertEqual(relic_record("hollow").get("volume"), "hollow")

    def test_the_section_may_be_called_ruins(self):
        built = relics_spawn(self.write(_ruin("Ruins", "ruins")))
        self.assertEqual([r.key for r in built], ["hollow"])


class ItSaysWhatWentWrongTests(_Base):
    def test_a_passage_to_nowhere_costs_that_ruin_and_says_so(self):
        text = _ruin().replace("Passage to: mouth 350", "Passage to: crypt 350") + SECOND
        built = relics_spawn(self.write(text))            # must not raise
        self.assertEqual([r.key for r in built], ["cyst"])
        said = [l for l in self.heard if "hollow" in l and "crypt" in l]
        self.assertEqual(len(said), 1, self.heard)

    def test_no_loc_is_said(self):
        relics_spawn(self.write(_ruin().replace("Loc: 0, 0, 20000\n", "Seed: 3\n")))
        self.assertEqual(len([l for l in self.heard if "Loc:" in l]), 1, self.heard)
        self.assertIsNotNone(volume_get("hollow"))

    def test_a_relic_with_no_rooms_is_said(self):
        text = _ruin().replace("### [The Mouth]", "#### [The Mouth]").replace(
            "### [The Nave]", "#### [The Nave]")
        self.assertEqual(relics_spawn(self.write(text)), [])
        self.assertEqual(len([l for l in self.heard if "no rooms" in l]), 1, self.heard)

    def test_an_unknown_key_is_said(self):
        relics_load(self.write(_ruin()))
        self.assertIsNone(relic_spawn("holow"))
        self.assertEqual(len([l for l in self.heard if "holow" in l]), 1)


BOX = """
### [The Gallery](gallery)
---
Relic: hollow
Box: 3000, 0, -3000, 600, 400, 800
Passage to: nave 300
---
A built room.
"""


class APassageMayEndOnABoxTests(_Base):
    def test_written_on_the_box(self):
        built = relics_spawn(self.write(_ruin() + BOX))
        self.assertEqual([r.key for r in built], ["hollow"])
        self.assertTrue(volume_contains(volume_get("hollow"), (3000, 0, 18400)))
        self.assertEqual(self.heard, [])

    def test_pointing_at_the_box(self):
        text = _ruin().replace("Passage to: mouth 350",
                               "Passage to: mouth 350, gallery 300") \
            + BOX.replace("Passage to: nave 300\n", "")
        built = relics_spawn(self.write(text))
        self.assertEqual([r.key for r in built], ["hollow"])
        self.assertTrue(volume_contains(volume_get("hollow"), (3000, 0, 18400)))

    def test_lint_sees_one_joined_ruin(self):
        codes = _codes(_ruin() + BOX)
        self.assertEqual([c for c in codes if c.startswith("relic-")], [])


class LintSeesWhatTheGameWillNotReadTests(unittest.TestCase):
    def test_the_lessons_ruin_is_clean(self):
        self.assertEqual(_codes(_ruin()), [])
        self.assertEqual(_codes(_ruin("Ruins", "ruins")), [])

    def test_a_room_with_one_hash_too_many(self):
        found = [f for f in amd_lint(
            content=_ruin().replace("### [The Nave]", "#### [The Nave]"), cross_file=False)
            if f.code == "relic-part-level"]
        self.assertEqual(len(found), 1)
        self.assertIn("3 hashes", found[0].message)

    def test_a_room_with_one_hash_too_few(self):
        codes = _codes(_ruin().replace("### [The Mouth]", "## [The Mouth]"))
        self.assertIn("relic-outside-section", codes)

    def test_a_room_with_no_relic_line(self):
        codes = _codes(_ruin().replace("Relic: hollow\nChamber: 0, 0, 0, 900",
                                       "Chamber: 0, 0, 0, 900"))
        self.assertIn("relic-part-no-owner", codes)

    def test_a_passage_to_nowhere_says_the_ruin_is_not_built(self):
        found = [f for f in amd_lint(
            content=_ruin().replace("Passage to: mouth 350", "Passage to: crypt 350"),
            cross_file=False) if f.code == "relic-dangling-passage"]
        self.assertEqual(len(found), 1)
        self.assertIn("does not build", found[0].message)

    def test_disconnected_points_at_the_relic_not_line_one(self):
        text = _ruin().replace("Passage to: mouth 350\n", "")
        found = [f for f in amd_lint(content=text, cross_file=False)
                 if f.code == "relic-disconnected"]
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].line, text.splitlines().index("### [The Hollow](hollow)") + 1)


class ALiveEditMovesTheWallsTests(_Base):
    def test_the_walls_follow_the_space(self):
        path = self.write(_ruin())
        relics_spawn(path)
        before = set(role(relic_wall_role("hollow")))
        self.write(_ruin().replace("Loc: 0, 0, 20000", "Loc: 0, 0, 60000"))
        self.assertIsNotNone(relic_reload("hollow"))
        now = set(role(relic_wall_role("hollow"))) - before
        self.assertGreater(len(now), 100)
        from sbs_utils.procedural.query import to_object
        zs = [to_object(i).pos.z for i in now if to_object(i) is not None]
        self.assertGreater(min(zs), 50000)


if __name__ == "__main__":
    unittest.main()
