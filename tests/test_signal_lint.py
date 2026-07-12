"""Unit tests for signal_lint: side-effects in a //signal route are flagged; //shared/signal
and display-only //signal routes are not."""
import unittest
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()
from sbs_utils.procedural.signal_lint import signal_lint


def codes(src):
    return [f.code for f in signal_lint(content=src)]


class SignalLintTests(unittest.TestCase):
    def test_flags_spawn_in_signal_route(self):
        src = "//signal/boss_time\n    prefab_spawn(prefab_fleet_raider, {})\n"
        self.assertEqual(codes(src), ["signal-side-effect-spawn"])

    def test_flags_modifier_and_random(self):
        src = ("//signal/buy\n"
               "    if random.randint(1, 2) == 1:\n"
               "        modifier_add(role(\"__player__\"), \"x\", 1.0, \"k\")\n")
        self.assertIn("signal-side-effect-random", codes(src))
        self.assertIn("signal-side-effect-modifier", codes(src))

    def test_flags_quest_and_save(self):
        src = ("//signal/done\n"
               "    quest_mark_complete(AGENT_ID, QUEST_ID)\n"
               "    universe_save(seed, i, j, systems)\n")
        self.assertEqual(set(codes(src)),
                         {"signal-side-effect-quest", "signal-side-effect-save"})

    def test_shared_signal_is_not_flagged(self):
        src = "//shared/signal/boss_time\n    prefab_spawn(prefab_fleet_raider, {})\n"
        self.assertEqual(codes(src), [])

    def test_display_only_signal_is_clean(self):
        src = ("//signal/show_results\n"
               "    gui_text(\"$text:Game Over\")\n"
               "    comms_broadcast(role(\"__player__\"), \"done\")\n")
        self.assertEqual(codes(src), [])

    def test_route_boundary_scopes_the_body(self):
        # The spawn belongs to a following non-signal route, NOT the //signal one.
        src = ("//signal/ping\n"
               "    gui_text(\"hi\")\n"
               "//spawn\n"
               "    npc_spawn(0, 0, 0, \"x\", \"r\", \"a\", \"behav_npcship\")\n")
        self.assertEqual(codes(src), [])

    def test_comment_line_is_ignored(self):
        src = "//signal/ping\n    # prefab_spawn(...) would be wrong here\n    gui_text(\"hi\")\n"
        self.assertEqual(codes(src), [])


if __name__ == "__main__":
    unittest.main()
