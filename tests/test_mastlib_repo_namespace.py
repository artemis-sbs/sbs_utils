"""Two packaged addons of ONE repo share a Python namespace, as their source folders do.

Open Universe ships two addons. `universe_core` asks whether the Admiral is there with
`"admiralty_configure" in globals()`, and `admiral`'s Python calls `universe_core`'s
helpers by bare name. Run from source folders both work, because sibling addon folders
share the mission's namespace. Packaged, each mastlib had a namespace of its own - so a
mission made by `sbs create -t ou` that added the admiral mastlib got no Admiral, no
error and an empty log. The one place it worked was the mission that never loads the
mastlibs. Found by the Class 5 author lessons.

Driven through `Mast.import_content` on real .mastlib files, the path the engine runs.
"""
import os
import tempfile
import unittest
import zipfile

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # noqa: F401
from sbs_utils.mast.mast import Mast
from sbs_utils.mast.mast_globals import MastGlobals

CORE = (
    "def krn_core_helper():\n"
    "    return 'core'\n"
    "def krn_admiral_present():\n"
    "    return 'krn_admiralty_configure' in globals()\n"
    "def _shared_name():\n"
    "    return 'core private'\n"
    "def krn_core_private():\n"
    "    return _shared_name()\n"
)
ADMIRAL = (
    "def krn_admiralty_configure():\n"
    "    return krn_core_helper() + ' seen from admiral'\n"
    "def _shared_name():\n"
    "    return 'admiral private'\n"
    "def krn_admiral_private():\n"
    "    return _shared_name()\n"
)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.before = set(MastGlobals.mission_py_modules)
        self.addCleanup(self._forget)

    def _forget(self):
        for key in set(MastGlobals.mission_py_modules) - self.before:
            MastGlobals.mission_py_modules.pop(key, None)
        for name in [n for n in MastGlobals.globals if n.startswith("krn_")]:
            MastGlobals.globals.pop(name, None)

    def lib(self, file_name, files):
        path = os.path.join(self.tmp.name, file_name)
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("__init__.mast", "".join(f"import {n}\n" for n in files))
            for name, src in files.items():
                z.writestr(name, src)
        return path

    def load(self, file_name, files):
        m = Mast()
        errors = m.import_content("__init__.mast", m, self.lib(file_name, files))
        self.assertEqual(errors, [], f"import errors: {errors}")


class TwoAddonsOfOneRepo(Base):
    def test_THE_CORE_SEES_THAT_THE_OTHER_ADDON_IS_LOADED(self):
        self.load("kowner.KRepo.core.v9.mastlib", {"krn_core.py": CORE})
        self.assertFalse(MastGlobals.globals["krn_admiral_present"]())
        self.load("kowner.KRepo.admiral.v9.mastlib", {"krn_admiral.py": ADMIRAL})
        self.assertTrue(MastGlobals.globals["krn_admiral_present"](),
                        "universe_core could not see the admiral addon it was loaded with")

    def test_one_addon_calls_the_others_helper_by_bare_name(self):
        self.load("kowner.KRepo.core.v9.mastlib", {"krn_core.py": CORE})
        self.load("kowner.KRepo.admiral.v9.mastlib", {"krn_admiral.py": ADMIRAL})
        self.assertEqual(MastGlobals.globals["krn_admiralty_configure"](),
                         "core seen from admiral")

    def test_load_order_does_not_matter(self):
        self.load("kowner.KRepo.admiral.v9.mastlib", {"krn_admiral.py": ADMIRAL})
        self.load("kowner.KRepo.core.v9.mastlib", {"krn_core.py": CORE})
        self.assertTrue(MastGlobals.globals["krn_admiral_present"]())
        self.assertEqual(MastGlobals.globals["krn_admiralty_configure"](),
                         "core seen from admiral")

    def test_an_underscore_name_is_still_private_to_its_file(self):
        self.load("kowner.KRepo.core.v9.mastlib", {"krn_core.py": CORE})
        self.load("kowner.KRepo.admiral.v9.mastlib", {"krn_admiral.py": ADMIRAL})
        self.assertEqual(MastGlobals.globals["krn_core_private"](), "core private")
        self.assertEqual(MastGlobals.globals["krn_admiral_private"](), "admiral private")

    def test_TWO_ADDONS_MAY_EACH_HAVE_A_FILE_OF_THE_SAME_NAME(self):
        """Sharing a namespace must not make the second `helpers.py` look already loaded."""
        self.load("kowner.KRepo.one.v9.mastlib",
                  {"helpers.py": "def krn_one():\n    return 1\n"})
        self.load("kowner.KRepo.two.v9.mastlib",
                  {"helpers.py": "def krn_two():\n    return 2\n"})
        self.assertEqual(MastGlobals.globals["krn_one"](), 1)
        self.assertIn("krn_two", MastGlobals.globals, "the second addon's file was skipped")
        self.assertEqual(MastGlobals.globals["krn_two"](), 2)


class AddonsOfDifferentRepos(Base):
    def test_another_repos_addon_is_not_in_the_namespace(self):
        self.load("kowner.KRepo.core.v9.mastlib", {"krn_core.py": CORE})
        self.load("kowner.Other.admiral.v9.mastlib", {"krn_admiral.py": ADMIRAL})
        self.assertFalse(MastGlobals.globals["krn_admiral_present"](),
                         "two repos must not share a Python namespace")

    def test_the_scope_key(self):
        key = Mast.lib_scope_key
        self.assertEqual(key("artemis-sbs.OpenUniverse.admiral.v1.4.0.mastlib"),
                         key(os.path.join("x", "y", "artemis-sbs.OpenUniverse.universe_core.v1.4.0.mastlib")))
        self.assertNotEqual(key("artemis-sbs.OpenUniverse.admiral.v1.4.0.mastlib"),
                            key("artemis-sbs.LegendaryMissions.ai.v1.4.0.mastlib"))
        self.assertEqual(key("odd_name.mastlib"), "odd_name.mastlib")


if __name__ == "__main__":
    unittest.main()
