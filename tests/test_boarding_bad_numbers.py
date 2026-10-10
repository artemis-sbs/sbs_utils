"""A number that is not a number never takes the mission down.

`Qty: two` and `Reach: far` raised `ValueError` inside `boarding_ground_load`, so no
ground loaded at all. `; take tablet completes pim_tablet` and `; calm sentry, give power
cell` raised inside `boarding_answer` - the second AFTER `calm` had been applied.

Now: the bad value is said once in `mast.runtime.log`, in a writer's words; a record uses
the default; an answer's outcomes are skipped WHOLE, before any of them is applied; and
`sbs lint` says so first.

Driven through `boarding_ground_load`, `dialogue_apply` and `amd_lint`.

    python -m unittest tests.test_boarding_bad_numbers
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import logging
import os
import shutil
import tempfile
import unittest

import sbs_utils.mast_sbs.story_nodes  # noqa: F401  (import first: circular import)
import cosmos_dev.mock.sbs as sbs
from sbs_utils.agent import clear_shared
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.procedural import amd_dialogue as D
from sbs_utils.procedural import boarding as A
from sbs_utils.procedural import boarding_checks as C
from sbs_utils.procedural import boarding_combat as K
from sbs_utils.procedural import boarding_ground as GR
from sbs_utils.procedural import boarding_props as P
from sbs_utils.procedural import boarding_tiles as BT
from sbs_utils.procedural import tilemap as T
from sbs_utils.procedural.amd_doc import amd_document
from sbs_utils.procedural.amd_lint import amd_lint
from sbs_utils.procedural.amd_mission import amd_mission_data
from sbs_utils.procedural.lifeform import lifeform_spawn

BADNUM_TILESET = """tileset: g
kinds:
  dirt:   walk see   look=dirt
  rock:              look=rock
"""

BADNUM_AREA = """area: yard
title: The Yard
tileset: g
entry: pad
legend:
  .: dirt
  #: rock
  P: dirt @pad
---
########
#.P....#
#......#
########
"""

BADNUM_WORLD = """# [World](world)

## [Props](props)

### [Fuse](fuse)
---
Area: yard
At: 4, 1
Sprite: g:dirt
Item: fuse
Qty: {qty}
---

### [Lever](lever)
---
Area: yard
At: 5, 1
Sprite: g:rock
Scene: pull
Reach: {reach}
Blocks: yes
---
A lever.

## [Hostiles](hostiles)

### [Sentry](sentry)
---
Area: yard
At: 5, 2
Sprite: g:rock
HP: {hp}
Drops: power_cell
---

## [Scenes](scenes)

### [Pull](pull)
% It moves.

- [Talk it down]() ; {outcome}
- [Leave it]()
"""


def _badnum_world(qty="2", reach="1", hp="3", outcome="calm sentry"):
    return BADNUM_WORLD.format(qty=qty, reach=reach, hp=hp, outcome=outcome)


class _BadNumHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.lines = []

    def emit(self, record):
        self.lines.append(record.getMessage())


class _BadNumBase(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        self.addCleanup(setattr, FrameContext, "context", None)
        SpaceObject.clear()
        clear_shared()
        for clear in (A.boarding_clear, T.tilemap_clear, T.tilemap_clear_tilesets,
                      BT.boarding_tile_clear, P.boarding_props_clear,
                      C.boarding_checks_clear, K.boarding_combat_clear,
                      GR.boarding_ground_clear, D.dialogue_outcome_notes_clear):
            clear()
            self.addCleanup(clear)
        self.folder = tempfile.mkdtemp(prefix="badnum_")
        self.addCleanup(shutil.rmtree, self.folder, ignore_errors=True)
        for name, text in (("g.tileset", BADNUM_TILESET), ("yard.tiles", BADNUM_AREA)):
            with open(os.path.join(self.folder, name), "w", encoding="utf-8",
                      newline="\n") as f:
                f.write(text)
        self.log = _BadNumHandler()
        logging.getLogger("mast.runtime").addHandler(self.log)
        self.addCleanup(logging.getLogger("mast.runtime").removeHandler, self.log)
        T._WATCH["task"] = object()
        K._WATCH["task"] = object()

    def load(self, **kw):
        import contextlib
        import io
        doc = amd_document(_badnum_world(**kw), data_parser=amd_mission_data)
        with contextlib.redirect_stdout(io.StringIO()):
            return GR.boarding_ground_load(doc, folder=self.folder)

    def said(self, word):
        return [line for line in self.log.lines if word in line]


class ARecordUsesTheDefaultTests(_BadNumBase):

    def test_the_ground_as_written_loads_and_says_nothing(self):
        got = self.load()
        self.assertEqual((got["areas"], got["props"], got["people"]), (1, 2, 1))
        self.assertEqual(P.boarding_prop("fuse")["qty"], 2)
        self.assertEqual(self.log.lines, [])

    def test_qty_two_is_one_and_the_ground_still_loads(self):
        got = self.load(qty="two")
        self.assertEqual((got["areas"], got["props"], got["people"]), (1, 2, 1))
        self.assertEqual(P.boarding_prop("fuse")["qty"], 1)
        self.assertIsNotNone(P.boarding_prop("fuse")["id"], "it is on the map")
        said = self.said("Qty")
        self.assertEqual(len(said), 1, self.log.lines)
        self.assertIn("two", said[0])
        self.assertIn("Fuse", said[0])
        self.assertIn("1", said[0])

    def test_reach_far_is_one(self):
        self.load(reach="far")
        self.assertEqual(P.boarding_prop("lever")["reach"], 1)
        self.assertEqual(len(self.said("Reach")), 1, self.log.lines)
        self.assertIn("far", self.said("Reach")[0])

    def test_hp_three_is_the_default_and_is_SAID(self):
        self.load(hp="three")
        self.assertEqual(K.boarding_hostile("sentry")["hp"], 2)
        said = self.said("HP")
        self.assertEqual(len(said), 1, self.log.lines)
        self.assertIn("three", said[0])
        self.assertIn("Sentry", said[0])

    def test_it_is_said_once_however_often_the_ground_is_loaded(self):
        self.load(qty="two", hp="three")
        self.load(qty="two", hp="three")
        self.assertEqual(len(self.said("Qty")), 1)
        self.assertEqual(len(self.said("HP")), 1)

    def test_a_number_written_as_a_number_with_a_decimal_is_fine(self):
        self.load(qty="3", reach="2", hp="4")
        self.assertEqual(P.boarding_prop("fuse")["qty"], 3)
        self.assertEqual(P.boarding_prop("lever")["reach"], 2)
        self.assertEqual(K.boarding_hostile("sentry")["hp"], 4)
        self.assertEqual(self.log.lines, [])


class AnAnswerIsSkippedWholeTests(_BadNumBase):

    def setUp(self):
        super().setUp()
        self.load()
        self.body = lifeform_spawn("Kovac", "", "boarding").id

    def outcomes(self, text):
        from sbs_utils.procedural.amd import amd_choice
        return amd_choice("- [Go]() ; " + text)["outcomes"]

    def test_give_with_a_space_in_the_item_does_not_raise_and_calm_is_not_applied(self):
        """`; calm sentry, give power cell`: `calm` used to be applied, then it raised."""
        self.assertEqual(K.boarding_hostile_state("sentry"), "idle")
        got = D.dialogue_apply(self.body, None, self.outcomes("calm sentry, give power cell"))
        self.assertIsNot(got, False, "the answer is not refused: the scene goes on")
        self.assertEqual(K.boarding_hostile_state("sentry"), "idle", "calm was applied")
        self.assertEqual(P.boarding_pack(self.body), {})
        said = self.said("give power cell")
        self.assertEqual(len(said), 1, self.log.lines)
        self.assertIn("power_cell", said[0])

    def test_take_followed_by_another_verb_with_no_comma(self):
        """`; take tablet completes pim_tablet`."""
        P.boarding_give(self.body, "tablet")
        got = D.dialogue_apply(self.body, None,
                               self.outcomes("take tablet completes pim_tablet"))
        self.assertIsNot(got, False)
        self.assertEqual(P.boarding_holding(self.body, "tablet"), 1, "nothing was taken")
        said = self.said("take tablet completes pim_tablet")
        self.assertEqual(len(said), 1, self.log.lines)
        self.assertIn("comma", said[0])

    def test_said_once_however_often_it_is_pressed(self):
        for _ in range(3):
            D.dialogue_apply(self.body, None, self.outcomes("give power cell"))
        self.assertEqual(len(self.said("give power cell")), 1)

    def test_the_right_spellings_still_work(self):
        D.dialogue_apply(self.body, None, self.outcomes("calm sentry, give power_cell"))
        self.assertEqual(K.boarding_hostile_state("sentry"), "calm")
        self.assertEqual(P.boarding_holding(self.body, "power_cell"), 1)
        D.dialogue_apply(self.body, None, self.outcomes("give fuse 3"))
        self.assertEqual(P.boarding_holding(self.body, "fuse"), 3)
        self.assertTrue(D.dialogue_apply(self.body, None, self.outcomes("take fuse 2")))
        self.assertEqual(P.boarding_holding(self.body, "fuse"), 1)
        # A take that cannot be paid still refuses the pick, as it always did.
        self.assertIs(D.dialogue_apply(self.body, None, self.outcomes("take fuse 5")), False)
        self.assertEqual(self.log.lines, [])

    def test_a_handler_that_raises_does_not_take_the_mission_down(self):
        def boom(agent_id, speaker, tokens):
            raise ValueError("no")
        D.dialogue_register_outcome("badnum_boom", boom)
        self.addCleanup(D._OUTCOME_HANDLERS.pop, "badnum_boom", None)
        got = D.dialogue_apply(self.body, None,
                               [("badnum_boom", "x"), ("give", "fuse")])
        self.assertIsNot(got, False)
        self.assertEqual(P.boarding_holding(self.body, "fuse"), 1, "the rest still ran")
        self.assertEqual(len(self.said("badnum_boom")), 1, self.log.lines)


class LintSaysSoFirstTests(unittest.TestCase):
    def codes(self, **kw):
        return [(f.code, f.message) for f in
                amd_lint(content=_badnum_world(**kw), cross_file=False)]

    def only(self, code, **kw):
        return [m for c, m in self.codes(**kw) if c == code]

    def test_as_written_is_clean_of_these(self):
        codes = [c for c, _ in self.codes()]
        self.assertNotIn("not-a-number", codes)
        self.assertNotIn("pack-item-shape", codes)

    def test_qty_reach_and_hp(self):
        for kw, word in (({"qty": "two"}, "Qty"), ({"reach": "far"}, "Reach"),
                         ({"hp": "three"}, "HP")):
            found = self.only("not-a-number", **kw)
            self.assertEqual(len(found), 1, (kw, found))
            self.assertIn(word, found[0])

    def test_a_whole_number_field_does_not_take_a_fraction_but_speed_would(self):
        self.assertEqual(len(self.only("not-a-number", qty="1.5")), 1)
        text = _badnum_world().replace("HP: 3\n", "HP: 3\nSpeed: 2.5\nCooldown: 1.5\n")
        self.assertEqual([f.code for f in amd_lint(content=text, cross_file=False)
                          if f.code == "not-a-number"], [])

    def test_an_item_key_with_a_space_in_give_and_take(self):
        found = self.only("pack-item-shape", outcome="calm sentry, give power cell")
        self.assertEqual(len(found), 1, found)
        self.assertIn("power_cell", found[0])
        found = self.only("pack-item-shape", outcome="take tablet completes pim_tablet")
        self.assertEqual(len(found), 1, found)
        for good in ("give power_cell", "give power_cell 2", "take fuse", "take fuse 3"):
            self.assertEqual(self.only("pack-item-shape", outcome=good), [], good)


if __name__ == "__main__":
    unittest.main()
