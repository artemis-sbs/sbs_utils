"""Regression: a subfolder .py import inside a packaged (.mastlib) addon must not
shift the MAST import base for the sibling imports that follow it.

The casino addon's __init__.mast did `import games/engines.py` before several
`import *.mast` lines. When packaged, content_from_lib_or_file set the shared
basedir cursor to "games", so the next `import casino.mast` resolved to the
non-existent "games/casino.mast" and the addon failed to load. See
mast.import_python_module_for_source.
"""
import os, tempfile, zipfile, unittest
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()
import sbs_utils.mast.mast as mast_mod
from sbs_utils.mast.mast import Mast


class TestMastLibImportBasedir(unittest.TestCase):
    def _make_lib(self, tmp):
        path = os.path.join(tmp, "kimport_test.mastlib")
        with zipfile.ZipFile(path, "w") as z:
            # a subfolder .py import BEFORE a sibling .mast import: the bug case.
            z.writestr("__init__.mast",
                       "import sub/kimport_helper.py\nimport kimport_sibling.mast\n")
            z.writestr("sub/kimport_helper.py",
                       "def kimport_helper_fn():\n    return 42\n")
            z.writestr("kimport_sibling.mast",
                       "== kimport_sib ==\n    ->END\n")
        return path

    def test_subfolder_py_import_does_not_poison_siblings(self):
        with tempfile.TemporaryDirectory() as tmp:
            lib = self._make_lib(tmp)
            m = Mast()
            errors = m.import_content("__init__.mast", m, lib)
            self.assertEqual(errors, [], f"import errors: {errors}")
            # the sibling label loaded despite the preceding subfolder .py import
            self.assertIn("kimport_sib", m.labels)


class TestMastLibHandleRelease(unittest.TestCase):
    """A compile keeps .mastlib handles open (one per lib instead of one per file
    read), so it MUST drop them on the way out. A leaked handle is a Windows file
    lock: the lib can no longer be deleted or replaced, which breaks `sbs.pyz lib`
    rebuilds and any tooling that compiles then repackages.

    Covers both public entry points - the scope guard is depth-counted rather than
    keyed on `root is None`, because import_content() is entered directly with a
    non-None root and that path leaked.
    """

    def _make_lib(self, tmp):
        path = os.path.join(tmp, "krelease_test.mastlib")
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("__init__.mast", "import krelease_sibling.mast\n")
            z.writestr("krelease_sibling.mast", "== krelease_sib ==\n    ->END\n")
        return path

    def _assert_released(self, lib):
        self.assertEqual(mast_mod._lib_zip_cache, {},
                         "compile left a .mastlib handle cached")
        self.assertEqual(mast_mod._compile_depth, 0,
                         "compile scope depth did not unwind")
        # the real test on Windows: an open handle makes this raise PermissionError
        os.unlink(lib)

    def test_import_content_releases_handle(self):
        with tempfile.TemporaryDirectory() as tmp:
            lib = self._make_lib(tmp)
            m = Mast()
            errors = m.import_content("__init__.mast", m, lib)
            self.assertEqual(errors, [], f"import errors: {errors}")
            self._assert_released(lib)

    def test_handle_released_even_when_compile_fails(self):
        # a lib whose entry point is missing: the read fails, the handle still goes
        with tempfile.TemporaryDirectory() as tmp:
            lib = os.path.join(tmp, "kbroken_test.mastlib")
            with zipfile.ZipFile(lib, "w") as z:
                z.writestr("not_the_entry_point.mast", "== nope ==\n    ->END\n")
            m = Mast()
            errors = m.import_content("__init__.mast", m, lib)
            self.assertTrue(errors, "expected a load error for a missing entry point")
            self._assert_released(lib)


if __name__ == "__main__":
    unittest.main(verbosity=2)
