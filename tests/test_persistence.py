"""Schema-versioned persistence (sbs_utils.procedural.persistence), extracted
from the Open Universe save layer. Pure; uses temp files."""
import os
import tempfile
import unittest
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()
from sbs_utils.procedural import persistence
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


def _bytes(path):
    with open(path, "rb") as f:
        return f.read()


def _boom(data):
    raise ValueError("bad migration")


class TestAFileThatWillNotLoadIsNeverOverwritten(unittest.TestCase):
    """`load() or {}` turned "could not read your save" into "here is an empty one",
    and the next write made it permanent. Each of these wrote over the file before."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.path = os.path.join(self.td.name, "s.yaml")

    def test_a_raising_migration_leaves_the_file_and_a_copy(self):
        PersistentStore(self.path, version=1).save({"a": 1})
        before = _bytes(self.path)
        store = PersistentStore(self.path, version=2, migrations={1: _boom}, backup="version")
        self.assertIsNone(store.load())
        self.assertEqual(store.last_status, persistence.STATUS_UNMIGRATABLE)
        self.assertIn("bad migration", store.last_error)
        self.assertEqual(_bytes(self.path), before)
        self.assertEqual(_bytes(self.path + ".v1.bak"), before)

    def test_update_refuses_to_write_over_an_unmigratable_file(self):
        PersistentStore(self.path, version=1).save({"a": 1})
        before = _bytes(self.path)
        store = PersistentStore(self.path, version=2, migrations={1: _boom}, backup="version")
        self.assertIsNone(store.update(b=2))
        self.assertEqual(_bytes(self.path), before)
        self.assertEqual(sorted(os.listdir(self.td.name)), ["s.yaml", "s.yaml.v1.bak"],
                         "the pre-upgrade backup IS the copy; no second one")

    def test_update_refuses_to_write_over_an_unreadable_file(self):
        with open(self.path, "w") as f:
            f.write("players: [unclosed\n  nope: : :\n")
        before = _bytes(self.path)
        store = PersistentStore(self.path, version=1)
        self.assertIsNone(store.load())
        self.assertEqual(store.last_status, persistence.STATUS_UNREADABLE)
        self.assertIsNone(store.update(b=2))
        self.assertEqual(_bytes(self.path), before)
        self.assertEqual(_bytes(self.path + ".unreadable.bak"), before)

    def test_set_aside_reuses_an_identical_copy_and_never_replaces_another(self):
        with open(self.path, "wb") as f:
            f.write(b"a: [1\n")
        store = PersistentStore(self.path, version=1)
        store.load()
        first = store.set_aside()
        self.assertEqual(store.set_aside(), first)
        with open(self.path, "wb") as f:
            f.write(b"a: [2\n")
        second = store.set_aside()
        self.assertNotEqual(second, first)
        self.assertEqual(_bytes(first), b"a: [1\n")
        self.assertEqual(_bytes(second), b"a: [2\n")

    def test_a_newer_file_loads_and_is_not_rewritten(self):
        PersistentStore(self.path, version=5).save({"a": 1, "later": {"x": 1}})
        before = _bytes(self.path)
        store = PersistentStore(self.path, version=2)
        self.assertEqual(store.load()["later"], {"x": 1})
        self.assertEqual(store.last_status, persistence.STATUS_NEWER)
        self.assertIsNone(store.update(b=2))
        self.assertEqual(_bytes(self.path), before)

    def test_an_empty_file_is_missing_not_broken(self):
        with open(self.path, "w") as f:
            f.write("\n")
        store = PersistentStore(self.path, version=1)
        self.assertIsNone(store.load())
        self.assertEqual(store.last_status, persistence.STATUS_MISSING)
        self.assertEqual(store.update(a=1)["a"], 1)

    def test_protect_off_is_the_old_behavior(self):
        with open(self.path, "w") as f:
            f.write("a: [1\n")
        store = PersistentStore(self.path, version=1, protect=False)
        self.assertEqual(store.update(b=2), {"b": 2, "save_version": 1})


class TestBackupPerVersion(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.path = os.path.join(self.td.name, "s.yaml")

    def test_each_version_climbed_from_keeps_its_own_backup(self):
        PersistentStore(self.path, version=1).save({"a": 1})
        v1 = _bytes(self.path)
        two = PersistentStore(self.path, version=2, backup="version",
                              migrations={1: lambda d: {**d, "b": 2}})
        two.save(two.load())
        v2 = _bytes(self.path)
        three = PersistentStore(self.path, version=3, backup="version",
                                migrations={1: lambda d: {**d, "b": 2},
                                            2: lambda d: {**d, "c": 3}})
        self.assertEqual(three.load(), {"a": 1, "b": 2, "c": 3, "save_version": 3})
        self.assertEqual(_bytes(self.path + ".v1.bak"), v1)
        self.assertEqual(_bytes(self.path + ".v2.bak"), v2)
        self.assertFalse(os.path.exists(self.path + ".bak"))

    def test_a_backup_is_written_once(self):
        PersistentStore(self.path, version=1).save({"a": 1})
        v1 = _bytes(self.path)
        store = PersistentStore(self.path, version=2, backup="version",
                                migrations={1: lambda d: {**d, "b": 2}})
        store.load()
        with open(self.path, "a") as f:
            f.write("extra: 1\n")
        store.load()
        self.assertEqual(_bytes(self.path + ".v1.bak"), v1)

    def test_a_current_file_is_not_backed_up(self):
        PersistentStore(self.path, version=2).save({"a": 1})
        store = PersistentStore(self.path, version=2, backup="version",
                                migrations={1: lambda d: d})
        self.assertEqual(store.load()["a"], 1)
        self.assertEqual(os.listdir(self.td.name), ["s.yaml"])


class TestUnknownKeysRideThrough(unittest.TestCase):
    def test_modify_keeps_what_it_does_not_know(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "s.yaml")
            PersistentStore(p, version=2).save({"state": {"relics": {"a": [1, 2]}}, "x": 1})

            def change(data):
                data["x"] = 2

            PersistentStore(p, version=2).modify(change)
            out = PersistentStore(p, version=2).load()
            self.assertEqual(out, {"state": {"relics": {"a": [1, 2]}}, "x": 2, "save_version": 2})

    def test_modify_may_return_a_replacement(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "s.yaml")
            PersistentStore(p, version=1).save({"x": 1})
            PersistentStore(p, version=1).modify(lambda data: {"y": 2})
            self.assertEqual(PersistentStore(p, version=1).load(), {"y": 2, "save_version": 1})


if __name__ == "__main__":
    unittest.main(verbosity=2)
