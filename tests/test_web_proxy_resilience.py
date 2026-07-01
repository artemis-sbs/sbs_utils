"""Always-on proxy: _ensure_armed must (re)arm push whenever the engine is
reachable and tolerate it being down - the basis for running the proxy as a
persistent service, started before any mission and surviving engine restarts.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from cosmos_dev.webproxy.proxy import _ensure_armed, _IS_ARMED_EXPR


class _FakeClient:
    def __init__(self, armed=False, down=False):
        self.armed = armed
        self.down = down
        self.calls = []

    def eval(self, expr, timeout=None):
        self.calls.append(expr)
        if self.down:
            raise TimeoutError("engine down")
        if expr == _IS_ARMED_EXPR:
            return self.armed
        if "set_frames_file" in expr:
            self.armed = True
            return "frames.ndjson"
        return None


class TestEnsureArmed(unittest.TestCase):
    def test_engine_down_returns_false(self):
        c = _FakeClient(down=True)
        self.assertFalse(_ensure_armed(c, "frames.ndjson", was_armed=False))

    def test_engine_up_not_armed_arms_it(self):
        c = _FakeClient(armed=False)
        self.assertTrue(_ensure_armed(c, "frames.ndjson", was_armed=False))
        self.assertTrue(c.armed)
        self.assertTrue(any("set_frames_file" in e for e in c.calls))

    def test_engine_up_already_armed_no_rearm(self):
        c = _FakeClient(armed=True)
        self.assertTrue(_ensure_armed(c, "frames.ndjson", was_armed=True))
        self.assertFalse(any("set_frames_file" in e for e in c.calls))

    def test_restart_detected_when_armed_flips_false(self):
        # After a restart the engine reports not-armed again -> we re-arm.
        c = _FakeClient(armed=False)          # fresh engine process
        self.assertTrue(_ensure_armed(c, "frames.ndjson", was_armed=True))
        self.assertTrue(any("set_frames_file" in e for e in c.calls))


if __name__ == "__main__":
    unittest.main()
