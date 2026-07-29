"""`log()` - the library's own logging call.

    python -m unittest tests.test_execution_log
"""
import logging
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.procedural.execution import log


class Recorder(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)


class LoggingAtALevel(unittest.TestCase):
    """`logging.getLevelNamesMapping` is a FUNCTION. Calling `.get` on the function
    itself raised AttributeError, so every `log(msg, name, "warning")` in the library
    crashed its CALLER - the opposite of what a warning is for, and hidden because the
    only callers are on paths that are supposed to be rare."""

    def setUp(self):
        self.logger = logging.getLogger("test_execution_log")
        self.logger.setLevel(logging.DEBUG)
        self.handler = Recorder()
        self.logger.addHandler(self.handler)

    def tearDown(self):
        self.logger.removeHandler(self.handler)

    def test_a_named_level_does_not_raise(self):
        log("careful", "test_execution_log", "warning")
        self.assertEqual([r.levelno for r in self.handler.records], [logging.WARNING])

    def test_levels_are_case_insensitive(self):
        log("shout", "test_execution_log", "ERROR")
        self.assertEqual(self.handler.records[0].levelno, logging.ERROR)

    def test_no_level_still_means_debug(self):
        log("quiet", "test_execution_log")
        self.assertEqual(self.handler.records[0].levelno, logging.DEBUG)

    def test_a_level_nobody_defines_still_logs_the_message(self):
        """A typo in a level is not a reason to lose the message - or to take out the
        code that was trying to report something."""
        log("odd", "test_execution_log", "not-a-real-level")
        self.assertEqual([r.getMessage() for r in self.handler.records], ["odd"])


if __name__ == "__main__":
    unittest.main()
