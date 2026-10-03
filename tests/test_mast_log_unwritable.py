"""Compiling must not fail because its log file cannot be created.

`Mast()` opens `mast.compile.log` and `mast.runtime.log` in the mission folder. A tool
that compiles outside a running mission can have a mission folder that resolves inside a
`.mastlib` zip - `sbs lint`'s await check did, for any Open Universe mission whose
`story.mast` contained the word `await` - and the lint run ended in a traceback:

    FileNotFoundError: ...\__lib__\artemis-sbs.OpenUniverse.universe_core.v1.4.0.mastlib\mast.compile.log

    python -m unittest tests.test_mast_log_unwritable
"""
import os
import unittest
from unittest import mock

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # noqa: F401
from sbs_utils import fs
from sbs_utils.mast.mast import Mast
from sbs_utils.procedural.await_lint import await_lint


def _inside_a_zip(name):
    return os.path.join(os.path.dirname(__file__), "no_such.mastlib", name)


class UnwritableLogTests(unittest.TestCase):
    def test_a_compiler_can_still_be_made(self):
        with mock.patch.object(fs, "get_mission_dir_filename", _inside_a_zip):
            Mast()                                   # must not raise

    def test_the_await_check_still_answers(self):
        source = "== a ==\n    await delay_sim(5):\n        log('never')\n    ->END\n"
        with mock.patch.object(fs, "get_mission_dir_filename", _inside_a_zip):
            found = await_lint(content=source)
        self.assertEqual([f.code for f in found], ["await-block-stray-statement"])


if __name__ == "__main__":
    unittest.main()
