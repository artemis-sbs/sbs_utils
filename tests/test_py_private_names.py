"""A leading underscore in an addon's .py is PRIVATE to that file.

WHAT THIS COST. Every .py of a mission is exec'd into one shared namespace so that a
helper in one file can call a sibling's by bare name. That used to include
underscored names, and because a function's `__globals__` IS that dict, a top-level
`_helper` resolved AT CALL TIME to whichever file loaded last.

LegendaryMissions shipped it: Engineering's View tab called its own `_label` and got
`director/director_overlays.py`'s `_label` - a string sanitizer that returns text and
draws nothing - because director loads later. The tab rendered every other widget
perfectly and simply had no labels. No error, no warning. Four rounds of engine
round-trips to find, and no unit test could see it: a test imports the file as an
ordinary Python module, where the name is that file's own.

    python -m unittest discover -s tests -p "test_py_private_names.py"
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import os
import sys
import tempfile
import unittest
import zipfile

from sbs_utils.mast.mast import Mast
from sbs_utils.mast.mast_globals import MastGlobals

SCOPE = "<test-mission>"


def _load(src, scope=SCOPE, module_name=None):
    """What Mast.import_python does to one .py file, including the sys.modules entry
    that `import sibling` resolves through."""
    ns = MastGlobals.make_py_file_namespace(scope)
    if module_name:
        shared = MastGlobals.get_mission_py_module(scope).__dict__
        sys.modules[module_name] = MastGlobals.FileModule(module_name, ns, shared)
        _LOADED.append(module_name)
    exec(compile(src, "<test>", "exec"), ns)
    MastGlobals.publish_py_file_namespace(scope, ns)
    return ns


#: sys.modules entries a test made, torn down in _Base.
_LOADED = []


class _Base(unittest.TestCase):
    def setUp(self):
        MastGlobals.mission_py_modules.pop(SCOPE, None)

    def tearDown(self):
        MastGlobals.mission_py_modules.pop(SCOPE, None)
        while _LOADED:
            sys.modules.pop(_LOADED.pop(), None)


class AnUnderscoreIsPrivateToItsFile(_Base):
    def test_two_files_keep_their_own_private_helper(self):
        """THE BUG. Both define `_label`; each must call its own."""
        a = _load("def _label(t): return 'A'\ndef a_pub(): return _label(1)\n")
        b = _load("def _label(t): return 'B'\ndef b_pub(): return _label(1)\n")
        self.assertEqual(a["a_pub"](), "A")
        self.assertEqual(b["b_pub"](), "B")

    def test_load_order_does_not_decide_which_wins(self):
        """It used to: last file exec'd owned the name for everybody."""
        b = _load("def _label(t): return 'B'\ndef b_pub(): return _label(1)\n")
        _load("def _label(t): return 'A'\ndef a_pub(): return _label(1)\n")
        self.assertEqual(b["b_pub"](), "B", "a later file stole this file's private")

    def test_a_private_name_is_not_published_to_the_shared_namespace(self):
        _load("def _secret(): return 1\ndef pub(): return 2\n")
        shared = MastGlobals.get_mission_py_module(SCOPE).__dict__
        self.assertNotIn("_secret", shared)
        self.assertIn("pub", shared)

    def test_a_private_name_is_invisible_to_a_sibling(self):
        _load("def _secret(): return 1\n")
        b = _load("def reach(): return _secret()\n")
        with self.assertRaises(NameError):
            b["reach"]()


class PublicNamesStillCrossFiles(_Base):
    """The reason the shared namespace exists - cross-file bare calls, both
    directions, whatever the load order."""

    def test_a_file_can_call_an_earlier_files_public_helper(self):
        _load("def earlier(): return 'earlier'\n")
        b = _load("def use(): return earlier()\n")
        self.assertEqual(b["use"](), "earlier")

    def test_a_file_can_call_a_LATER_files_public_helper(self):
        """Resolution is at CALL time, which is what makes load order irrelevant."""
        a = _load("def use(): return later()\n")
        _load("def later(): return 'later'\n")
        self.assertEqual(a["use"](), "later")

    def test_a_public_name_can_still_be_replaced_by_a_later_file(self):
        """Unchanged, and still worth prefixing against - `sbs lint`'s
        ns-duplicate-function is about exactly this."""
        a = _load("def shared_name(): return 'A'\ndef use(): return shared_name()\n")
        _load("def shared_name(): return 'B'\n")
        self.assertEqual(a["use"](), "B")


class TheFileStillBehavesLikePython(_Base):
    """A dict SUBCLASS as globals takes CPython off its fast builtins path, so every
    builtin lookup goes through the fallback. Measured on the engine's 3.11, where
    `range` raised NameError; 3.14 resolved it without help."""

    def test_builtins_resolve(self):
        ns = _load("def f(): return len(list(range(3)))\n")
        self.assertEqual(ns["f"](), 3)

    def test_comprehensions_see_module_privates(self):
        ns = _load("_S = 'x'\ndef f(): return [_S for _ in range(2)]\n")
        self.assertEqual(ns["f"](), ["x", "x"])

    def test_nested_functions_see_module_privates(self):
        ns = _load("_S = 'x'\ndef f():\n    def g(): return _S\n    return g()\n")
        self.assertEqual(ns["f"](), "x")

    def test_a_class_body_sees_module_privates(self):
        ns = _load("_V = 'v'\nclass K:\n    v = _V\n")
        self.assertEqual(ns["K"].v, "v")

    def test_an_import_inside_the_file_works(self):
        ns = _load("import math\ndef f(): return math.floor(1.7)\n")
        self.assertEqual(ns["f"](), 1)

    def test_a_genuinely_missing_name_still_raises_NameError(self):
        ns = _load("def f(): return nope_not_here()\n")
        with self.assertRaises(NameError):
            ns["f"]()


class TheFileStillRegistersAsAMastGlobal(_Base):
    """A def's `__module__` comes from whatever `__name__` its globals carry, and
    `register_mission_functions` registers only functions whose `__module__` matches
    the SHARED module - that is how it tells a mission's own defs from re-exported
    library ones.

    Giving each file its own globals without carrying that `__name__` over made every
    addon function silently stop being a MAST global: the story still compiled, then
    died at runtime on `name 'lm_eng_crew_items' is not defined`. 15 console tests
    caught it; the unit tests above did not, because they never ask MAST for a name.
    """

    def test_a_public_def_is_registered_as_a_mast_global(self):
        from sbs_utils.mast.mast_globals import MastGlobals as MG
        had = "pub_for_mast" in MG.globals
        try:
            _load("def pub_for_mast(): return 'yes'\n")
            MG.register_mission_functions(MG.get_mission_py_module(SCOPE))
            self.assertIn("pub_for_mast", MG.globals)
            self.assertEqual(MG.globals["pub_for_mast"](), "yes")
        finally:
            if not had:
                MG.globals.pop("pub_for_mast", None)

    def test_a_private_def_is_NOT_registered(self):
        from sbs_utils.mast.mast_globals import MastGlobals as MG
        _load("def _priv_for_mast(): return 'no'\n")
        MG.register_mission_functions(MG.get_mission_py_module(SCOPE))
        self.assertNotIn("_priv_for_mast", MG.globals)


class TheRealImportPath(unittest.TestCase):
    """Driven through `Mast.import_content` on a real .mastlib, NOT through a helper.

    My first version of these called a local `_load()` that set up `sys.modules`
    itself - so it tested the helper, passed against the OLD production binding, and
    proved nothing. The engine caught what it missed. Everything here goes through
    the code the engine runs.
    """

    def _lib(self, tmp, files):
        path = os.path.join(tmp, "kpriv_test.mastlib")
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("__init__.mast",
                       "".join(f"import {n}\n" for n in files))
            for name, src in files.items():
                z.writestr(name, src)
        return path

    def _load_lib(self, files):
        with tempfile.TemporaryDirectory() as tmp:
            m = Mast()
            errors = m.import_content("__init__.mast", m, self._lib(tmp, files))
            self.assertEqual(errors, [], f"import errors: {errors}")
            return m

    def test_two_files_keep_their_own_private_helper(self):
        """THE BUG: LM's Engineering `_label` got the director addon's `_label`."""
        self._load_lib({
            "kp_a.py": "def _label(t): return 'A'\ndef kp_a_pub(): return _label(1)\n",
            "kp_b.py": "def _label(t): return 'B'\ndef kp_b_pub(): return _label(1)\n",
        })
        self.assertEqual(MastGlobals.globals["kp_a_pub"](), "A")
        self.assertEqual(MastGlobals.globals["kp_b_pub"](), "B",
                         "a later file stole this file's private")

    def test_a_public_def_is_still_a_mast_global(self):
        """Per-file globals lose `__module__` unless `__name__` carries over, and
        then EVERY addon function silently stops being a MAST global - the story
        compiles and dies at runtime on `name '...' is not defined`."""
        self._load_lib({"kp_c.py": "def kp_c_pub(): return 'yes'\n"})
        self.assertIn("kp_c_pub", MastGlobals.globals)
        self.assertEqual(MastGlobals.globals["kp_c_pub"](), "yes")

    def test_a_private_def_is_not_a_mast_global(self):
        self._load_lib({"kp_d.py": "def _kp_d_priv(): return 1\n"})
        self.assertNotIn("_kp_d_priv", MastGlobals.globals)

    def test_import_sibling_then_call_its_private(self):
        """THE ENGINE CAUGHT THIS. `casino/bar_content.py` does `import casino_amd`
        then `casino_amd._declare_casino_vocabulary()`; LM died at startup with
        `has no attribute '_declare_casino_vocabulary'`."""
        self._load_lib({
            "kp_sib.py": "def _kp_hidden(): return 'hidden'\n",
            "kp_user.py": ("import kp_sib\n"
                           "def kp_user_pub(): return kp_sib._kp_hidden()\n"),
        })
        self.assertEqual(MastGlobals.globals["kp_user_pub"](), "hidden")

    def test_import_sibling_then_call_its_public(self):
        self._load_lib({
            "kp_sib2.py": "def kp_shown(): return 'shown'\n",
            "kp_user2.py": ("import kp_sib2\n"
                            "def kp_user2_pub(): return kp_sib2.kp_shown()\n"),
        })
        self.assertEqual(MastGlobals.globals["kp_user2_pub"](), "shown")

    def test_a_bare_cross_file_call_still_works(self):
        """The reason the shared namespace exists."""
        self._load_lib({
            "kp_e.py": "def kp_e_helper(): return 'helper'\n",
            "kp_f.py": "def kp_f_pub(): return kp_e_helper()\n",
        })
        self.assertEqual(MastGlobals.globals["kp_f_pub"](), "helper")

    def test_builtins_still_resolve_inside_an_addon_file(self):
        """A dict SUBCLASS as globals takes CPython off its fast builtins path. This
        raised `NameError: range` on the engine's 3.11 while 3.14 was fine."""
        self._load_lib({"kp_g.py": "def kp_g_pub(): return len(list(range(3)))\n"})
        self.assertEqual(MastGlobals.globals["kp_g_pub"](), 3)


if __name__ == "__main__":
    unittest.main()
