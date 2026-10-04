"""Saving a YAML file does not destroy the one that was there until the new one is whole.

`save_yaml_data` opened the file itself with 'w', which empties it before a byte is
written. Ten headless runs finishing their games in the same second met in
`game_results.yaml`: one read a half-written file, could not parse it, started a new list
and saved that. Two hundred games of history became the last twenty six.

    python -m unittest tests.test_fs_yaml_save_swap
"""
import os
import tempfile
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils import fs


class Unsavable:
    """Something no YAML dumper will write."""


class SaveSwapTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.path = os.path.join(self.dir.name, "results.yaml")

    def leftovers(self):
        return sorted(n for n in os.listdir(self.dir.name) if n != "results.yaml")

    def test_a_save_round_trips(self):
        fs.save_yaml_data(self.path, [{"mission": "one"}, {"mission": "two"}])
        self.assertEqual(fs.load_yaml_data(self.path), [{"mission": "one"}, {"mission": "two"}])
        self.assertEqual(self.leftovers(), [])

    def test_a_save_that_fails_leaves_the_old_file_whole(self):
        fs.save_yaml_data(self.path, [{"mission": "one"}])
        fs.save_yaml_data(self.path, [{"mission": "two"}, Unsavable()])
        self.assertEqual(fs.load_yaml_data(self.path), [{"mission": "one"}])
        self.assertEqual(self.leftovers(), [])

    def test_the_old_file_is_whole_for_as_long_as_the_new_one_is_being_written(self):
        fs.save_yaml_data(self.path, [{"mission": "one"}])
        seen = []

        def write(f):
            f.write("- mission: tw")                      # half a document
            seen.append(fs.load_yaml_data(self.path))     # what a second game would read
            f.write("o\n")

        fs._write_then_swap(self.path, write)
        self.assertEqual(seen, [[{"mission": "one"}]])
        self.assertEqual(fs.load_yaml_data(self.path), [{"mission": "two"}])
        self.assertEqual(self.leftovers(), [])

    def test_a_first_save_needs_no_file_to_be_there(self):
        fs.save_yaml_data(self.path, {"a": 1})
        self.assertEqual(fs.load_yaml_data(self.path), {"a": 1})


if __name__ == "__main__":
    unittest.main()
