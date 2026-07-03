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


if __name__ == "__main__":
    unittest.main(verbosity=2)
