"""`sbs lint` must not open with "could not read ship data ... Check the Artemis install path".

It did, on every run, for every mission. The relic pass asked for the shipData catalog
before looking whether the document had a relic in it, and under the CLI the catalog is
not where the library looks (`exe_dir` is the Python program's folder there, not the
game's). So a writer linting an eight-line quest was told, first thing, that their
install was broken and that anything spawning a ship would fail.

`_relic_known_art` already promised "empty means SAY NOTHING". It said rather a lot.

    python -m unittest tests.test_amd_lint_ship_data_alarm
"""
import os
import tempfile
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils import fs
from sbs_utils.procedural import amd_lint as L
from sbs_utils.procedural import ship_data as SD
from sbs_utils.procedural.amd_lint import amd_lint

QUEST = """# [Sample Mission](sample)

## [Quests](quests)

### [Close Inspection](approach)
---
Scope: shared
Starts when: at once
Done when: reach derelict 500
---
Bring the ship in close.
"""

RELIC = """# [Ruin](ruin)

## [Relics](relics)

### [The Sink](sink)
---
Chamber: hall 0, 0, 0, 800
Art: no_such_hull_key
---
A hall.
"""


class NoRelicNoCatalogTests(unittest.TestCase):
    def setUp(self):
        self.asked = 0
        self._real = L._relic_known_art

        def counting():
            self.asked += 1
            return self._real()
        L._relic_known_art = counting

    def tearDown(self):
        L._relic_known_art = self._real

    def test_a_document_with_no_relic_never_asks_for_ship_data(self):
        amd_lint(content=QUEST)
        self.assertEqual(self.asked, 0)

    def test_a_relic_with_art_still_asks(self):
        """The check this protects must keep working."""
        amd_lint(content=RELIC)
        self.assertGreaterEqual(self.asked, 1)


class NoCatalogSaysNothingTests(unittest.TestCase):
    """The CLI's situation: `exe_dir` points somewhere with no `data/shipData` under it."""

    def setUp(self):
        self._exe_dir = fs.exe_dir
        # BOTH caches: `ship_index` is derived from `ship_data_cache` and kept separately,
        # so restoring only one leaves an empty index behind for every later test.
        self._cache = SD.ship_data_cache
        self._index = SD.ship_index
        self._get = SD.get_ship_data
        self.empty = tempfile.mkdtemp(prefix="no_cosmos_here_")
        fs.exe_dir = self.empty
        SD.ship_data_cache = None
        SD.ship_index = None
        self.loads = 0

        def counting():
            self.loads += 1
            return self._get()
        SD.get_ship_data = counting

    def tearDown(self):
        SD.get_ship_data = self._get
        SD.ship_data_cache = self._cache
        SD.ship_index = self._index
        fs.exe_dir = self._exe_dir
        os.rmdir(self.empty)

    def test_it_answers_empty(self):
        self.assertEqual(L._relic_known_art(), set())

    def test_it_does_not_try_the_load_that_raises_the_alarm(self):
        L._relic_known_art()
        self.assertEqual(self.loads, 0)

    def test_it_does_not_leave_an_empty_ship_table_cached(self):
        """A failed load caches `{"#ship-list": []}` for the rest of the process."""
        L._relic_known_art()
        self.assertIsNone(SD.ship_data_cache)

    def test_linting_a_relic_with_art_is_quiet_too(self):
        got = amd_lint(content=RELIC)
        self.assertNotIn("relic-unknown-art", [f.code for f in got])
        self.assertEqual(self.loads, 0)


class WithACatalogTests(unittest.TestCase):
    def setUp(self):
        self._cache = SD.ship_data_cache
        self._index = SD.ship_index
        SD.ship_data_cache = None
        SD.ship_index = None

    def tearDown(self):
        SD.ship_data_cache = self._cache
        SD.ship_index = self._index

    @unittest.skipUnless(
        any(os.path.exists(os.path.join(fs.get_artemis_data_dir(), "shipData" + ext))
            for ext in (".yaml", ".json")),
        "no shipData in this install")
    def test_a_reachable_catalog_is_still_read(self):
        known = L._relic_known_art()
        self.assertIn("tsn_light_cruiser", known)
        got = amd_lint(content=RELIC)
        self.assertIn("relic-unknown-art", [f.code for f in got])


if __name__ == "__main__":
    unittest.main()
