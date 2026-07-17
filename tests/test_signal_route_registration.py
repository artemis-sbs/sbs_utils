# Unit test: //signal vs //shared/signal REGISTRATION - the compiler's routing decision behind
# the #1 multiplayer footgun (SIGNAL_ROUTING.md).
#
#   //signal/<name>          -> registers PER CONSOLE  (runs once per connected console + server)
#   //shared/signal/<name>   -> registers SERVER-ONLY  (runs exactly once)
#
# route_label.py injects `signal_register(<name>, <label>, <server>)` into main for each route -
# server=True for //shared/signal, server=False for //signal. The full once-vs-per-console DISPATCH
# is multi-console integration (out of scope for a unit test), but the compile-time server flag IS
# the decision that makes a side-effecting route safe or a footgun, and it belongs here as fast,
# isolated sbs_utils coverage. We read the flag from the compiled call's co_consts.
#
# Run:  python -m unittest tests.test_signal_route_registration
from sbs_utils.mast.mast import Mast
from sbs_utils.agent import clear_shared
from sbs_utils.mast_sbs import story_nodes  # noqa: F401 - registers Cosmos MAST nodes via @mast_node()
from sbs_utils.fs import test_set_exe_dir
import unittest

test_set_exe_dir()


def signal_registrations(code):
    """Compile a story and return {signal_name: server_flag} for every //signal / //shared/signal
    route. The compiler injects `signal_register(name, label, server)` into main; the server bool
    is a constant in that call's compiled code (co_consts)."""
    m = Mast()
    clear_shared()
    errors = m.compile(code, "test", m)
    assert errors == [], errors
    out = {}
    for c in m.labels["main"].cmds:
        if "signal_register" not in str(getattr(c, "line", "")):
            continue
        consts = getattr(getattr(c, "code", None), "co_consts", None) or ()
        # signal_register(name, label, server) -> co_consts starts (name, label, server, ...)
        name = consts[0] if consts and isinstance(consts[0], str) else None
        server = next((x for x in consts if isinstance(x, bool)), None)
        if name is not None:
            out[name] = server
    return out


class TestSignalRouteRegistration(unittest.TestCase):
    def test_signal_registers_per_console(self):
        regs = signal_registrations("\n->END\n\n//signal/alpha\n    ->END\n")
        self.assertIn("alpha", regs)
        self.assertIs(regs["alpha"], False,
                      "//signal must register server=False (runs per console + server)")

    def test_shared_signal_registers_server_only(self):
        regs = signal_registrations("\n->END\n\n//shared/signal/beta\n    ->END\n")
        self.assertIn("beta", regs)
        self.assertIs(regs["beta"], True,
                      "//shared/signal must register server=True (runs server-only, once)")

    def test_both_route_independently_in_one_story(self):
        regs = signal_registrations(
            "\n->END\n\n//signal/alpha\n    ->END\n\n//shared/signal/beta\n    ->END\n")
        self.assertEqual(regs.get("alpha"), False, regs)
        self.assertEqual(regs.get("beta"), True, regs)

    def test_multisegment_shared_signal_uses_first_segment_only(self):
        # The compiler registers a signal route under only the FIRST path segment after
        # shared/signal (route_label.py uses paths[2]); deeper segments are dropped. Signal
        # names are conventionally flat, so the effective behavior is: //shared/signal/build/done
        # registers the "build" signal (still SERVER-ONLY), NOT "build/done". Locked here so the
        # server flag AND this first-segment behavior are both regression-guarded.
        regs = signal_registrations("\n->END\n\n//shared/signal/build/done\n    ->END\n")
        self.assertEqual(regs.get("build"), True, regs)
        self.assertNotIn("build/done", regs)

    def test_multisegment_signal_uses_first_segment_only(self):
        regs = signal_registrations("\n->END\n\n//signal/wave/cleared\n    ->END\n")
        self.assertEqual(regs.get("wave"), False, regs)
        self.assertNotIn("wave/cleared", regs)


if __name__ == "__main__":
    unittest.main()
