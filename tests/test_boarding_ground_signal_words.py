"""Two signal words on a boarding party's ground, through the game's own loader.

* `Hidden until: signal x` waits for `x`, exactly as `Hidden until: x` does. It used to
  wait for a signal called `signal x`, which nothing sends, so the thing stayed off the
  map for good - for a prop and for a person alike.
* A prop that opens sends the quest signal `<key>_opened` (as a relic's barrier does),
  so `Done when: signal strongbox_opened` completes with no route in the story.

The files are real files in a real folder, read by `document_get_amd_file` with the
mission parser and loaded by `boarding_ground_load` - the line a `story.mast` writes.

    python -m unittest tests.test_boarding_ground_signal_words
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import os
import shutil
import tempfile
import unittest

import sbs_utils.mast_sbs.story_nodes  # noqa: F401  (import first: circular import)
import cosmos_dev.mock.sbs as sbs
from tests.reset_helper import reset_mock

from sbs_utils.agent import Agent
from sbs_utils.handlerhooks import reset_mission_state
from sbs_utils.procedural import boarding_combat as K
from sbs_utils.procedural import boarding_ground as BG
from sbs_utils.procedural import boarding_props as P
from sbs_utils.procedural import tilemap as T
from sbs_utils.procedural import tilemap_art as TA
from sbs_utils.procedural.amd import amd_hidden_until_signal
from sbs_utils.procedural.amd_doc import amd_section
from sbs_utils.procedural.amd_mission import amd_mission_data
from sbs_utils.procedural.quest import document_get_amd_file, quest_is_complete
from sbs_utils.procedural.quest_driver import quest_grant_amd, quest_on_signal
from sbs_utils.procedural.signal import signal_emit, signal_observe, signal_unobserve

TILESET = """tileset: sw_yard
title: Yard ground
kinds:
  dirt:   walk see   look=dirt   color=#653
  rock:              look=rock   color=#444
"""

YARD = """area: sw_yard
title: The Yard
tileset: sw_yard
entry: pad
legend:
  .: dirt
  #: rock
  P: dirt @pad
  B: dirt @box
  C: dirt @cache
  N: dirt @nest
---
#########
#.P.B.C.#
#.....N.#
#########
"""

WORLD = """# [Mission](mission)

## [Quests](quests)

### [Open the strongbox](open_box)
---
Scope: shared
Starts when: at once
Done when: signal strongbox_opened
---
Get it open.

## [Props](props)

### [Strongbox](strongbox)
---
Area: sw_yard
Mark: box
Blocks: yes
Opens with: signal box_unlocked
---
A steel box.

### [Cache](cache)
---
Area: sw_yard
Mark: cache
Hidden until: signal lp_power
---
Under a tarp.

## [People](people)

### [Glassback](glassback)
---
Area: sw_yard
Mark: nest
Hidden until: signal nest_woken
---
It hunts heat.
"""


class _Base(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)
        sbs.resume_sim()
        self.addCleanup(reset_mission_state)
        T.tilemap_clear_tilesets()
        self.addCleanup(T.tilemap_clear_tilesets)
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.write("ground/yard.tileset", TILESET)
        self.write("ground/yard.tiles", YARD)
        self.write("mission.amd", WORLD)
        real_find = TA.tilemap_art_find
        TA.tilemap_art_find = lambda name: None
        self.addCleanup(setattr, TA, "tilemap_art_find", real_find)
        T._WATCH["task"] = object()         # no tick tasks in a unit test
        K._WATCH["task"] = object()
        self.doc = document_get_amd_file(os.path.join(self.tmp, "mission.amd"),
                                         data_parser=amd_mission_data)
        self.got = BG.boarding_ground_load(self.doc, folder=self.tmp)

    def write(self, rel, text):
        path = os.path.join(self.tmp, *rel.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        return path


class HiddenUntilSignalTests(_Base):
    def test_the_word_signal_is_not_part_of_the_name(self):
        self.assertEqual(amd_hidden_until_signal("signal lp_power"), "lp_power")
        self.assertEqual(amd_hidden_until_signal("lp_power"), "lp_power")
        self.assertEqual(amd_hidden_until_signal("Signal LP_Power"), "lp_power")
        self.assertEqual(amd_hidden_until_signal(None), "")
        # A signal that happens to BE called `signal` keeps its name.
        self.assertEqual(amd_hidden_until_signal("signal"), "signal")

    def test_a_prop_hidden_until_signal_x_appears_when_x_is_sent(self):
        self.assertEqual((self.got["props"], self.got["people"]), (2, 1))
        self.assertFalse(P.boarding_prop("cache")["shown"])
        self.assertIsNone(P.boarding_prop("cache")["id"])
        self.assertIsNone(P.boarding_prop_at("sw_yard", 6, 1))
        signal_emit("lp_power")
        self.assertTrue(P.boarding_prop("cache")["shown"])
        self.assertEqual(P.boarding_prop_at("sw_yard", 6, 1), "cache")

    def test_a_signal_called_signal_x_does_not_show_it(self):
        signal_emit("signal lp_power")
        self.assertFalse(P.boarding_prop("cache")["shown"])

    def test_a_person_hidden_until_signal_x_arrives_when_x_is_sent(self):
        self.assertIsNone(K.boarding_hostile("glassback")["id"])
        self.assertNotIn("glassback", self.got["unplaced"])
        signal_emit("nest_woken")
        rec = K.boarding_hostile("glassback")
        self.assertIsNotNone(rec["id"])
        self.assertEqual(T.tilemap_where(rec["id"]), ("sw_yard", 6, 2))

    def test_a_prop_added_from_code_reads_it_the_same_way(self):
        P.boarding_prop_add("crate", "sw_yard", "pad", hidden="signal crate_drop")
        self.assertFalse(P.boarding_prop("crate")["shown"])
        signal_emit("crate_drop")
        self.assertTrue(P.boarding_prop("crate")["shown"])


class OpenedIsAQuestSignalTests(_Base):
    def setUp(self):
        super().setUp()
        self.seen = []

        def heard(name, data):
            self.seen.append((name, dict(data or {})))
            # LegendaryMissions' `//shared/signal/quest_signal` route, in one line.
            if name == "quest_signal":
                quest_on_signal((data or {}).get("SIGNAL_NAME"))
        signal_observe(heard)
        self.addCleanup(signal_unobserve, heard)
        quest_grant_amd(Agent.SHARED_ID, amd_section(self.doc, "quests"))

    def test_opening_the_strongbox_completes_done_when_signal_strongbox_opened(self):
        self.assertFalse(quest_is_complete(Agent.SHARED_ID, "open_box"))
        self.assertFalse(P.boarding_prop("strongbox")["open"])
        signal_emit("box_unlocked")          # its `Opens with: signal box_unlocked`
        self.assertTrue(P.boarding_prop("strongbox")["open"])
        self.assertIn(("quest_signal", {"SIGNAL_NAME": "strongbox_opened"}), self.seen)
        self.assertTrue(quest_is_complete(Agent.SHARED_ID, "open_box"))

    def test_it_is_sent_once(self):
        signal_emit("box_unlocked")
        signal_emit("box_unlocked")
        self.assertFalse(P.boarding_prop_open("strongbox"))
        sent = [s for s in self.seen if s == ("quest_signal",
                                              {"SIGNAL_NAME": "strongbox_opened"})]
        self.assertEqual(len(sent), 1)

    def test_the_prop_opened_signal_is_still_sent(self):
        P.boarding_prop_open("strongbox", how="key")
        self.assertIn(("boarding_prop_opened",
                       {"BOARDING_PROP": "strongbox", "BOARDING_HOW": "key"}), self.seen)


if __name__ == "__main__":
    unittest.main()
