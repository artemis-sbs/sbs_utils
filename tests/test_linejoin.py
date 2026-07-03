import unittest
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.mast.mast_linejoin import join_bracket_continuations as J


def line_of(src, needle):
    """1-based line number where `needle` appears in src."""
    return src[:src.index(needle)].count("\n") + 1


class TestLineJoin(unittest.TestCase):
    def test_no_brackets_passthrough(self):
        s = "x = 1\ny = 2\n"
        self.assertEqual(J(s), s)

    def test_single_line_unchanged(self):
        s = 'foo(a, b, {"k": 1})\n'
        self.assertEqual(J(s), s)

    def test_multiline_dict_assign_collapses(self):
        s = 'x = {\n  "a": 1,\n  "b": 2\n}\ny = 3\n'
        out = J(s)
        # the dict is now one logical line (no newline between { and })
        logical = out.split("\n")[0]
        self.assertIn('"a": 1', logical)
        self.assertIn('"b": 2', logical)
        self.assertIn("}", logical)

    def test_multiline_func_call_collapses(self):
        s = 'prefab_spawn("fleet", {\n  "race": "skaraan",\n  "n": 3\n})\n'
        out = J(s)
        logical = out.split("\n")[0]
        self.assertIn('"race": "skaraan"', logical)
        self.assertTrue(logical.rstrip().endswith("})"))

    def test_line_numbers_preserved_after_block(self):
        # y must still report as line 5 after a 4-line collapsed dict.
        s = 'x = {\n  "a": 1,\n  "b": 2\n}\ny = 3\n'
        self.assertEqual(line_of(s, "y = 3"), 5)
        out = J(s)
        self.assertEqual(line_of(out, "y = 3"), 5)

    def test_collapsed_expr_compiles_as_python(self):
        s = 'x = {\n  "a": 1,\n  "b": 2\n}\n'
        out = J(s)
        rhs = out.split("\n")[0].split("=", 1)[1].strip()
        self.assertEqual(compile(rhs, "<string>", "eval") and eval(rhs), {"a": 1, "b": 2})

    def test_prose_apostrophe_not_a_string(self):
        # dialogue line with a contraction must be left exactly alone
        s = "== main ==\n% You can't win!\n% Go climb a tree!\n"
        self.assertEqual(J(s), s)

    def test_prose_unbalanced_bracket_does_not_leak(self):
        s = "% I am (thinking\n% next line\nx = 1\n"
        out = J(s)
        # nothing collapsed; x=1 still on its own line
        self.assertEqual(out, s)

    def test_comment_inside_brackets_dropped(self):
        s = 'foo(\n  a,  # explain a\n  b\n)\n'
        out = J(s)
        logical = out.split("\n")[0]
        self.assertNotIn("#", logical)          # comment must not survive on joined line
        self.assertIn("a", logical)
        self.assertIn("b", logical)
        self.assertTrue(logical.rstrip().endswith(")"))

    def test_trailing_comment_at_depth0_kept(self):
        s = "x = 1  # keep me\ny = 2\n"
        self.assertEqual(J(s), s)

    def test_tilde_fence_untouched(self):
        s = 'g = ~~{\n  "x": 1\n}~~\n'
        self.assertEqual(J(s), s)

    def test_triple_quote_block_untouched(self):
        s = 'gui_text("""line one\nline two""")\n'
        self.assertEqual(J(s), s)

    def test_yaml_metadata_fence_untouched(self):
        s = "@map/x \"X\"\nmetadata: ``` yaml\nProperties:\n    A: 'gui(\"{x}\")'\n```\n    y = 1\n"
        self.assertEqual(J(s), s)

    def test_nested_brackets(self):
        s = 'x = foo(\n  bar(\n    1,\n    2\n  ),\n  3\n)\n'
        out = J(s)
        logical = out.split("\n")[0]
        self.assertEqual(eval(logical.split("=", 1)[1].strip(),
                              {"foo": lambda *a: list(a), "bar": lambda *a: sum(a)}),
                         [3, 3])


if __name__ == "__main__":
    unittest.main()
