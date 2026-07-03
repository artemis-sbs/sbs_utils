"""End-to-end: does a multiline python expression actually COMPILE through the
real MAST parser now (it did not before the pre-pass)?"""
import unittest
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # noqa: F401  (register node types)
from sbs_utils.mast.mast import Mast
from sbs_utils.agent import clear_shared


def compile_ok(src):
    m = Mast()
    clear_shared()
    return m.compile(src, "test", m)


class TestMultilineCompile(unittest.TestCase):
    def test_multiline_dict_assign(self):
        src = (
            "== setup ==\n"
            "    d = {\n"
            '        "race": "skaraan",\n'
            '        "n": 3\n'
            "    }\n"
            "    ->END\n"
        )
        self.assertEqual(compile_ok(src), [])

    def test_multiline_func_call(self):
        src = (
            "== setup ==\n"
            '    prefab_spawn("prefab_fleet_raider", {\n'
            '        "race": "skaraan",\n'
            '        "fleet_difficulty": 2,\n'
            '        "START_X": 100\n'
            "    })\n"
            "    ->END\n"
        )
        self.assertEqual(compile_ok(src), [])

    def test_multiline_list(self):
        src = (
            "== setup ==\n"
            "    xs = [\n"
            "        1,\n"
            "        2,\n"
            "        3\n"
            "    ]\n"
            "    ->END\n"
        )
        self.assertEqual(compile_ok(src), [])

    def test_multiline_if_condition(self):
        src = (
            "== setup ==\n"
            "    a = 1\n"
            "    b = 2\n"
            "    if (a == 1 and\n"
            "        b == 2):\n"
            "        c = 3\n"
            "    ->END\n"
        )
        self.assertEqual(compile_ok(src), [])

    def test_multiline_nested_call_in_call(self):
        src = (
            "== setup ==\n"
            "    v = Vec3.rand_in_sphere(\n"
            "        3000,\n"
            "        5000,\n"
            "        False\n"
            "    )\n"
            "    ->END\n"
        )
        self.assertEqual(compile_ok(src), [])

    def test_error_line_number_is_accurate(self):
        # a genuine python error on the line AFTER a 4-line multiline dict must
        # still report line 7, not a drifted number.
        src = (
            "== setup ==\n"          # 1
            "    d = {\n"            # 2
            '        "a": 1,\n'      # 3
            '        "b": 2\n'       # 4
            "    }\n"                # 5
            "    x = 1\n"            # 6
            "    y = )bad(\n"        # 7  <- syntax error here
            "    ->END\n"           # 8
        )
        errors = compile_ok(src)
        self.assertTrue(errors, "expected a compile error")
        self.assertIn("Line 7", "".join(errors))


if __name__ == "__main__":
    unittest.main()
