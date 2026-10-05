"""A line pasted below `->END` never runs, and nothing said so.

The end of a map label looks like the place to add one more line, and `->END` is the last
thing there. A recipe card pasted under it compiled, lint was clean, and the ruin (or the
boarding scene, or the fleet) was simply not in the game.

    python -m unittest tests.test_reach_lint
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.procedural.reach_lint import reach_lint

MAP = '''@map/amd_sample "AMD Sample"
" A short investigation.
    npc_spawn(0, 0, 0, "DS 1", "tsn, station", "starbase_command", "behav_station")
    await task_schedule(spawn_players)
    task_schedule(watch_for_arrival)
    ->END


=== watch_for_arrival
    ->END if not object_exists(hulk_id)
    for p in to_object_list(role("__player__")):
        if sbs.distance_id(p.id, hulk_id) < 2000:
            signal_emit("quest_signal", {"SIGNAL_NAME": "derelict_found"})
            ->END
    await delay_sim(2)
    jump watch_for_arrival
'''


def _lines(text):
    return [(f.line, f.code) for f in reach_lint(content=text)]


class UnreachableTests(unittest.TestCase):
    def test_the_templates_own_story_is_quiet(self):
        self.assertEqual(_lines(MAP), [])

    def test_a_line_pasted_below_the_end(self):
        text = MAP.replace(
            "    ->END\n\n\n=== watch_for_arrival",
            "    ->END\n    relics_spawn(get_mission_dir_filename(\"mission.amd\"))\n\n\n"
            "=== watch_for_arrival")
        self.assertEqual(_lines(text), [(7, "mast-unreachable")])

    def test_only_the_first_dead_line_is_reported(self):
        text = MAP.replace(
            "    ->END\n\n\n=== watch_for_arrival",
            "    ->END\n    one()\n    two()\n    three()\n\n=== watch_for_arrival")
        self.assertEqual(_lines(text), [(7, "mast-unreachable")])

    def test_the_message_names_the_line_that_ended_it(self):
        text = "== a ==\n    ->END\n    never()\n"
        found = reach_lint(content=text)
        self.assertEqual(len(found), 1)
        self.assertIn("line 2", found[0].message)

    def test_a_comment_or_a_blank_line_after_the_end_is_fine(self):
        self.assertEqual(_lines("== a ==\n    ->END\n    # the end\n\n"), [])

    def test_a_conditional_end_falls_through(self):
        self.assertEqual(_lines("== a ==\n    ->END if done\n    more()\n"), [])

    def test_an_end_inside_a_block_does_not_end_the_label(self):
        text = "== a ==\n    if done:\n        ->END\n    more()\n    ->END\n"
        self.assertEqual(_lines(text), [])

    def test_a_dead_line_inside_a_block(self):
        text = "== a ==\n    if done:\n        ->END\n        never()\n    more()\n"
        self.assertEqual(_lines(text), [(4, "mast-unreachable")])

    def test_a_button_block_after_an_end_in_the_one_before(self):
        text = ('//comms\n    + "Hail":\n        hail()\n        ->END\n'
                '    + "Other":\n        other()\n')
        self.assertEqual(_lines(text), [])

    def test_a_new_label_starts_fresh(self):
        text = "== a ==\n    ->END\n--- again\n    more()\n== b ==\n    b()\n"
        self.assertEqual(_lines(text), [])

    def test_the_spaced_spelling(self):
        self.assertEqual(_lines("== a ==\n    -> END\n    never()\n"),
                         [(3, "mast-unreachable")])

    def test_text_in_a_triple_quoted_block_is_not_code(self):
        text = '== a ==\n    ->END\n"""\n    not code\n"""\n'
        self.assertEqual(_lines(text), [])


class ALabelStartsWhereverItIsIndented(unittest.TestCase):
    """A recipe card pasted with four spaces in front of it RUNS (measured in the mock,
    Lecture 11's re-measure), and this check said its first line never would: it took the
    route line for one more line of the label that had just ended."""

    MAP = "== setup ==\n    place()\n    ->END\n"

    def test_an_indented_route_is_a_new_label(self):
        text = self.MAP + "    //shared/signal/quest_started\n        tug()\n        ->END\n"
        self.assertEqual(_lines(text), [])

    def test_only_the_route_line_indented(self):
        text = self.MAP + "    //shared/signal/quest_started\n    tug()\n    ->END\n"
        self.assertEqual(_lines(text), [])

    def test_an_indented_label_and_an_indented_map(self):
        self.assertEqual(_lines(self.MAP + "    == later ==\n    more()\n"), [])
        self.assertEqual(_lines(self.MAP + '    @map/second "Second"\n    more()\n'), [])

    def test_a_dead_line_after_the_indented_card_is_still_found(self):
        text = (self.MAP + "    //shared/signal/quest_started\n        tug()\n"
                "        ->END\n        late()\n")
        self.assertEqual(_lines(text), [(7, "mast-unreachable")])

    def test_the_advice_names_both_causes(self):
        found = reach_lint(content="== a ==\n    ->END\n    never()\n")
        self.assertIn("move it above line 2", found[0].message)
        self.assertIn("pasted INTO a label", found[0].message)


if __name__ == "__main__":
    unittest.main()
