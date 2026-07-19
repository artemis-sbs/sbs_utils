"""Live-inspection tests (Phase: Signal Tracer). Prove the InspectionBus + the
signal tap: a mission that emits a signal publishes a typed event, the bus is
inert with no sink, and the tap cleanly restores.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest
from tests.test_mast_debug import build_runner
from cosmos_dev.mast_inspect import InspectionBus, SignalTap, _json_safe

SIG_CODE = """
logger(var="output")
sub_task_schedule(listen)
signal_emit("test_sig", {"say": "hi"})
await delay_test(5)

=== listen
signal_register("test_sig", respond)
yield idle

=== respond
log("got {say}")
yield idle
"""


class TestSignalTap(unittest.TestCase):
    def tearDown(self):
        # Ensure no wrapper lingers on the class between tests.
        from sbs_utils.mast.mast import Mast
        base = getattr(Mast.signal_emit, "_mast_orig", None)
        if base is not None:
            Mast.signal_emit = base

    def test_bus_inert_without_sink(self):
        bus = InspectionBus()
        self.assertFalse(bus.active)
        bus.publish("signal", {"name": "x"})   # no sink -> no-op, no error

    def test_signal_tap_publishes_on_emit(self):
        got = []
        bus = InspectionBus()
        bus.subscribe(got.append)
        tap = SignalTap(bus).install()
        try:
            errors, runner, mast = build_runner(SIG_CODE)
            self.assertEqual(errors, [])
            runner.start_task("main")            # runs main -> emits test_sig
            for _ in range(8):
                runner.tick()
            sigs = [e for e in got if e["kind"] == "signal"]
            self.assertTrue(sigs, "no signal events captured")
            payloads = [e["payload"] for e in sigs]
            hit = next(p for p in payloads if p["name"] == "test_sig")
            self.assertEqual(hit["data"], {"say": "hi"})   # json-safe copy
            self.assertGreaterEqual(hit["routes"], 1)      # the listener registered
            # events carry a monotonic seq
            self.assertEqual([e["seq"] for e in got], sorted(e["seq"] for e in got))
        finally:
            tap.uninstall()

    def test_inert_when_no_sink_even_if_installed(self):
        bus = InspectionBus()                    # not subscribed
        tap = SignalTap(bus).install()
        try:
            errors, runner, mast = build_runner(SIG_CODE)
            runner.start_task("main")
            for _ in range(4):
                runner.tick()
            # nothing to assert on the (empty) sink; the point is it didn't raise
        finally:
            tap.uninstall()

    def test_uninstall_restores(self):
        from sbs_utils.mast.mast import Mast
        original = Mast.signal_emit
        tap = SignalTap(InspectionBus()).install()
        self.assertIsNot(Mast.signal_emit, original)     # patched
        tap.uninstall()
        self.assertIs(Mast.signal_emit, original)        # restored

    def test_json_safe(self):
        self.assertEqual(_json_safe({"a": 1, "b": [1, "x"]}), {"a": 1, "b": [1, "x"]})
        self.assertIsInstance(_json_safe(object()), str)  # non-serializable -> repr


if __name__ == "__main__":
    unittest.main()
