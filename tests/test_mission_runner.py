import json
import os
import sys
import tempfile
import unittest

from cosmos_dev.mission_runner import _find_missions_root, _load_libs


def _make_layout(tmp, story_data):
    """Create missions_root/__lib__/ + MyMission/story.json inside tmp.

    Returns (mission_dir, missions_root, lib_dir).
    """
    missions_root = tmp
    mission_dir   = os.path.join(tmp, "MyMission")
    lib_dir       = os.path.join(tmp, "__lib__")
    os.makedirs(mission_dir, exist_ok=True)
    os.makedirs(lib_dir,     exist_ok=True)
    with open(os.path.join(mission_dir, "story.json"), "w") as f:
        json.dump(story_data, f)
    return mission_dir, missions_root, lib_dir


def _touch(path):
    """Create an empty file at path."""
    open(path, "w").close()


class TestFindMissionsRoot(unittest.TestCase):

    def test_finds_root_when_lib_in_direct_parent(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "__lib__"))
            mission_dir = os.path.join(tmp, "MyMission")
            os.makedirs(mission_dir)
            self.assertEqual(_find_missions_root(mission_dir), os.path.abspath(tmp))

    def test_finds_root_two_levels_up(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "__lib__"))
            mission_dir = os.path.join(tmp, "group", "MyMission")
            os.makedirs(mission_dir)
            self.assertEqual(_find_missions_root(mission_dir), os.path.abspath(tmp))

    def test_accepts_missions_root_itself_as_start(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "__lib__"))
            self.assertEqual(_find_missions_root(tmp), os.path.abspath(tmp))

    def test_raises_when_no_lib_dir_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            mission_dir = os.path.join(tmp, "MyMission")
            os.makedirs(mission_dir)
            with self.assertRaises(RuntimeError):
                _find_missions_root(mission_dir)

    def test_error_message_contains_start_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            mission_dir = os.path.join(tmp, "NoLib")
            os.makedirs(mission_dir)
            try:
                _find_missions_root(mission_dir)
                self.fail("Expected RuntimeError")
            except RuntimeError as e:
                self.assertIn("NoLib", str(e))


class TestLoadLibs(unittest.TestCase):

    def setUp(self):
        self._orig_path = list(sys.path)

    def tearDown(self):
        sys.path[:] = self._orig_path

    def test_adds_sbslib_to_sys_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            mission_dir, root, lib_dir = _make_layout(tmp, {"sbslib": ["fake.sbslib"]})
            lib_path = os.path.join(lib_dir, "fake.sbslib")
            _touch(lib_path)
            _load_libs(mission_dir, root)
            self.assertIn(lib_path, sys.path)

    def test_adds_mastlib_to_sys_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            mission_dir, root, lib_dir = _make_layout(tmp, {"mastlib": ["fake.mastlib"]})
            lib_path = os.path.join(lib_dir, "fake.mastlib")
            _touch(lib_path)
            _load_libs(mission_dir, root)
            self.assertIn(lib_path, sys.path)

    def test_adds_both_sbslib_and_mastlib(self):
        with tempfile.TemporaryDirectory() as tmp:
            mission_dir, root, lib_dir = _make_layout(
                tmp, {"sbslib": ["a.sbslib"], "mastlib": ["b.mastlib"]}
            )
            lib_a = os.path.join(lib_dir, "a.sbslib")
            lib_b = os.path.join(lib_dir, "b.mastlib")
            _touch(lib_a)
            _touch(lib_b)
            _load_libs(mission_dir, root)
            self.assertIn(lib_a, sys.path)
            self.assertIn(lib_b, sys.path)

    def test_missing_lib_does_not_raise(self):
        with tempfile.TemporaryDirectory() as tmp:
            mission_dir, root, lib_dir = _make_layout(
                tmp, {"sbslib": ["nonexistent.sbslib"]}
            )
            _load_libs(mission_dir, root)   # file absent — must not raise

    def test_missing_lib_does_not_add_to_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            mission_dir, root, lib_dir = _make_layout(
                tmp, {"sbslib": ["nonexistent.sbslib"]}
            )
            _load_libs(mission_dir, root)
            absent = os.path.join(lib_dir, "nonexistent.sbslib")
            self.assertNotIn(absent, sys.path)

    def test_no_story_json_does_not_raise(self):
        with tempfile.TemporaryDirectory() as tmp:
            lib_dir = os.path.join(tmp, "__lib__")
            mission_dir = os.path.join(tmp, "MyMission")
            os.makedirs(lib_dir)
            os.makedirs(mission_dir)
            _load_libs(mission_dir, tmp)    # no story.json — must not raise

    def test_does_not_add_duplicate_path_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            mission_dir, root, lib_dir = _make_layout(tmp, {"sbslib": ["dup.sbslib"]})
            lib_path = os.path.join(lib_dir, "dup.sbslib")
            _touch(lib_path)
            _load_libs(mission_dir, root)
            _load_libs(mission_dir, root)   # second call
            self.assertEqual(sys.path.count(lib_path), 1)

    def test_empty_story_json_does_not_raise(self):
        with tempfile.TemporaryDirectory() as tmp:
            mission_dir, root, _ = _make_layout(tmp, {})
            _load_libs(mission_dir, root)

    def test_lib_dir_as_directory_is_also_added(self):
        # sbslib can be a directory (unzipped), not just a zip file
        with tempfile.TemporaryDirectory() as tmp:
            mission_dir, root, lib_dir = _make_layout(
                tmp, {"sbslib": ["mylib_dir"]}
            )
            os.makedirs(os.path.join(lib_dir, "mylib_dir"))
            _load_libs(mission_dir, root)
            self.assertIn(os.path.join(lib_dir, "mylib_dir"), sys.path)


if __name__ == "__main__":
    unittest.main()
