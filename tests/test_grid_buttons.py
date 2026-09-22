"""Reading and pressing grid-comms buttons from a console.

`grid_control` is an engine widget a console can only hand a rectangle to: no scroll, no
row height, no styling, and a menu taller than the box is cut off. `comms_grid_buttons` /
`comms_grid_press` let a console draw the same buttons itself.

THE TRAP THESE EXIST FOR: `index` is the position in the UNFILTERED button list. A button
hidden by its `if`, or already used because it is `*`, is skipped when drawing but still
consumes an index - `set_buttons` enumerates before it filters, and the press path looks
the button up by that index. Get this wrong and every press after a hidden button runs
the wrong action, which on Engineering means ordering the wrong repair.

    python -m unittest discover -s tests -p "test_grid_buttons.py"
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

import sbs_utils.mast_sbs.story_nodes  # noqa: F401  (first, to break a circular import)
import cosmos_dev.mock.sbs as mock_sbs

import sys
sys.modules.setdefault("sbs", mock_sbs)

from sbs_utils.procedural import comms as C


class _FakeButton:
    """A `Button` node as far as these functions read one."""

    def __init__(self, message, color=None, code=None, used=False):
        self.message = message
        self.color = color
        self.code = code
        self._used = used

    def should_present(self, id_tuple):
        return not self._used


class _FakeTask:
    """The promise's task - what the conditions and labels are evaluated on."""

    def __init__(self, truths=None):
        self.truths = truths or {}

    def format_string(self, s):
        return s

    def eval_code(self, code):
        return self.truths.get(code, True)


class _FakePromise:
    def __init__(self, buttons, task=None, path="comms/grid"):
        self.expanded_buttons = buttons
        self.task = task or _FakeTask()
        self.path = path


class _Base(unittest.TestCase):
    ORIGIN = 101
    SELECTED = 202

    def setUp(self):
        # A module-level `__name` is NOT mangled (that only happens inside a class
        # body), so the store is reachable by its own name. Asserted rather than
        # guessed: a wrong lookup here would make every test below pass vacuously.
        self.promises = C.__dict__["__comms_promises"]
        self.assertIsInstance(self.promises, dict)
        self.promises.clear()

    def tearDown(self):
        self.promises.clear()

    def open(self, buttons, task=None, path="comms/grid"):
        """Put an interaction in the store, as start_comms_common_selected would."""
        prom = _FakePromise(buttons, task, path)

        class _Task:
            def get_variable(self, name):
                return prom if name == "BUTTON_PROMISE" else None

        self.promises[(self.ORIGIN, self.SELECTED)] = _Task()
        return prom


class TheIndexIsNotTheRow(_Base):
    """The whole reason these accessors exist rather than a console counting rows."""

    def test_a_hidden_button_still_consumes_an_index(self):
        self.open([_FakeButton("first"),
                   _FakeButton("hidden", code="nope"),
                   _FakeButton("third")],
                  task=_FakeTask({"nope": False}))
        rows = C.comms_grid_buttons(self.ORIGIN, self.SELECTED)
        self.assertEqual([r["label"] for r in rows], ["first", "third"])
        self.assertEqual([r["index"] for r in rows], [0, 2],
                         "the row number was used as the index - presses will misfire")

    def test_a_used_one_shot_button_also_consumes_an_index(self):
        self.open([_FakeButton("spent", used=True), _FakeButton("live")])
        rows = C.comms_grid_buttons(self.ORIGIN, self.SELECTED)
        self.assertEqual([(r["label"], r["index"]) for r in rows], [("live", 1)])

    def test_several_hidden_in_a_row(self):
        self.open([_FakeButton("a"),
                   _FakeButton("x", code="no"), _FakeButton("y", code="no"),
                   _FakeButton("b")],
                  task=_FakeTask({"no": False}))
        self.assertEqual([r["index"] for r in C.comms_grid_buttons(self.ORIGIN, self.SELECTED)],
                         [0, 3])


class WhatARowCarries(_Base):
    def test_label_color_and_icon(self):
        self.open([_FakeButton("Fix now", color="red icon:wrench")])
        row = C.comms_grid_buttons(self.ORIGIN, self.SELECTED)[0]
        self.assertEqual((row["label"], row["color"], row["icon"]),
                         ("Fix now", "red", "wrench"))

    def test_no_format_block_is_white_and_iconless(self):
        self.open([_FakeButton("Plain")])
        row = C.comms_grid_buttons(self.ORIGIN, self.SELECTED)[0]
        self.assertEqual((row["color"], row["icon"]), ("white", None))

    def test_an_icon_only_block_keeps_the_default_color(self):
        self.open([_FakeButton("Workout", color="icon:person")])
        row = C.comms_grid_buttons(self.ORIGIN, self.SELECTED)[0]
        self.assertEqual((row["color"], row["icon"]), ("white", "person"))

    def test_a_two_color_format_is_left_alone(self):
        """`=$raider red, white` is an existing convention - comma is spoken for, which
        is why the icon marker is `icon:` and not a comma slot."""
        self.open([_FakeButton("Hail", color="red, white")])
        row = C.comms_grid_buttons(self.ORIGIN, self.SELECTED)[0]
        self.assertEqual((row["color"], row["icon"]), ("red, white", None))

    def test_a_two_color_format_can_still_carry_an_icon(self):
        self.open([_FakeButton("Hail", color="red, white icon:gear")])
        row = C.comms_grid_buttons(self.ORIGIN, self.SELECTED)[0]
        self.assertEqual((row["color"], row["icon"]), ("red, white", "gear"))


class WhenThereIsNothingOpen(_Base):
    def test_no_interaction_is_an_empty_list(self):
        self.assertEqual(C.comms_grid_buttons(self.ORIGIN, self.SELECTED), [])

    def test_an_interaction_with_no_buttons_is_an_empty_list(self):
        self.open([])
        self.assertEqual(C.comms_grid_buttons(self.ORIGIN, self.SELECTED), [])

    def test_every_button_hidden_is_an_empty_list(self):
        self.open([_FakeButton("x", code="no")], task=_FakeTask({"no": False}))
        self.assertEqual(C.comms_grid_buttons(self.ORIGIN, self.SELECTED), [])


class PressingGoesThroughTheDispatcher(_Base):
    """The press must take the same path the engine's own press takes, or one-shot
    buttons stop being marked used and the menu stops redrawing afterwards."""

    def _tap(self):
        from sbs_utils.consoledispatcher import ConsoleDispatcher
        seen = []
        orig = ConsoleDispatcher.dispatch_message
        ConsoleDispatcher.dispatch_message = staticmethod(
            lambda event, console: seen.append((event, console)))
        self.addCleanup(lambda: setattr(ConsoleDispatcher, "dispatch_message", orig))
        return seen

    def test_a_press_dispatches_the_engines_own_event(self):
        self.open([_FakeButton("a"), _FakeButton("b")])
        seen = self._tap()
        self.assertTrue(C.comms_grid_press(self.ORIGIN, self.SELECTED, 1))
        (event, console), = seen
        self.assertEqual(console, "grid_selected_UID")
        self.assertEqual(event.tag, "press_grid_button")
        self.assertEqual(event.origin_id, self.ORIGIN)
        self.assertEqual(event.selected_id, self.SELECTED)
        self.assertEqual(event.sub_tag, "1", "the index must ride in sub_tag as a string")

    def test_the_index_from_a_row_is_what_gets_pressed(self):
        """End to end on the trap: read, then press the row's own index."""
        self.open([_FakeButton("first"),
                   _FakeButton("hidden", code="no"),
                   _FakeButton("third")],
                  task=_FakeTask({"no": False}))
        rows = C.comms_grid_buttons(self.ORIGIN, self.SELECTED)
        seen = self._tap()
        C.comms_grid_press(self.ORIGIN, self.SELECTED, rows[1]["index"])
        self.assertEqual(seen[0][0].sub_tag, "2", "pressed the wrong button")

    def test_an_out_of_range_index_is_refused_not_dispatched(self):
        self.open([_FakeButton("only")])
        seen = self._tap()
        self.assertFalse(C.comms_grid_press(self.ORIGIN, self.SELECTED, 5))
        self.assertFalse(C.comms_grid_press(self.ORIGIN, self.SELECTED, -1))
        self.assertEqual(seen, [])

    def test_pressing_with_nothing_open_is_refused(self):
        seen = self._tap()
        self.assertFalse(C.comms_grid_press(self.ORIGIN, self.SELECTED, 0))
        self.assertEqual(seen, [])

    def test_a_none_index_is_refused(self):
        self.open([_FakeButton("only")])
        self.assertFalse(C.comms_grid_press(self.ORIGIN, self.SELECTED, None))


class TheRevisionTellsAConsoleToRedraw(_Base):
    def test_a_settled_menu_reports_the_same_revision(self):
        self.open([_FakeButton("a")])
        self.assertEqual(C.comms_grid_revision(self.ORIGIN, self.SELECTED),
                         C.comms_grid_revision(self.ORIGIN, self.SELECTED))

    def test_a_button_becoming_hidden_moves_the_revision(self):
        task = _FakeTask({"cond": True})
        self.open([_FakeButton("a"), _FakeButton("b", code="cond")], task=task)
        before = C.comms_grid_revision(self.ORIGIN, self.SELECTED)
        task.truths["cond"] = False
        self.assertNotEqual(C.comms_grid_revision(self.ORIGIN, self.SELECTED), before)

    def test_navigating_to_a_submenu_moves_the_revision(self):
        """The labels can be identical between two paths; the path is part of the
        revision so a submenu with the same words still repaints."""
        prom = self.open([_FakeButton("Back")], path="comms/grid")
        before = C.comms_grid_revision(self.ORIGIN, self.SELECTED)
        prom.path = "comms/grid/dc/work"
        self.assertNotEqual(C.comms_grid_revision(self.ORIGIN, self.SELECTED), before)

    def test_nothing_open_has_a_stable_revision(self):
        self.assertEqual(C.comms_grid_revision(self.ORIGIN, self.SELECTED),
                         C.comms_grid_revision(self.ORIGIN, self.SELECTED))


class TheEngineWidgetIsStillFedCorrectly(_Base):
    """Other consoles and other missions still place `grid_control`. An `icon:` marker
    is for the script renderer and must never reach the widget as a colour."""

    def test_the_icon_marker_is_stripped_from_the_sent_color(self):
        self.assertEqual(C._comms_split_icon("red icon:wrench")[0], "red")

    def test_a_block_that_is_only_an_icon_falls_back_to_white(self):
        color, icon = C._comms_split_icon("icon:person")
        self.assertIsNone(color)
        self.assertEqual(icon, "person")

    def test_an_ordinary_color_is_untouched(self):
        self.assertEqual(C._comms_split_icon("red"), ("red", None))


if __name__ == "__main__":
    unittest.main()
