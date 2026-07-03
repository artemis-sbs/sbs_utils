"""Regression: a colon inside a quoted string in an `on ...:` header must not be
mistaken for the block-start colon (e.g. gui_button("Test Upgrades:"))."""
import unittest
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # noqa: F401 (register node types)
from sbs_utils.mast.mast import Mast
from sbs_utils.agent import clear_shared


def compile_ok(src):
    m = Mast()
    clear_shared()
    return m.compile(src, "test", m)


class TestOnChangeColon(unittest.TestCase):
    def test_colon_in_button_label(self):
        src = (
            "== setup ==\n"
            "    on gui_message(gui_button(\"Test Upgrades:\")):\n"
            "        x = 1\n"
            "    await gui()\n"
        )
        self.assertEqual(compile_ok(src), [])

    def test_colon_in_change_expr_string(self):
        src = (
            "== setup ==\n"
            "    on change get_data_set_value(id, \"dock:state\", 0):\n"
            "        y = 2\n"
            "    await gui()\n"
        )
        self.assertEqual(compile_ok(src), [])

    def test_plain_on_change_still_compiles(self):
        src = (
            "== setup ==\n"
            "    on change counter:\n"
            "        counter2 = counter\n"
            "    await gui()\n"
        )
        self.assertEqual(compile_ok(src), [])

    def test_colon_in_await_condition_string(self):
        src = (
            "== setup ==\n"
            "    await signal_next(\"dock:done\")\n"
            "    ->END\n"
        )
        self.assertEqual(compile_ok(src), [])

    def test_colon_in_await_block_condition(self):
        # await <expr>: with a colon inside a quoted arg
        src = (
            "== setup ==\n"
            "    await gui():\n"
            "        * \"Buy: 5 credits\":\n"
            "            x = 1\n"
        )
        self.assertEqual(compile_ok(src), [])


if __name__ == "__main__":
    unittest.main()
