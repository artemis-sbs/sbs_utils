"""Regression tests for compile_format_string (mast_node.py).

The old wrapping (f\"\"\"{message}\"\"\") emitted broken code whenever the text
contained a triple quote or ended in a quote. The helper now picks a safe
delimiter and raises a clear error if it truly can't wrap the text.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()
import unittest
from sbs_utils.mast.mast_node import compile_format_string


class TestCompileFormatString(unittest.TestCase):
    def _eval(self, code, **vars):
        return eval(code, {}, vars)

    def test_none_and_plain_passthrough(self):
        self.assertIsNone(compile_format_string(None))
        self.assertEqual(compile_format_string("no braces here"), "no braces here")

    def test_basic_format(self):
        code = compile_format_string("hello {x}")
        self.assertEqual(self._eval(code, x=5), "hello 5")

    def test_embedded_double_quotes(self):
        code = compile_format_string('say "hi" to {who}')
        self.assertEqual(self._eval(code, who="Bob"), 'say "hi" to Bob')

    def test_embedded_triple_quotes(self):
        # Old code produced a SyntaxError here; now it falls back to ''' delim.
        code = compile_format_string('block \"\"\"x\"\"\" {n}')
        self.assertEqual(self._eval(code, n=2), 'block \"\"\"x\"\"\" 2')

    def test_trailing_quote(self):
        code = compile_format_string('value {v}"')
        self.assertEqual(self._eval(code, v=1), 'value 1"')

    def test_mixed_triple_quotes_raises_clear_error(self):
        with self.assertRaises(Exception):
            compile_format_string("a \"\"\" b ''' c {x}")


if __name__ == "__main__":
    unittest.main()
