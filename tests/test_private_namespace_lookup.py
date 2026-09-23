"""PrivateFileNamespace: a file's globals fall back to the shared mission namespace
for EVERY way of asking - a bare lookup, `in globals()`, and `globals().get()`.

OpenUniverse's `admiral_present()` is `"admiralty_configure" in globals()`. With only
`__missing__` implemented, `in` looked at the file's own names alone, answered False,
and the whole Admiral economy silently never switched on.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from sbs_utils.mast.mast_globals import MastGlobals

NS = MastGlobals.PrivateFileNamespace


class TestPrivateNamespaceLookup(unittest.TestCase):
    def setUp(self):
        self.shared = {"admiralty_configure": lambda: 1, "shared_only": 5}
        self.ns = NS(self.shared)
        self.ns["mine"] = 7
        self.ns["_private"] = 9

    def test_in_sees_shared_names(self):
        self.assertIn("admiralty_configure", self.ns)
        self.assertIn("mine", self.ns)
        self.assertNotIn("nothing_anywhere", self.ns)

    def test_get_sees_shared_names(self):
        self.assertEqual(self.ns.get("shared_only"), 5)
        self.assertEqual(self.ns.get("mine"), 7)
        self.assertEqual(self.ns.get("nothing_anywhere", "dflt"), "dflt")

    def test_a_file_name_wins_over_a_shared_one(self):
        self.shared["mine"] = 100
        self.assertEqual(self.ns.get("mine"), 7)
        self.assertEqual(self.ns["mine"], 7)

    def test_in_globals_from_code_run_in_the_namespace(self):
        """The real shape: code exec'd with this dict as globals asks `in globals()`."""
        exec("def present():\n    return 'admiralty_configure' in globals()\n", self.ns)
        self.assertTrue(self.ns["present"]())

    def test_private_names_are_still_not_published(self):
        self.assertNotIn("_private", self.shared)

    def test_builtins_are_not_in_globals(self):
        self.assertNotIn("len", self.ns)


if __name__ == "__main__":
    unittest.main()
