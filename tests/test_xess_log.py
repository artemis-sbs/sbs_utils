"""The survey log: scanning files the entry, and a revisit updates it.

    THE xESS ACTS. THE ePADD READS.

The device shows the LAST reading and a count; this is the record behind it. Two
properties carry the whole design and both are easy to lose:

* **There is no Record button.** SCAN files the entry, so the party's record fills in
  as they explore and nobody has to remember to keep it.
* **A room read twice UPDATES rather than appends.** A party walking back through the
  corridor it came in by would otherwise file the corridor over and over until the log
  was mostly corridor. The same identity rule the room-entry trigger already uses.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir

test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs
from sbs_utils.agent import clear_shared
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.procedural import survey_log as L


class _LogBase(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(0, "test"))
        FrameContext.page = None
        SpaceObject.clear()
        clear_shared()
        L.xess_log_clear()
        self.addCleanup(L.xess_log_clear)
        self.addCleanup(setattr, FrameContext, "page", None)


class ScanningFilesTheEntry(_LogBase):
    def test_a_reading_is_kept(self):
        L.xess_log("scan", "lab:bench", "The gel is cold.", site=1)
        self.assertEqual(1, L.xess_log_count())

    def test_the_newest_is_what_the_DEVICE_shows(self):
        L.xess_log("scan", "lab:bench", "One", site=1)
        L.xess_log("scan", "gallery:reactor", "Two", site=1)
        self.assertEqual("Two", L.xess_log_last()["text"])

    def test_entries_come_back_NEWEST_FIRST(self):
        L.xess_log("scan", "a", "One", site=1)
        L.xess_log("scan", "b", "Two", site=1)
        self.assertEqual(["Two", "One"], [e["text"] for e in L.xess_log_entries()])

    def test_a_revision_moves_on_every_write(self):
        """One number for a screen's `on change` to watch, rather than walking the
        list every frame."""
        before = L.xess_log_revision()
        L.xess_log("scan", "a", "One", site=1)
        self.assertNotEqual(before, L.xess_log_revision())

    def test_long_text_is_trimmed_with_ASCII(self):
        """The engine draws no ellipsis character."""
        entry = L.xess_log("scan", "a", "x" * (L.MAX_TEXT + 50), site=1)
        self.assertLessEqual(len(entry["text"]), L.MAX_TEXT)
        self.assertTrue(entry["text"].endswith("..."))
        self.assertTrue(all(ord(c) < 128 for c in entry["text"]))

    def test_the_log_is_capped(self):
        """A mission scanning every cell of a big interior loses its oldest readings
        rather than its frame rate."""
        for i in range(L.MAX_KEPT + 20):
            L.xess_log("scan", "cell-%d" % i, "x", site=1)
        self.assertEqual(L.MAX_KEPT, L.xess_log_count())


class ARevisitUpdatesRatherThanAppends(_LogBase):
    def test_the_same_room_twice_is_ONE_entry(self):
        L.xess_log("scan", "lab:bench", "Cold.", site=1)
        L.xess_log("scan", "lab:bench", "Colder.", site=1)
        self.assertEqual(1, L.xess_log_count())

    def test_and_it_holds_the_LATEST_reading(self):
        L.xess_log("scan", "lab:bench", "Cold.", site=1)
        L.xess_log("scan", "lab:bench", "Colder.", site=1)
        self.assertEqual("Colder.", L.xess_log_entries()[0]["text"])

    def test_the_count_is_how_a_revisit_is_VISIBLE(self):
        """Updating rather than appending would otherwise hide that anyone went back."""
        L.xess_log("scan", "lab:bench", "Cold.", site=1)
        L.xess_log("scan", "lab:bench", "Colder.", site=1)
        self.assertEqual(2, L.xess_log_entries()[0]["count"])

    def test_a_DIFFERENT_room_is_its_own_entry(self):
        L.xess_log("scan", "lab:bench", "One", site=1)
        L.xess_log("scan", "gallery:reactor", "Two", site=1)
        self.assertEqual(2, L.xess_log_count())

    def test_and_so_is_the_same_room_on_a_DIFFERENT_SITE(self):
        """Two outposts can both have a Sample Lab. Keying on the room alone would
        have the second overwrite the first's reading."""
        L.xess_log("scan", "lab:bench", "One", site=1)
        L.xess_log("scan", "lab:bench", "Two", site=2)
        self.assertEqual(2, L.xess_log_count())

    def test_and_so_is_a_different_KIND_of_reading(self):
        """A shot fired in a room is not the same fact as a scan of it."""
        L.xess_log("scan", "lab:bench", "One", site=1)
        L.xess_log("shot", "lab:bench", "Two", site=1)
        self.assertEqual(2, L.xess_log_count())


class ItCanBeFilteredForTheTileAndTheApp(_LogBase):
    def test_by_kind(self):
        L.xess_log("scan", "a", "One", site=1)
        L.xess_log("shot", "b", "Two", site=1)
        self.assertEqual(1, L.xess_log_count("scan"))
        self.assertEqual("Two", L.xess_log_last("shot")["text"])

    def test_by_site(self):
        L.xess_log("scan", "a", "One", site=1)
        L.xess_log("scan", "a", "Two", site=2)
        self.assertEqual(1, len(L.xess_log_entries(site=2)))

    def test_an_empty_log_answers_rather_than_raising(self):
        self.assertEqual([], L.xess_log_entries())
        self.assertIsNone(L.xess_log_last())
        self.assertEqual(0, L.xess_log_count())

    def test_an_entry_can_be_fetched_by_id(self):
        entry = L.xess_log("scan", "a", "One", site=1)
        self.assertEqual("One", L.xess_log_get(entry["id"])["text"])
        self.assertIsNone(L.xess_log_get(9999))


class TheSeamSCANAlreadyCalls(_LogBase):
    """`gui/xess._file` has called `xess_log` since before this store existed, as a
    no-op behind an ImportError. Now that it resolves, the call has to WORK - and a
    scan of a corridor (no room node) still must not file anything."""

    def test_the_device_calls_it_with_a_client_and_no_site(self):
        """`by=` is a CLIENT, which the store resolves to a crew NAME - a client id
        means nothing to somebody reading the log later, and the console that took a
        reading may be holding somebody else by then."""
        entry = L.xess_log("scan", "lab:bench", "Cold.", by=None)
        self.assertIn("by", entry)
        self.assertEqual(0, entry["site"], "no boarding host resolves to 0, not a crash")


if __name__ == "__main__":
    unittest.main()
