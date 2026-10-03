"""A stage direction that could not be applied says so in the log everybody reads.

`Action: - quill hails quill_hello` with the scene not registered used to produce no call,
a PASS from the headless run, and an empty `mast.runtime.log` - while the sentence the
author needed went to a logger named `action`, which has no handler.

    python -m unittest tests.test_action_failure_is_said
"""
import logging
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # noqa: F401
from sbs_utils.procedural import amd_action


class _Listen(logging.Handler):
    def __init__(self):
        super().__init__()
        self.lines = []

    def emit(self, record):
        self.lines.append(record.getMessage())


class ActionFailureIsSaidTests(unittest.TestCase):
    def setUp(self):
        self.heard = _Listen()
        log = logging.getLogger("mast.runtime")
        log.addHandler(self.heard)
        self.addCleanup(log.removeHandler, self.heard)

    def test_the_message_reaches_the_runtime_log(self):
        amd_action._action_log("there is no dialogue scene called 'quill_hello'")
        self.assertEqual(self.heard.lines,
                         ["Action: there is no dialogue scene called 'quill_hello'"])

    def test_it_never_raises(self):
        amd_action._action_log(None)
        self.assertEqual(len(self.heard.lines), 1)


if __name__ == "__main__":
    unittest.main()
