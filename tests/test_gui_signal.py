"""A control can emit a signal: `gui_signal(widget, name)` and `signal=` on the builders.

Driven through a real StoryPage compiled from MAST, clicked the way the engine sends
a click, and received by real `//signal` / `//shared/signal` routes - so a green run
here means the payload reached a route, not that a callback was attached.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

import cosmos_dev.mock.sbs as sbs
from sbs_utils.mast.maststory import MastStory
from sbs_utils.mast_sbs import story_nodes  # noqa: F401  (registers route/gui nodes)
from sbs_utils.mast_sbs.maststorypage import StoryPage
from sbs_utils.mast.mastscheduler import MastScheduler
from sbs_utils.mast.mast_globals import MastGlobals
from sbs_utils.agent import clear_shared
from sbs_utils.gui import Gui
from sbs_utils.helpers import FrameContext, Context, FakeEvent, props_display_text
from sbs_utils.procedural.gui.message import dead_handler_sites_clear

CID = 0   # the server console: main (where routes register) runs there first
HITS = []


def gsig_hit(*what):
    HITS.append(what)


MastGlobals.import_python_function(gsig_hit)


def _indent_screen(code):
    """Indent the screen (everything before the first route) under a label."""
    screen, sep, routes = code.partition("\n//")
    body = "\n".join("    " + ln if ln.strip() else ln for ln in screen.splitlines())
    return body + (sep + routes if sep else "")


class GuiSignalPage(StoryPage):
    story = None


class _Base(unittest.TestCase):
    def tearDown(self):
        if hasattr(self, "_orig_rte"):
            MastScheduler.on_runtime_error = self._orig_rte
        Gui.clients = {}
        Gui.widget_list_sent = {}
        GuiSignalPage.story = None
        FrameContext.task = None
        FrameContext.page = None
        FrameContext.mast = None
        FrameContext.context = None
        HITS.clear()

    def start(self, code):
        HITS.clear()
        dead_handler_sites_clear()
        clear_shared()
        Gui.clients = {}
        Gui.widget_list_sent = {}
        sbs.create_new_sim()
        sbs.resume_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(0, "test"))
        story = MastStory()
        # A //signal route registers by a command appended to MAIN, so a screen
        # written as top-level code would reach `await gui()` before any route
        # registered. The screen goes in a label that main (now only the
        # registrations) falls into.
        code = "== gsig_screen ==\n" + _indent_screen(code) + "\n"
        errors = story.compile(code, "gui_signal", story)
        self.assertEqual(errors, [], f"compile errors: {errors}")
        story.compiler_errors = []
        GuiSignalPage.story = story
        FrameContext.mast = story
        self.errors = []
        self._orig_rte = MastScheduler.on_runtime_error
        MastScheduler.on_runtime_error = self.errors.append
        self.page = GuiSignalPage()
        Gui.push(CID, self.page)
        self.present(3)

    def present(self, n=1):
        for _ in range(n):
            sbs.sim._time_tick_counter += 30
            self.page.present(FakeEvent(CID, "gui_present"))

    def item_showing(self, text):
        want = text.strip().lower()
        for tag, entry in list(self.page.tag_map.items()):
            item = entry[0] if isinstance(entry, tuple) and entry else entry
            shown = props_display_text(getattr(item, "value", None)) or \
                props_display_text(getattr(item, "message", None))
            if shown and shown.strip().lower() == want:
                return tag, item
        self.fail(f"no widget showing {text!r}")

    def dispatch(self, tag, **kw):
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(CID, "gui_message"))
        Gui.on_message(FakeEvent(client_id=CID, tag="gui_message", sub_tag=tag, **kw))
        self.present(1)


HEAD = 'gui_section("area: 5,5,95,95;")\ngui_row()\n'


class TestButtonSignal(_Base):
    def test_press_reaches_a_shared_signal_route_with_its_data(self):
        self.start(HEAD + """gui_button("Press", data={"which": "alpha"}, signal="gsig_pressed")
await gui()

//shared/signal/gsig_pressed
    gsig_hit("shared", which, SIGNAL_CLIENT_ID, SIGNAL_VALUE)
""")
        tag, _ = self.item_showing("Press")
        self.dispatch(tag)
        self.assertIn(("shared", "alpha", CID, None), HITS)
        self.assertEqual(self.errors, [])

    def test_signal_runs_alongside_on_press(self):
        self.start(HEAD + """b = gui_button("Press", signal="gsig_pressed")
on gui_message(b):
    gsig_hit("block")
await gui()

//shared/signal/gsig_pressed
    gsig_hit("signal")
""")
        tag, _ = self.item_showing("Press")
        self.dispatch(tag)
        self.assertIn(("block",), HITS)
        self.assertIn(("signal",), HITS)

    def test_a_click_elsewhere_does_not_emit(self):
        self.start(HEAD + """gui_button("Press", signal="gsig_pressed")
gui_button("Other")
await gui()

//shared/signal/gsig_pressed
    gsig_hit("signal")
""")
        tag, _ = self.item_showing("Other")
        self.dispatch(tag)
        self.assertEqual(HITS, [])

    def test_each_press_emits_again(self):
        self.start(HEAD + """gui_button("Press", signal="gsig_pressed")
await gui()

//shared/signal/gsig_pressed
    gsig_hit("signal")
""")
        tag, _ = self.item_showing("Press")
        self.dispatch(tag)
        self.dispatch(tag)
        self.assertEqual(HITS.count(("signal",)), 2)


class TestValueControls(_Base):
    def test_checkbox_sends_its_new_state(self):
        self.start(HEAD + """gui_checkbox("Shields", signal="gsig_shields")
await gui()

//shared/signal/gsig_shields
    gsig_hit("cb", SIGNAL_VALUE)
""")
        tag = next(t for t, e in self.page.tag_map.items()
                   if type(e[0]).__name__ == "Checkbox")
        self.dispatch(tag)
        self.dispatch(tag)
        self.assertEqual(HITS, [("cb", True), ("cb", False)])

    def test_dropdown_sends_the_selection(self):
        self.start(HEAD + """gui_drop_down("text:Slow;list:Slow,Fast;", signal="gsig_speed")
await gui()

//shared/signal/gsig_speed
    gsig_hit("dd", SIGNAL_VALUE)
""")
        tag, _ = self.item_showing("Slow")
        self.dispatch(tag, value_tag="Fast")
        self.assertEqual(HITS, [("dd", "Fast")])

    def test_cycle_button_sends_the_new_state(self):
        self.start(HEAD + """gui_cycle_button("icons,circles", value="icons", signal="gsig_rooms")
await gui()

//shared/signal/gsig_rooms
    gsig_hit("cyc", SIGNAL_VALUE)
""")
        tag = next(t for t, e in self.page.tag_map.items()
                   if type(e[0]).__name__ == "CycleButton")
        self.dispatch(tag)
        self.assertEqual(HITS, [("cyc", "circles")])

    def test_gui_signal_on_an_existing_widget(self):
        self.start(HEAD + """b = gui_button("Press")
gui_signal(b, "gsig_pressed", {"n": 3})
await gui()

//shared/signal/gsig_pressed
    gsig_hit("sig", n)
""")
        tag, _ = self.item_showing("Press")
        self.dispatch(tag)
        self.assertEqual(HITS, [("sig", 3)])


class TestListboxSignal(_Base):
    def test_row_click_sends_the_selection(self):
        self.start(HEAD + """gui_list_box(["alpha", "beta"], "row-height:2em;", select=True, signal="gsig_row")
await gui()

//shared/signal/gsig_row
    gsig_hit("lb", SIGNAL_VALUE)
""")
        lb = next(e[0] for t, e in self.page.tag_map.items()
                  if type(e[0]).__name__ == "LayoutListbox")
        self.dispatch(f"{lb.tag_prefix}:1:__click")
        self.assertEqual(HITS, [("lb", "beta")])


# ---------------------------------------------------------------------------
# Choices in a text area
# ---------------------------------------------------------------------------

STORY = "The hatch is open.^[Go left](signal://gsig_pick?way=left)^[Go right](signal://gsig_pick?way=right)"


class TestTextAreaChoices(_Base):
    def area(self):
        from sbs_utils.pages.layout.text_area import TextArea
        for layout in self.page.layouts:
            stack = [layout]
            while stack:
                node = stack.pop()
                if isinstance(node, TextArea):
                    return node
                stack.extend(getattr(node, "rows", None) or [])
                stack.extend(getattr(node, "columns", None) or [])
        self.fail("no text area on the page")

    def test_a_group_is_one_line_of_chips(self):
        from sbs_utils.pages.layout.text_area import ChoiceFlowLine
        self.start(HEAD + f'gui_text_area("{STORY}")\nawait gui()\n')
        ta = self.area()
        flows = [ln for ln in ta.lines if isinstance(ln, ChoiceFlowLine)]
        self.assertEqual(len(flows), 1)
        self.assertEqual([c[4]["display"] for c in flows[0].chips], ["Go left", "Go right"])
        self.assertEqual(len(ta._choice_map), 2)

    def test_click_emits_consumes_and_the_route_continues_the_story(self):
        self.start(HEAD + f'gui_text_area("{STORY}")\nawait gui()\n' + """
//shared/signal/gsig_pick
    gsig_hit("pick", way, SIGNAL_CHOICE)
    gui_text_area_append(SIGNAL_ITEM, "You went " + way + ".")
""")
        ta = self.area()
        right = next(t for t, c in ta._choice_map.items() if c["display"] == "Go right")
        self.dispatch(right)
        self.assertEqual(HITS, [("pick", "right", "Go right")])
        self.assertEqual(self.errors, [])
        text = "\n".join(ta.content)
        self.assertIn("[Go right](chosen://gsig_pick)", text)
        self.assertNotIn("Go left", text)
        self.assertTrue(text.endswith("You went right."))
        self.assertEqual(ta._choice_map, {})

    def test_a_second_click_on_a_used_group_does_nothing(self):
        self.start(HEAD + f'gui_text_area("{STORY}")\nawait gui()\n' + """
//shared/signal/gsig_pick
    gsig_hit("pick", way)
""")
        ta = self.area()
        tags = list(ta._choice_map)
        self.dispatch(tags[0])
        self.dispatch(tags[1])
        self.assertEqual(HITS, [("pick", "left")])

    def test_appended_choices_are_live(self):
        self.start(HEAD + f'gui_text_area("{STORY}")\nawait gui()\n' + """
//shared/signal/gsig_pick
    gsig_hit("pick", way)
    gui_text_area_append(SIGNAL_ITEM, "A door.^[Open it](signal://gsig_pick?way=door)")
""")
        ta = self.area()
        self.dispatch(next(iter(ta._choice_map)))
        door = next(t for t, c in ta._choice_map.items() if c["display"] == "Open it")
        self.dispatch(door)
        self.assertEqual(HITS, [("pick", "left"), ("pick", "door")])
        self.assertEqual("\n".join(ta.content).count("chosen://"), 2)


class TestChoicePacking(unittest.TestCase):
    """The wrap panel, in pixels, without a page."""

    def setUp(self):
        # Text is measured through the (mock) engine.
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(0, "test"))

    def tearDown(self):
        FrameContext.context = None

    def pack(self, labels, width, **opts):
        from sbs_utils.pages.layout.text_area import ChoiceFlowLine
        o = dict(ChoiceFlowLine.DEFAULTS, **opts)
        return ChoiceFlowLine.pack([{"display": s} for s in labels], width, o)

    def test_short_labels_share_a_row_when_wide(self):
        chips = self.pack(["Yes", "No", "Maybe"], 2000)
        self.assertEqual({c[1] for c in chips}, {0})

    def test_they_wrap_when_narrow(self):
        chips = self.pack(["Kneel by the body", "Check the console", "Leave"], 150)
        self.assertEqual(len({c[1] for c in chips}), 3)

    def test_rows_fill_before_wrapping(self):
        from sbs_utils.pages.layout.measure import measure_line_width
        from sbs_utils.pages.layout.text_area import ChoiceFlowLine
        w = measure_line_width("gui-2", "Alpha") + 24 + ChoiceFlowLine.SLACK_PX
        chips = self.pack(["Alpha", "Alpha", "Alpha"], 2 * w + 8 + 1)
        self.assertEqual([c[1] == 0 for c in chips], [True, True, False])

    def test_an_overlong_label_gets_a_full_row_and_a_taller_chip(self):
        long = "Tell the captain everything you saw in the cargo hold, including the thing"
        chips = self.pack(["Short", long], 200)
        short, big = chips
        self.assertEqual(big[2], 200)
        self.assertGreater(big[1], short[1])
        self.assertGreater(big[3], short[3])

    def test_stack_gives_every_chip_a_row(self):
        chips = self.pack(["Yes", "No"], 2000, layout="stack")
        self.assertEqual([c[2] for c in chips], [2000, 2000])
        self.assertNotEqual(chips[0][1], chips[1][1])

    def test_nothing_is_wider_than_the_row(self):
        chips = self.pack(["a" * 5, "b" * 40, "c" * 80], 300)
        for x, y, w, h, _ in chips:
            self.assertLessEqual(x + w, 300.0001)


if __name__ == "__main__":
    unittest.main()
