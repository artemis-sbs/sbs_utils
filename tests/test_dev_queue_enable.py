"""dev_queue_enabled() opt-ins: the COSMOS_DEV_QUEUE env var OR a
dev_queue.enable marker file in the mission dir (so the engine can be launched
normally, no env vars). Inert otherwise.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import os
import tempfile
import unittest

from sbs_utils import fs
from cosmos_dev.devqueue import dev_queue


class TestDevQueueEnable(unittest.TestCase):
    def setUp(self):
        self._env = os.environ.pop("COSMOS_DEV_QUEUE", None)
        self._script_dir = fs.script_dir
        fs.script_dir = tempfile.mkdtemp()   # mission dir get_mission_dir_filename uses

    def tearDown(self):
        if self._env is not None:
            os.environ["COSMOS_DEV_QUEUE"] = self._env
        else:
            os.environ.pop("COSMOS_DEV_QUEUE", None)
        fs.script_dir = self._script_dir

    def test_disabled_by_default(self):
        self.assertFalse(dev_queue.dev_queue_enabled())

    def test_env_var_enables(self):
        os.environ["COSMOS_DEV_QUEUE"] = "1"
        self.assertTrue(dev_queue.dev_queue_enabled())

    def test_env_var_zero_does_not_enable(self):
        os.environ["COSMOS_DEV_QUEUE"] = "0"
        self.assertFalse(dev_queue.dev_queue_enabled())

    def test_marker_file_enables_without_env(self):
        marker = fs.get_mission_dir_filename("dev_queue.enable")
        with open(marker, "w") as f:
            f.write("")
        self.assertTrue(dev_queue.dev_queue_enabled())
        os.remove(marker)
        self.assertFalse(dev_queue.dev_queue_enabled())


if __name__ == "__main__":
    unittest.main()
