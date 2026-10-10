"""Nobody aboard a generated deck seals a room (procedural/boarding_deckplan.py).

A boarded ship's own crew stands still and blocks. The rule this pins, over every floor
plan LegendaryMissions ships and a mix of writer's `Area: deck` records: from where the
party arrives, every writer's record can be walked up to, every one of the ship's crew
can be walked up to, and every tile of floor nothing stands on can be walked - asked of
the game's own path finder (``tilemap_path`` / ``tilemap_is_open``), not of the
generator's bookkeeping.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import contextlib
import glob
import io
import os
import sys
import unittest
from collections import deque

import cosmos_dev.mock.sbs as mock_sbs
sys.modules.setdefault("sbs", mock_sbs)

import sbs_utils.mast_sbs.story_nodes  # noqa: F401  (import first: circular import)
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.procedural import boarding_combat as K
from sbs_utils.procedural import boarding_deckplan as D
from sbs_utils.procedural import boarding_props as P
from sbs_utils.procedural import tilemap as T


def _reach_grid_files():
    here = os.path.dirname(os.path.abspath(__file__))
    return sorted(glob.glob(os.path.join(here, "..", "..", "LegendaryMissions", "races",
                                         "*.grid")))


def _reach_near(c):
    x, y = c
    return ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))


#: The mixes of writer's records stood aboard each hull: (name, [(suffix, blocks)]) for
#: every kind of room the hull has, plus the entry and the hallway.
_REACH_MIXES = (
    ("one that blocks", [("a", True)]),
    ("one that does not", [("a", False)]),
    ("two that block", [("a", True), ("b", True)]),
    ("one of each", [("a", True), ("b", False)]),
)


class _ReachBase(unittest.TestCase):
    def setUp(self):
        mock_sbs.create_new_sim()
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent())
        self.addCleanup(setattr, FrameContext, "context", None)
        self.clears = (T.tilemap_clear, T.tilemap_clear_tilesets, P.boarding_props_clear,
                       D.boarding_deck_clear, K.boarding_combat_clear)
        for clear in self.clears:
            clear()
            self.addCleanup(clear)

    def board(self, text, records, people=(), hostile=False):
        """Build the deck as a visit does: the writer's records are declared first, the
        deck is built and they are settled, then the ship's own crew comes aboard."""
        for clear in self.clears:
            clear()
        P.boarding_props_declare({"children": [
            {"key": key, "display_text": key, "description": "x",
             "data": {"area": "deck", "mark": mark, "blocks": "yes" if blocks else "no"}}
            for key, mark, blocks in records]})
        K.boarding_hostiles_declare({"children": [
            {"key": key, "display_text": key, "description": "x",
             "data": {"area": "deck", "mark": mark, "calm": "yes" if calm else "no"}}
            for key, mark, calm in people]})
        plan = D.boarding_deck_plan_ascii(text)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            area = D.boarding_deck_build(plan, D.DECK_AREA)
            crew = D.boarding_deck_crew(area, hostile=hostile)
        return plan, area, crew

    #: Up to this much floor the walk is asked of `tilemap_is_open` / `tilemap_path`
    #: themselves, tile by tile. Above it (the starbases, the biggest warships) the same
    #: question is asked of the map those two read - walkable tiles less the cells a
    #: blocking actor covers - because the path finder scans every actor for every
    #: tile, which is minutes per starbase. The two are compared on every smaller hull.
    EXACT_BELOW = 400

    def open_cells(self, area):
        """The cells the path finder will walk: built from what `tilemap_is_open`
        reads (the tile kinds, the blocked cells, the blocking actors)."""
        rec = T._AREAS[area]
        covered = set()
        for aid in T.tilemap_actors(area):
            if T._ACTORS[aid]["blocks"]:
                covered.update(T.tilemap_actor_cells(aid))
        out = set()
        for y in range(rec["h"]):
            for x in range(rec["w"]):
                spec = T._kind_spec(rec, rec["tiles"][y][x])
                if spec and spec["walk"] and (x, y) not in rec["blocked"]                         and (x, y) not in covered:
                    out.add((x, y))
        return out

    def walked(self, area):
        """Everything a party can walk to from the entry, and the open cells."""
        start = T.tilemap_entry(area)
        opened = self.open_cells(area)
        exact = len(D._DECKS[area]["floor"]) <= self.EXACT_BELOW
        if exact:
            real = {c for c in D._DECKS[area]["floor"] | opened
                    if T.tilemap_is_open(area, c[0], c[1])}
            self.assertEqual(real, opened, "the test's map is not the path finder's")
        seen = {start}
        q = deque([start])
        while q:
            for n in _reach_near(q.popleft()):
                if n not in seen and n in opened:
                    seen.add(n)
                    q.append(n)
        return start, seen, opened, exact

    def check(self, area, crew, label):
        rec = D._DECKS[area]
        start, seen, opened, exact = self.walked(area)
        standing = {}
        for key, r in list(P._PROPS.items()) + list(K._HOSTILES.items()):
            if r.get("area") != area or r.get("id") is None:
                continue
            where = T.tilemap_where(r["id"])
            standing[key] = ((where[1], where[2]), r)
        # 1. The floor: every tile nothing blocking stands on.
        self.assertEqual((rec["floor"] & opened) - seen, set(),
                         (label, "floor nobody can walk to"))
        # 2. Everything a writer wrote, and everyone of her crew.
        for key, (cell, r) in sorted(standing.items()):
            if r.get("generated") and key not in crew:
                continue                             # furniture and doors
            if cell in opened:
                goals = [cell]
            else:
                goals = [n for n in _reach_near(cell) if n in seen]
            self.assertTrue(goals and (goals[0] in seen),
                            (label, key, cell, "cannot be walked up to"))
            goal = goals[0]
            if goal != start and exact:
                path = T.tilemap_path(area, start, goal)
                self.assertTrue(path and path[-1] == goal, (label, key, cell, "no path"))
        return standing


@unittest.skipUnless(_reach_grid_files(), "LegendaryMissions is not beside this repo")
class EveryShippedPlanCanBeWalkedTests(_ReachBase):

    def test_there_are_63_plans(self):
        self.assertEqual(len(_reach_grid_files()), 63)

    def wanted(self, text):
        """How many crew this hull had before the rule - asked of the same call, with
        nothing of a writer's aboard."""
        if text not in self._wanted:
            _, _, crew = self.board(text, [])
            self._wanted[text] = len(crew)
        return self._wanted[text]

    _wanted = {}

    def run_mix(self, mix, hostile=False, people=False):
        name, shape = mix
        self.counts = {"off": 0, "records": 0, "crew": 0, "crew_wanted": 0}
        try:
            self._run_mix(name, shape, hostile, people)
        finally:
            if os.environ.get("DECK_REACH_COUNTS"):
                print("COUNTS", name, hostile, people, self.counts)
        return self.counts

    def _run_mix(self, name, shape, hostile, people):
        for path in _reach_grid_files():
            hull = os.path.basename(path)
            with open(path, encoding="utf-8") as f:
                text = f.read()
            plan = D.boarding_deck_plan_ascii(text)
            kinds = sorted({D.boarding_deck_room_kind(n) for n in plan["cells"].values()}
                           | {"entry", "hallway"})
            records = [("%s_%s" % (kind, tag), kind, blocks)
                       for kind in kinds for tag, blocks in shape]
            folk = [("p_%s" % kind, kind, True) for kind in kinds] if people else []
            with self.subTest(plan=hull, mix=name):
                plan, area, crew = self.board(text, records, folk, hostile=hostile)
                standing = self.check(area, crew, (hull, name))
                settled = D._DECKS[area]["settled"]
                for key, _, blocks in records:
                    # Aboard - or, for something that BLOCKS on a hull with no floor
                    # left for it, said to be not aboard. Never stood on something.
                    if key not in standing:
                        self.assertTrue(blocks and settled[key].get("off"),
                                        (hull, key, "was not stood aboard"))
                        self.counts["off"] += 1
                    self.counts["records"] += 1
                cells = [c for c, _ in standing.values()]
                self.assertEqual(len(cells), len(set(cells)), (hull, "two on one cell"))
                self.counts["crew"] += len(crew)
                self.counts["crew_wanted"] += self.wanted(text)

    def test_one_that_blocks_in_every_kind(self):
        self.run_mix(_REACH_MIXES[0])

    def test_one_that_does_not_block_in_every_kind(self):
        counts = self.run_mix(_REACH_MIXES[1])
        # Something that does not block is ALWAYS aboard, on every hull.
        self.assertEqual(counts["off"], 0)
        # ... and they cost the ship none of her crew: the crowd is who it was.
        self.assertGreaterEqual(counts["crew"], counts["crew_wanted"] - 4)
        self.assertGreater(counts["crew_wanted"], 540)

    def test_two_that_block_in_every_kind(self):
        self.run_mix(_REACH_MIXES[2])

    def test_one_of_each_in_every_kind(self):
        self.run_mix(_REACH_MIXES[3])

    def test_aboard_an_enemy_with_guards_in_the_hallways(self):
        self.run_mix(_REACH_MIXES[3], hostile=True)

    def test_with_somebody_calm_of_the_writers_in_every_kind(self):
        self.run_mix(_REACH_MIXES[0], people=True)

    def test_the_crew_is_still_a_crowd_in_the_cabins(self):
        """Where they stand: hands in the rooms people live and work in, never on the
        way in or in a doorway - and as many as before on a hull with room for them."""
        path = next(p for p in _reach_grid_files() if p.endswith("pirate_brigantine.grid"))
        with open(path, encoding="utf-8") as f:
            text = f.read()
        plan, area, crew = self.board(text, [("strongbox", "quarters", True)])
        want = max(2, min(12, len(plan["cells"]) // 10))
        self.assertEqual(len(crew), want)
        avoid = set(T.tilemap_mark_cells(area, "entry")) | set(T.tilemap_mark_cells(area, "door"))
        halls = set(T.tilemap_mark_cells(area, "room:hallway"))
        for key in crew:
            r = K.boarding_hostile(key)
            self.assertTrue(r["calm"])
            self.assertEqual(r["state"], "calm")
            where = T.tilemap_where(r["id"])
            self.assertNotIn((where[1], where[2]), avoid)
            self.assertNotIn((where[1], where[2]), halls)

    def test_the_lessons_strongbox_in_the_captains_cabin_can_be_reached(self):
        """`agent_c3d_report.md` defect 1: `Mark: quarters` on the brigantine."""
        path = next(p for p in _reach_grid_files() if p.endswith("pirate_brigantine.grid"))
        with open(path, encoding="utf-8") as f:
            text = f.read()
        records = [("strongbox", "quarters", True), ("gull_kit", "entry", False)]
        plan, area, crew = self.board(text, records, [("oduya", "brig", True)])
        self.check(area, crew, "box_cabin")
        # ... and with twelve more things aboard that do not block (`free_rooms`).
        more = records + [("f_" + k, k, False) for k in (
            "sickbay", "bay", "brig", "cargo", "quarters", "beam", "impulse", "maneuver",
            "sensor", "shield", "torpedo", "warp")]
        plan, area, crew = self.board(text, [("strongbox", "brig", True)] + more[1:],
                                      [("oduya", "brig", True)])
        self.check(area, crew, "free_rooms")


class LateRecordsTests(_ReachBase):
    """A record declared after the crew came aboard is not stood on one of them."""

    def test_a_late_record_is_not_stood_on_the_crew(self):
        files = _reach_grid_files()
        if not files:
            self.skipTest("LegendaryMissions is not beside this repo")
        path = next(p for p in files if p.endswith("pirate_brigantine.grid"))
        with open(path, encoding="utf-8") as f:
            text = f.read()
        plan, area, crew = self.board(text, [])
        crew_cells = set()
        for key in crew:
            where = T.tilemap_where(K.boarding_hostile(key)["id"])
            crew_cells.add((where[1], where[2]))
        late = [("late_%d" % i, "quarters", bool(i % 2)) for i in range(12)]
        P.boarding_props_declare({"children": [
            {"key": key, "display_text": key, "description": "x",
             "data": {"area": "deck", "mark": mark, "blocks": "yes" if blocks else "no"}}
            for key, mark, blocks in late]})
        with contextlib.redirect_stdout(io.StringIO()):
            got = D.boarding_deck_settle(area)
        self.assertEqual(sorted(got), sorted(k for k, _, _ in late))
        self.assertEqual(set(got.values()) & crew_cells, set())
        self.check(area, crew, "late")


if __name__ == "__main__":
    unittest.main()
