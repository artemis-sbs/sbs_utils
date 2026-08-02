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


class ReEmissionLintTests(unittest.TestCase):
    """The second axis: //shared/signal fixes WHERE a route runs, not HOW MANY TIMES
    the signal is emitted. See SIGNAL_ROUTING.md."""

    def test_flags_unkeyed_spawn_in_a_shared_init_route(self):
        src = ("//shared/signal/create_player_ships\n"
               "    player_spawn(0, 0, 0, \"A\", \"tsn\", \"hull\")\n")
        self.assertEqual(codes(src), ["signal-init-unkeyed-spawn"])

    def test_keyed_create_is_the_fix_not_the_bug(self):
        src = ("//shared/signal/create_player_ships\n"
               "    player_ensure(0, 0, 0, 0, \"hull\")\n")
        self.assertEqual(codes(src), [])

    def test_side_prefab_counts_as_a_keyed_create(self):
        # A side is keyed by definition (one agent per key) and re-declaring is a REPAIR,
        # so create_sides spawning side prefabs is correct, not a duplication risk.
        src = ("//shared/signal/create_sides\n"
               "    prefab_spawn(prefab_side_generic, data={\"key\":\"tsn\"})\n")
        self.assertEqual(codes(src), [])

    def test_a_ship_prefab_in_an_init_route_is_still_flagged(self):
        src = ("//shared/signal/create_fleet\n"
               "    prefab_spawn(prefab_fleet_raider, {})\n")
        self.assertEqual(codes(src), ["signal-init-unkeyed-spawn"])

    def test_per_item_emit_in_a_loop_is_normal(self):
        # Emitting a per-item signal from a loop is a correct pattern; only INIT-shaped
        # names are flagged.
        src = ("=== award\n"
               "    for q in quests:\n"
               "        signal_emit(\"quest_signal\", q)\n")
        self.assertEqual(codes(src), [])

    def test_once_guarded_init_route_is_not_flagged(self):
        src = ("//shared/signal/create_player_ships once\n"
               "    player_spawn(0, 0, 0, \"A\", \"tsn\", \"hull\")\n")
        self.assertEqual(codes(src), [])

    def test_non_init_shared_route_is_not_flagged(self):
        # Only init-shaped names; a shared route that spawns on purpose is normal.
        src = ("//shared/signal/wave_incoming\n"
               "    npc_spawn(0, 0, 0, \"x\", \"r\", \"a\", \"behav_npcship\")\n")
        self.assertEqual(codes(src), [])

    def test_flags_emit_inside_a_loop(self):
        src = ("=== create_default_player_ships\n"
               "    for d in SETTINGS.get(\"PLAYER_LIST\"):\n"
               "        signal_emit(\"create_player_ships\", None)\n")
        self.assertEqual(codes(src), ["signal-emit-in-loop"])

    def test_emit_after_the_loop_is_clean(self):
        src = ("=== create_default_player_ships\n"
               "    for d in SETTINGS.get(\"PLAYER_LIST\"):\n"
               "        player_ensure(0, 0, 0, 0, \"hull\")\n"
               "    signal_emit(\"create_player_ships\", None)\n")
        self.assertEqual(codes(src), [])

    def test_loop_state_does_not_leak_past_a_route_boundary(self):
        src = ("=== setup\n"
               "    for d in xs:\n"
               "        log(\"x\")\n"
               "//signal/ping\n"
               "    signal_emit(\"other\")\n")
        self.assertEqual(codes(src), [])


class SignalLintProjectTests(unittest.TestCase):
    """Whole-mission checks a single file cannot see."""

    ROUTE = ("//shared/signal/create_player_ships\n"
             "    player_spawn(0, 0, 0, \"A\", \"tsn\", \"hull\")\n")

    def test_flags_a_risky_init_signal_emitted_from_two_files(self):
        from sbs_utils.procedural.signal_lint import signal_lint_project
        found = signal_lint_project([
            ("routes.mast", self.ROUTE),
            ("a.mast", "== go ==\n    signal_emit(\"create_player_ships\")\n"),
            ("b.mast", "== go2 ==\n    signal_emit(\"create_player_ships\")\n"),
        ])
        self.assertEqual({f.code for _, f in found}, {"signal-multi-emit"})
        self.assertEqual({path for path, _ in found}, {"a.mast", "b.mast"})

    def test_single_emit_is_clean(self):
        from sbs_utils.procedural.signal_lint import signal_lint_project
        found = signal_lint_project([
            ("routes.mast", self.ROUTE),
            ("a.mast", "== go ==\n    signal_emit(\"create_player_ships\")\n"),
        ])
        self.assertEqual(found, [])

    def test_idempotent_handler_makes_multiple_emits_fine(self):
        from sbs_utils.procedural.signal_lint import signal_lint_project
        found = signal_lint_project([
            ("routes.mast", "//shared/signal/create_player_ships\n"
                            "    player_ensure(0, 0, 0, 0, \"hull\")\n"),
            ("a.mast", "== go ==\n    signal_emit(\"create_player_ships\")\n"),
            ("b.mast", "== go2 ==\n    signal_emit(\"create_player_ships\")\n"),
        ])
        self.assertEqual(found, [])


if __name__ == "__main__":
    unittest.main()


class TestLintAllowDirective(unittest.TestCase):
    """`# lint: allow` - because a rule that cannot see a guard must not be unarguable.

    show_game_results schedules its save once per console, which is exactly what the
    ticker rule describes - but the scheduled task guards itself with a shared flag, so
    it writes once. A linter with no way to say "this one is fine" gets ignored wholesale.
    """

    def _codes(self, src):
        from sbs_utils.procedural.signal_lint import signal_lint
        return [f.code for f in signal_lint(content=src)]

    def test_without_a_directive_it_flags(self):
        self.assertEqual(self._codes("//signal/x\n    task_schedule(t)\n"),
                         ["signal-side-effect-ticker"])

    def test_a_named_code_is_excused(self):
        self.assertEqual(
            self._codes("//signal/x\n    # lint: allow signal-side-effect-ticker\n"
                        "    task_schedule(t)\n"), [])

    def test_a_bare_allow_excuses_everything_on_that_line(self):
        self.assertEqual(
            self._codes("//signal/x\n    # lint: allow\n    task_schedule(t)\n"), [])

    def test_a_different_code_still_flags(self):
        self.assertEqual(
            self._codes("//signal/x\n    # lint: allow signal-emit-in-loop\n"
                        "    task_schedule(t)\n"), ["signal-side-effect-ticker"])

    def test_it_excuses_exactly_one_line(self):
        self.assertEqual(
            self._codes("//signal/x\n    # lint: allow\n    task_schedule(a)\n"
                        "    task_schedule(b)\n"), ["signal-side-effect-ticker"])
