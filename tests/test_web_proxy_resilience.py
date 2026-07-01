"""Always-on proxy: _ensure_armed must (re)arm push whenever the engine is
reachable and tolerate it being down - the basis for running the proxy as a
persistent service, started before any mission and surviving engine restarts.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from cosmos_dev.webproxy.proxy import (_ensure_armed, _IS_ARMED_EXPR,
                                       _Engine, _resolve_engine)


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


class TestResolveEngine(unittest.TestCase):
    def _engines(self, *specs):
        eng = [_Engine(n, d) for n, d in specs]
        by_name = {e.name: e for e in eng if e.name}
        named = [e for e in eng if not e.name]
        default = named[0] if named else (eng[0] if len(eng) == 1 else None)
        return by_name, default

    def test_single_default_no_prefix(self):
        by_name, default = self._engines(("", "dirA"))
        e, page = _resolve_engine("scores", by_name, default)
        self.assertIs(e, default)
        self.assertEqual(page, "scores")

    def test_named_engine_prefix_routes_and_strips(self):
        by_name, default = self._engines(("alpha", "dirA"), ("beta", "dirB"))
        e, page = _resolve_engine("alpha/scores", by_name, default)
        self.assertEqual(e.name, "alpha")
        self.assertEqual(page, "scores")

    def test_single_named_engine_is_default_too(self):
        by_name, default = self._engines(("alpha", "dirA"))
        # both /web/scores and /web/alpha/scores reach it
        e1, p1 = _resolve_engine("scores", by_name, default)
        e2, p2 = _resolve_engine("alpha/scores", by_name, default)
        self.assertIs(e1, default)
        self.assertEqual(p1, "scores")
        self.assertEqual(e2.name, "alpha")
        self.assertEqual(p2, "scores")

    def test_unknown_prefix_multi_engine_has_no_default(self):
        by_name, default = self._engines(("alpha", "dirA"), ("beta", "dirB"))
        e, page = _resolve_engine("gamma/scores", by_name, default)
        self.assertIsNone(e)          # no nameless default among many
        self.assertEqual(page, "gamma/scores")

    def test_nested_page_path(self):
        by_name, default = self._engines(("alpha", "dirA"))
        e, page = _resolve_engine("alpha/admin/panel", by_name, default)
        self.assertEqual(e.name, "alpha")
        self.assertEqual(page, "admin/panel")


if __name__ == "__main__":
    unittest.main()
