"""A plain statement directly inside an `await ...:` block is WARNED about.

The block exists for inline choices - `+`/`*` buttons, `=` inline labels and `on`
handlers, which attach to the await - and the runtime resumes at the block's end, so any
other line there compiles and never runs:

    await p:
        print("done")      # never executed, no error

It is a compile WARNING rather than an error on purpose: a story that compiled before must
still compile (MAST backward compatibility), and an error takes a whole story to 0 labels.
Surveyed 2026-09-18: 102 await blocks across every mission on the dev machine, and the only
hits were an obsolete, un-imported modding_tools file and an old-syntax test fixture.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.mast.mast import Mast
from sbs_utils.agent import clear_shared
from sbs_utils.mast_sbs import story_nodes  # noqa: F401  registers button/route nodes


def compile_mast(code):
    mast = Mast()
    clear_shared()
    errors = mast.compile(code, "test", mast)
    return errors, getattr(mast, "compile_warnings", [])


class TestStrayStatementInAwaitBlock(unittest.TestCase):

    def test_A_STRAY_STATEMENT_IS_WARNED(self):
        errors, warns = compile_mast(
            "== start ==\n"
            "    await delay_sim(1):\n"
            "        x = 1\n"
            "    ->END\n")
        self.assertEqual([], errors, "must still compile - backward compatibility")
        self.assertEqual(1, len(warns), warns)
        self.assertIn("NEVER RUN", warns[0])
        self.assertIn("x = 1", warns[0])

    def test_buttons_and_their_bodies_are_fine(self):
        errors, warns = compile_mast(
            "== start ==\n"
            "    await gui():\n"
            "        + \"Go\":\n"
            "            x = 1\n"
            "            log(\"pressed\")\n"
            "        * \"Once\":\n"
            "            y = 2\n"
            "    ->END\n")
        self.assertEqual([], errors)
        self.assertEqual([], warns)

    def test_inline_labels_and_on_handlers_are_fine(self):
        errors, warns = compile_mast(
            "== start ==\n"
            "    await delay_sim(1):\n"
            "        =timeout:\n"
            "            x = 1\n"
            "    ->END\n")
        self.assertEqual([], errors)
        self.assertEqual([], warns)

    def test_a_statement_AFTER_the_block_is_fine(self):
        errors, warns = compile_mast(
            "== start ==\n"
            "    await delay_sim(1):\n"
            "        + \"Go\":\n"
            "            x = 1\n"
            "    y = 2\n"
            "    ->END\n")
        self.assertEqual([], errors)
        self.assertEqual([], warns)

    def test_a_bare_await_has_no_block(self):
        errors, warns = compile_mast("== start ==\n    await delay_sim(1)\n    x = 1\n    ->END\n")
        self.assertEqual([], errors)
        self.assertEqual([], warns)


if __name__ == "__main__":
    unittest.main()
