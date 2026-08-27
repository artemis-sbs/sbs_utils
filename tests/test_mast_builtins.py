"""Which Python builtins a MAST expression can actually reach.

MAST replaces `__builtins__` with `MastGlobals.globals`, so a name that is not in that
dict is a NameError no matter how ordinary it looks in Python. `bool` and `float` were
the two numeric builtins missing beside `int`, and the failure only ever showed up in a
real run - a mission wrote `bool(x)`, headless never executed that line, and the engine
raised.

Run: python -m unittest tests.test_mast_builtins
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from sbs_utils.mast.mast_globals import MastGlobals
from sbs_utils.mast.mast_node import mast_compile


class MastBuiltinsTests(unittest.TestCase):
    def _eval(self, src):
        """Evaluate one expression exactly the way a MAST node does.

        The shape matters: `{"__builtins__": MastGlobals.globals}` is what
        `mastscheduler._EVAL_GLOBALS` uses. Handing `eval` a plain copy of the table
        instead lets Python quietly insert the REAL builtins behind it, and then every
        assertion below passes whether or not the name is in the table - a test that
        cannot fail. That is how the first draft of this file was wrong.
        """
        code = mast_compile(src, "eval")
        self.assertIsNotNone(code, f"{src!r} did not compile")
        return eval(code, {"__builtins__": MastGlobals.globals}, {})

    def test_bool_and_float_are_reachable(self):
        self.assertIs(self._eval("bool(1)"), True)
        self.assertIs(self._eval("bool(0)"), False)
        self.assertEqual(self._eval("float('2.5')"), 2.5)

    def test_the_numeric_family_is_complete(self):
        # Stated as a family rather than two names: `int` and `str` were always here, and
        # the gap was only visible to someone who tried the other two.
        for name in ("int", "float", "bool", "str", "abs", "min", "max"):
            self.assertIn(name, MastGlobals.globals, f"{name} is not reachable from MAST")

    def test_a_missing_builtin_really_does_raise(self):
        # The guard on the guard: if this ever stops raising, the table has grown a real
        # __builtins__ behind it and these tests stop measuring anything.
        with self.assertRaises(NameError):
            self._eval("compile('1', '<x>', 'eval')")


if __name__ == "__main__":
    unittest.main()
