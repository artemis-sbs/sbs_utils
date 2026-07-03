"""Schema-versioned persistence (sbs_utils.procedural.persistence), extracted
from the Open Universe save layer. Pure; uses temp files."""
import os
import tempfile
import unittest
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()
from sbs_utils.procedural.persistence import PersistentStore


class TestMigrate(unittest.TestCase):
    def test_absent_version_treated_as_1(self):
        s = PersistentStore("", version=1)
        self.assertEqual(s.migrate({"a": 1}), {"a": 1, "save_version": 1})

    def test_ladder_runs_single_step(self):
        migs = {1: lambda d: {**d, "b": 2}, 2: lambda d: {**d, "c": 3}}
        out = PersistentStore("", version=3, migrations=migs).migrate({"save_version": 1, "a": 1})
        self.assertEqual(out, {"save_version": 3, "a": 1, "b": 2, "c": 3})

    def test_newer_than_build_unchanged(self):
        s = PersistentStore("", version=1)
        self.assertEqual(s.migrate({"save_version": 5, "a": 1}), {"save_version": 5, "a": 1})

    def test_failure_returns_none(self):
        def boom(d):
            raise ValueError("bad migration")
        self.assertIsNone(PersistentStore("", version=2, migrations={1: boom}).migrate({"save_version": 1}))

    def test_non_dict_returns_none(self):
        self.assertIsNone(PersistentStore("", version=1).migrate("nope"))


class TestRoundTrip(unittest.TestCase):
    def test_save_stamps_and_load(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "save.yaml")
            PersistentStore(p, version=2).save({"x": 10})
            out = PersistentStore(p, version=2).load()
            self.assertEqual(out["x"], 10)
            self.assertEqual(out["save_version"], 2)

    def test_missing_file_is_none(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertIsNone(PersistentStore(os.path.join(td, "nope.yaml")).load())

    def test_update_merges_sections(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "s.yaml")
            s = PersistentStore(p, version=1)
            s.update(a=1)
            s.update(b=2)                 # must preserve a
            out = s.load()
            self.assertEqual(out["a"], 1)
            self.assertEqual(out["b"], 2)

    def test_backup_once_on_upgrading_load(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "s.yaml")
            PersistentStore(p, version=1).save({"a": 1})
            migs = {1: lambda d: {**d, "b": 2}}
            PersistentStore(p, version=2, migrations=migs).load()
            self.assertTrue(os.path.exists(p + ".bak"))

    def test_json_format(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "s.json")
            PersistentStore(p, version=1, fmt="json").save({"k": "v"})
            self.assertEqual(PersistentStore(p, version=1, fmt="json").load()["k"], "v")


if __name__ == "__main__":
    unittest.main(verbosity=2)
