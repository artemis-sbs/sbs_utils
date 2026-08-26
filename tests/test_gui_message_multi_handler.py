"""Every gui_message handler on a widget fires, not just the last one (LM #614).

Registration used to be a plain `=` in both slots, so attaching a second handler
silently discarded the first:

  * Channel 1 -- the page's tag_map, written by `on gui_message(w):`,
    `gui_message(w, label)` and `gui_button(on_press=...)`.
  * Channel 2 -- `layout_item.on_message_cb`, written by
    `gui_message_callback()` and `gui_message_label()`.

These pin the new behavior AND the three compatibility rules that make it safe:
a lone handler is never wrapped, an inert handler is not a link, and growing a
chain keeps the same tuple object. The five existing GUI-handler test files
passing untouched is the rest of the proof.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import logging
import unittest

import cosmos_dev.mock.sbs as sbs
from sbs_utils.mast.maststory import MastStory
from sbs_utils.mast_sbs import story_nodes  # noqa: F401  (registers route/gui nodes)
from sbs_utils.mast_sbs.maststorypage import StoryPage
from sbs_utils.mast.mastscheduler import MastScheduler, MastAsyncTask
from sbs_utils.mast.mast_globals import MastGlobals
from sbs_utils.mast.core_nodes.on_change import OnChangeRuntimeNode
from sbs_utils.agent import clear_shared
from sbs_utils.gui import Gui, GuiClient
from sbs_utils.helpers import FrameContext, Context, FakeEvent, props_display_text
from sbs_utils.message_chain import (MessageChain, compose_handler,
                                     invoke_message_cb, message_cb_add,
                                     message_handlers)
from sbs_utils.pages.layout.clickable import Clickable
from sbs_utils.pages.layout.column import Column
from sbs_utils.pages.layout.bounds import Bounds
from sbs_utils.pages.widgets.layout_listbox import LayoutListbox
from sbs_utils.procedural.gui import gui_row, gui_text
from sbs_utils.vec import Vec3
from sbs_utils.procedural.gui.button import MessageHandler
from sbs_utils.procedural.gui.message import MessageTrigger, dead_handler_sites_clear

CID = 1

# Collector shared with MAST. A module-level list keeps these assertions
# independent of `shared` variable scoping, which is not what they are about.
HITS = []


def mh_hit(what):
    HITS.append(what)


def mh_press():
    """on_press=<python callable> -- MessageHandler calls this with no args."""
    HITS.append("callable")


def mh_cb_a(event, item):
    HITS.append("cb-a")


def mh_cb_b(event, item):
    HITS.append("cb-b")


def mh_boom(event, item):
    raise RuntimeError("handler on fire")


# Names are MAST globals in ONE flat namespace shared by the whole discovered
# suite, so these carry a file-specific prefix.
MastGlobals.import_python_function(mh_hit)
MastGlobals.import_python_function(mh_press)
MastGlobals.import_python_function(mh_cb_a)
MastGlobals.import_python_function(mh_cb_b)


class MultiHandlerPage(StoryPage):
    story = None


class _FakeMain:
    def __init__(self, page):
        self.page = page


class _FakeGuiTask:
    """Enough for style parsing (`task.main.page.client_id`) and props formatting."""

    def __init__(self, page):
        self.main = _FakeMain(page)

    def set_variable(self, *a, **k):
        pass

    def get_variable(self, *a, **k):
        return None

    def compile_and_format_string(self, s):
        return s

    def format_string(self, s):
        return s


# ---------------------------------------------------------------------------
# Unit level: the compose rule and the chain itself, no MAST involved.
# ---------------------------------------------------------------------------

class _Node:
    """Stands in for a Channel-1 runtime node."""

    def __init__(self, name, sink):
        self.name = name
        self.sink = sink

    def on_message(self, event):
        self.sink.append(self.name)


class _InertNode(_Node):
    def is_inert(self):
        return True


class TestComposeRule(unittest.TestCase):
    def setUp(self):
        self.sink = []
        self.item = object()

    def test_one_handler_is_never_wrapped(self):
        """entry[1] must stay the raw node -- real consumers read it by type."""
        node = _Node("a", self.sink)
        entry = compose_handler(None, self.item, node)
        self.assertIs(entry[1], node)

    def test_a_none_node_registers_none_exactly_as_before(self):
        self.assertEqual(compose_handler(None, self.item, None), (self.item, None))

    def test_a_none_node_does_not_disturb_an_existing_handler(self):
        node = _Node("a", self.sink)
        first = compose_handler(None, self.item, node)
        # Every widget except gui_button registers None; that must not be a way
        # to wipe a handler that is already attached.
        self.assertEqual(compose_handler(first, self.item, None), (self.item, None))

    def test_a_second_handler_makes_a_chain(self):
        a, b = _Node("a", self.sink), _Node("b", self.sink)
        entry = compose_handler(compose_handler(None, self.item, a), self.item, b)
        self.assertIsInstance(entry[1], MessageChain)
        self.assertEqual(len(entry[1]), 2)
        entry[1].on_message("EV")
        self.assertEqual(self.sink, ["a", "b"])

    def test_a_third_handler_reuses_the_same_tuple(self):
        """Identity matters: the listbox retracts what it merged by `is`."""
        a, b, c = (_Node(n, self.sink) for n in "abc")
        two = compose_handler(compose_handler(None, self.item, a), self.item, b)
        three = compose_handler(two, self.item, c)
        self.assertIs(three, two)
        self.assertEqual(len(three[1]), 3)
        three[1].on_message("EV")
        self.assertEqual(self.sink, ["a", "b", "c"])

    def test_an_inert_handler_is_replaced_not_chained(self):
        """A bare gui_button() still gets a MessageHandler with nothing to run."""
        real = _Node("real", self.sink)
        entry = compose_handler((self.item, _InertNode("inert", self.sink)),
                                self.item, real)
        self.assertIs(entry[1], real)
        entry[1].on_message("EV")
        self.assertEqual(self.sink, ["real"])

    def test_a_different_widget_on_the_same_tag_replaces(self):
        a = _Node("a", self.sink)
        b = _Node("b", self.sink)
        other = object()
        entry = compose_handler((self.item, a), other, b)
        self.assertIs(entry[0], other)
        self.assertIs(entry[1], b)

    def test_registering_the_same_object_twice_fires_once(self):
        a = _Node("a", self.sink)
        entry = compose_handler(compose_handler(None, self.item, a), self.item, a)
        self.assertIs(entry[1], a)

    def test_the_same_object_added_twice_to_a_chain_fires_once(self):
        a, b = _Node("a", self.sink), _Node("b", self.sink)
        entry = compose_handler(compose_handler(None, self.item, a), self.item, b)
        compose_handler(entry, self.item, a)
        self.assertEqual(len(entry[1]), 2)

    def test_message_handlers_flattens_for_tooling(self):
        a, b = _Node("a", self.sink), _Node("b", self.sink)
        self.assertEqual(message_handlers(None), ())
        self.assertEqual(message_handlers(a), (a,))
        entry = compose_handler(compose_handler(None, self.item, a), self.item, b)
        self.assertEqual(message_handlers(entry[1]), (a, b))


class TestChannelTwoSlot(unittest.TestCase):
    """message_cb_add vs. plain assignment."""

    class _Item:
        on_message_cb = None

    def setUp(self):
        self.sink = []
        self.item = self._Item()
        self.a = lambda e, i: self.sink.append("a")
        self.b = lambda e, i: self.sink.append("b")

    def test_one_callback_is_stored_bare(self):
        message_cb_add(self.item, self.a)
        self.assertIs(self.item.on_message_cb, self.a)

    def test_two_callbacks_both_run_in_order(self):
        message_cb_add(self.item, self.a)
        message_cb_add(self.item, self.b)
        self.assertIsInstance(self.item.on_message_cb, MessageChain)
        invoke_message_cb(self.item.on_message_cb, "EV", self.item)
        self.assertEqual(self.sink, ["a", "b"])

    def test_direct_assignment_still_replaces(self):
        """`=` means replace. Only the explicit helper appends."""
        self.item.on_message_cb = self.a
        self.item.on_message_cb = self.b
        invoke_message_cb(self.item.on_message_cb, "EV", self.item)
        self.assertEqual(self.sink, ["b"])

    def test_the_same_callback_twice_is_stored_once(self):
        message_cb_add(self.item, self.a)
        message_cb_add(self.item, self.a)
        self.assertIs(self.item.on_message_cb, self.a)

    def test_a_legacy_object_callback_is_still_called_by_attribute(self):
        """Layout called this slot as `cb.on_message(event, item)`; Column called
        it as `cb(event, item)`. Both forms have to keep working."""
        sink = self.sink

        class Legacy:
            def on_message(self, event, item):
                sink.append("legacy")

        self.item.on_message_cb = Legacy()
        invoke_message_cb(self.item.on_message_cb, "EV", self.item)
        self.assertEqual(self.sink, ["legacy"])


class TestErrorIsolation(unittest.TestCase):
    def setUp(self):
        self.sink = []

    def test_a_raising_handler_does_not_stop_the_next(self):
        chain = MessageChain()
        chain.add(lambda e, i: (_ for _ in ()).throw(RuntimeError("boom")),
                  MessageChain.CB)
        chain.add(lambda e, i: self.sink.append("after"), MessageChain.CB)
        with self.assertLogs("mast.runtime", "ERROR") as caught:
            chain("EV", None)
        self.assertEqual(self.sink, ["after"])
        self.assertEqual(len(caught.records), 1)

    def test_stop_on_error_restores_propagation(self):
        chain = MessageChain()
        chain.add(lambda e, i: (_ for _ in ()).throw(RuntimeError("boom")),
                  MessageChain.CB)
        chain.add(lambda e, i: self.sink.append("after"), MessageChain.CB)
        chain.stop_on_error = True
        with self.assertRaises(RuntimeError):
            chain("EV", None)
        self.assertEqual(self.sink, [])

    def test_mutating_the_chain_mid_fire_does_not_skip_a_handler(self):
        """A handler may reroute and rebuild the GUI while the chain is still
        walking, so _fire iterates a snapshot."""
        chain = MessageChain()
        second = lambda e, i: self.sink.append("second")
        chain.add(lambda e, i: (self.sink.append("first"), chain.remove(second)),
                  MessageChain.CB)
        chain.add(second, MessageChain.CB)
        chain("EV", None)
        self.assertEqual(self.sink, ["first", "second"])
        self.assertEqual(len(chain), 1)

    def test_a_lone_handler_still_propagates(self):
        """Isolation only applies inside a chain, and a lone handler is never
        wrapped -- so a single-handler widget raises exactly as it always did."""
        item = TestChannelTwoSlot._Item()
        message_cb_add(item, mh_boom)
        with self.assertRaises(RuntimeError):
            invoke_message_cb(item.on_message_cb, "EV", item)


class TestClickSuppression(unittest.TestCase):
    """Column returns after its callback, so a widget with one does NOT also
    fire `on gui_click`. Preserved deliberately -- pinned so nobody 'fixes' it."""

    def test_a_callback_still_suppresses_the_click_record(self):
        Clickable.clicked = {}
        col = Column()
        col.tag = "t1"
        col.click_tag = "c1"
        hits = []
        message_cb_add(col, lambda e, i: hits.append("a"))
        message_cb_add(col, lambda e, i: hits.append("b"))
        col.on_message(FakeEvent(client_id=CID, tag="gui_message", sub_tag="c1"))
        self.assertEqual(hits, ["a", "b"])
        self.assertIsNone(Clickable.clicked.get(CID))

    def test_without_a_callback_the_click_is_recorded(self):
        Clickable.clicked = {}
        col = Column()
        col.tag = "t1"
        col.click_tag = "c1"
        col.on_message(FakeEvent(client_id=CID, tag="gui_message", sub_tag="c1"))
        self.assertIs(Clickable.clicked.get(CID), col)


# ---------------------------------------------------------------------------
# Integration: real MAST, a real StoryPage, clicks the way the engine sends them.
# ---------------------------------------------------------------------------

class _Base(unittest.TestCase):
    """Build a real StoryPage from a MAST snippet, present it, click by text."""

    def setUp(self):
        # Shipping behavior, not the #707 characterization profile.
        self._revive = MastAsyncTask.revive_ended_handlers
        self._pop = OnChangeRuntimeNode.pop_inline_block_on_end
        MastAsyncTask.revive_ended_handlers = True
        OnChangeRuntimeNode.pop_inline_block_on_end = True

    def tearDown(self):
        # hasattr, NOT "is not None": `on_runtime_error` DEFAULTS to None, so a
        # truthiness guard skips the restore and leaks this test's hook - and the
        # list it appends to - into every test that runs afterwards.
        if hasattr(self, "_orig_rte"):
            MastScheduler.on_runtime_error = self._orig_rte
        Gui.clients = {}
        Gui.widget_list_sent = {}
        MultiHandlerPage.story = None
        FrameContext.task = None
        FrameContext.page = None
        FrameContext.mast = None
        FrameContext.context = None
        HITS.clear()
        MastAsyncTask.revive_ended_handlers = self._revive
        OnChangeRuntimeNode.pop_inline_block_on_end = self._pop

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
        errors = story.compile(code, "multihandler", story)
        self.assertEqual(errors, [], f"compile errors: {errors}")
        story.compiler_errors = []
        MultiHandlerPage.story = story
        FrameContext.mast = story

        self.errors = []
        self._orig_rte = MastScheduler.on_runtime_error
        # StoryScheduler OVERRIDES `runtime_error`, so patching it on MastScheduler
        # binds a method nothing calls and the assertion below is vacuous. The
        # class-level `on_runtime_error` seam is what the story scheduler actually
        # fires (and is what cosmos_dev's verdict uses).
        MastScheduler.on_runtime_error = self.errors.append

        self.page = MultiHandlerPage()
        Gui.push(CID, self.page)
        self.present(3)
        return self.page

    def present(self, n=1):
        for _ in range(n):
            sbs.sim._time_tick_counter += 30      # ~1 sim-second per present
            self.page.present(FakeEvent(CID, "gui_present"))

    def find_tag(self, text):
        want = text.strip().lower()
        for tag, entry in list(self.page.tag_map.items()):
            item = entry[0] if isinstance(entry, tuple) and entry else entry
            shown = props_display_text(getattr(item, "value", None))
            if shown and shown.strip().lower() == want:
                return tag
        self.fail(f"no widget showing {text!r}; on screen: {self.visible()}")

    def visible(self):
        out = []
        for tag, entry in list(self.page.tag_map.items()):
            item = entry[0] if isinstance(entry, tuple) and entry else entry
            shown = props_display_text(getattr(item, "value", None))
            if shown:
                out.append(shown.strip())
        return out

    def node(self, text="Press"):
        entry = self.page.tag_map[self.find_tag(text)]
        return entry[1] if isinstance(entry, tuple) else entry

    def click(self, text="Press"):
        """A click the way the engine delivers one: dispatch, then a tick.

        The context event carries the CLICKING client, as handlerhooks sets it
        per event -- gui_message_label reaches its task through
        FrameContext.client_task, which resolves off that client_id.
        """
        self.dispatch(self.find_tag(text))
        self.present(1)

    def dispatch(self, tag):
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(CID, "gui_message"))
        Gui.on_message(FakeEvent(client_id=CID, tag="gui_message", sub_tag=tag))

    def walk_layouts(self):
        """Every node in the page's layout tree -- a sub-section is a nested
        Layout inside a row, not a tag_map entry."""
        out = []

        def walk(node):
            out.append(node)
            for row in getattr(node, "rows", None) or []:
                walk(row)
            for col in getattr(node, "columns", None) or []:
                walk(col)

        for layout in self.page.layouts:
            walk(layout)
        return out

    def assertNoRuntimeErrors(self):
        self.assertEqual(self.errors, [], f"runtime errors: {self.errors}")


HEAD = 'gui_section("area: 5,5,95,95;")\ngui_row()\n'

ONE_BLOCK = HEAD + """b = gui_button("Press")
on gui_message(b):
    mh_hit("only")
await gui()
"""

TWO_BLOCKS = HEAD + """b = gui_button("Press")
on gui_message(b):
    mh_hit("one")
on gui_message(b):
    mh_hit("two")
await gui()
"""

THREE_BLOCKS = HEAD + """b = gui_button("Press")
on gui_message(b):
    mh_hit("one")
on gui_message(b):
    mh_hit("two")
on gui_message(b):
    mh_hit("three")
await gui()
"""

LABEL_AND_BLOCK = HEAD + """b = gui_button("Press")
gui_message(b, mh_label_handler)
on gui_message(b):
    mh_hit("block")
await gui()

== mh_label_handler ==
    mh_hit("label")
    ->END
"""

ON_PRESS_AND_BLOCK = HEAD + """b = gui_button("Press", on_press=mh_press)
on gui_message(b):
    mh_hit("block")
await gui()
"""

BARE_BUTTON_AND_BLOCK = HEAD + """b = gui_button("Press")
on gui_message(b):
    mh_hit("block")
await gui()
"""

ALIASED_BUTTON = HEAD + """b = gui_button("Press", "tag: pressy;")
on gui_message(b):
    mh_hit("one")
on gui_message(b):
    mh_hit("two")
await gui()
"""


class TestChannelOneMultiplicity(_Base):
    def test_two_inline_blocks_both_run(self):
        self.start(TWO_BLOCKS)
        self.click()
        self.assertEqual(HITS, ["one", "two"])
        self.assertNoRuntimeErrors()

    def test_three_handlers_run_in_registration_order(self):
        self.start(THREE_BLOCKS)
        self.click()
        self.assertEqual(HITS, ["one", "two", "three"])

    def test_label_form_and_inline_block_both_run(self):
        self.start(LABEL_AND_BLOCK)
        self.click()
        self.assertEqual(HITS, ["label", "block"])

    def test_on_press_survives_a_later_on_gui_message(self):
        """The headline regression: `on gui_message` used to destroy on_press."""
        self.start(ON_PRESS_AND_BLOCK)
        self.click()
        self.assertEqual(HITS, ["callable", "block"])

    def test_one_handler_is_never_wrapped(self):
        self.start(ONE_BLOCK)
        self.assertIsInstance(self.node(), MessageTrigger)

    def test_a_bare_button_leaves_no_inert_link(self):
        """gui_button() always builds a MessageHandler; with no on_press it has
        nothing to run and must not become a link in the chain."""
        self.start(BARE_BUTTON_AND_BLOCK)
        self.assertIsInstance(self.node(), MessageTrigger)
        self.click()
        self.assertEqual(HITS, ["block"])

    def test_alias_and_tag_share_one_chain(self):
        self.start(ALIASED_BUTTON)
        self.assertIn("pressy", self.page.tag_map)
        # The alias key composes independently of the engine tag, so it is its
        # own chain object -- what has to match is the handlers in it.
        self.assertEqual(message_handlers(self.page.tag_map["pressy"][1]),
                         message_handlers(self.node()))
        self.assertIsInstance(self.node(), MessageChain)
        self.assertEqual(len(self.node()), 2)
        self.click()
        self.assertEqual(HITS, ["one", "two"])

    def test_presenting_repeatedly_does_not_accumulate(self):
        self.start(TWO_BLOCKS)
        self.present(20)
        self.assertEqual(len(self.node()), 2)
        self.click()
        self.assertEqual(HITS, ["one", "two"])


CB_AND_CB = HEAD + """b = gui_button("Press")
gui_message_callback(b, mh_cb_a)
gui_message_callback(b, mh_cb_b)
await gui()
"""

CB_ONLY = HEAD + """b = gui_button("Press")
gui_message_callback(b, mh_cb_a)
await gui()
"""

CB_AND_MESSAGE_LABEL = HEAD + """b = gui_button("Press")
gui_message_callback(b, mh_cb_a)
gui_message_label(b, mh_label_handler)
await gui()

== mh_label_handler ==
    mh_hit("label")
    ->END
"""

SECTION_CB = """sec = gui_section("area: 5,5,95,95;")
gui_message_callback(sec, mh_cb_a)
gui_row()
gui_text("Press")
await gui()
"""

SECTION_TWO_CBS = """sec = gui_section("area: 5,5,95,95;")
gui_message_callback(sec, mh_cb_a)
gui_message_callback(sec, mh_cb_b)
gui_row()
gui_text("Press")
await gui()
"""

SUB_SECTION_LABEL = HEAD + """sub = gui_sub_section()
with sub:
    gui_text("Inside")
gui_message_label(sub, mh_label_handler)
gui_button("Press")
await gui()

== mh_label_handler ==
    mh_hit("label")
    ->END
"""


class TestChannelTwoMultiplicity(_Base):
    def test_one_callback_is_stored_bare(self):
        self.start(CB_ONLY)
        item = self.page.tag_map[self.find_tag("Press")][0]
        self.assertIs(item.on_message_cb, mh_cb_a)

    def test_two_callbacks_both_run(self):
        self.start(CB_AND_CB)
        self.click()
        self.assertEqual(HITS, ["cb-a", "cb-b"])

    def test_callback_and_message_label_both_run(self):
        self.start(CB_AND_MESSAGE_LABEL)
        self.click()
        self.assertEqual(HITS, ["cb-a", "label"])

    def test_callback_on_a_section_no_longer_raises(self):
        """Layout called this slot by attribute; gui_message_callback assigns a
        plain function, so the first click used to raise AttributeError."""
        page = self.start(SECTION_CB)
        section_tag = page.layouts[0].tag
        self.dispatch(section_tag)
        self.assertEqual(HITS, ["cb-a"])
        self.assertNoRuntimeErrors()

    def test_two_callbacks_on_a_section_both_run(self):
        page = self.start(SECTION_TWO_CBS)
        self.dispatch(page.layouts[0].tag)
        self.assertEqual(HITS, ["cb-a", "cb-b"])

    def test_message_label_on_a_sub_section_reaches_the_layout(self):
        """PageSubSection is a wrapper around the Layout, not the Layout. Without
        the forward, the handler landed on the wrapper and nothing read it --
        which is what the example in gui_message_label's own docstring does."""
        self.start(SUB_SECTION_LABEL)
        owners = [n for n in self.walk_layouts()
                  if getattr(n, "on_message_cb", None) is not None]
        self.assertEqual(len(owners), 1,
                         "exactly the sub-section's layout carries the callback")
        self.dispatch(owners[0].tag)
        self.present(1)
        self.assertEqual(HITS, ["label"])


CB_AND_BLOCK = HEAD + """b = gui_button("Press")
gui_message_callback(b, mh_cb_a)
on gui_message(b):
    mh_hit("block")
await gui()
"""


REROUTE_MID_CHAIN = HEAD + """b = gui_button("Press")
on gui_message(b):
    mh_hit("first")
    gui_reroute_client(client_id, mh_elsewhere)
on gui_message(b):
    mh_hit("second")
await gui()

== mh_elsewhere ==
    gui_section("area: 5,5,95,95;")
    gui_row()
    gui_text("Elsewhere")
    await gui()
"""


class TestRerouteMidChain(_Base):
    def test_a_handler_that_reroutes_does_not_stop_the_chain(self):
        """Aborting the rest would reintroduce the bug #614 is about: a handler
        that silently never runs."""
        self.start(REROUTE_MID_CHAIN)
        self.click()
        self.assertEqual(HITS, ["first", "second"])


class TestCrossChannel(_Base):
    def test_callback_and_inline_block_both_run(self):
        """Channel 2 first: StoryPage.on_message walks the layouts before it
        looks the tag up in tag_map."""
        self.start(CB_AND_BLOCK)
        self.click()
        self.assertEqual(HITS, ["cb-a", "block"])


class _RowNode:
    """A Channel-1 runtime node a row template can attach."""

    def __init__(self, name, sink):
        self.name = name
        self.sink = sink

    def on_message(self, event):
        self.sink.append(self.name)


ROW_SINK = []


def _two_handler_row(item, **kwargs):
    """A row template that attaches TWO handlers to the same widget."""
    gui_row("row-height: 1.2em;")
    w = gui_text(f"$text:`{item}`;", style=f"tag:row-{item};")
    page = FrameContext.page                      # the listbox's SubPage shim
    page.add_tag(w, _RowNode(f"{item}-one", ROW_SINK))
    page.add_tag(w, _RowNode(f"{item}-two", ROW_SINK))
    return None


class TestSubPageAndListbox(unittest.TestCase):
    """Rows are built against a SubPage shim and merged into the page, so the
    compose rule has to hold there too -- and must NOT accumulate per redraw."""

    def setUp(self):
        ROW_SINK.clear()
        sbs.create_new_sim()
        FrameContext.aspect_ratios[0] = Vec3(1024, 768, 0)
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        self.page = StoryPage()
        self.page.pending_gui = False
        self.page.client_id = 0
        self.page.gui_task = _FakeGuiTask(self.page)
        self.client = GuiClient(0)
        self.client.page_stack.append(self.page)
        FrameContext.page = self.page
        FrameContext.task = self.page.gui_task

    def tearDown(self):
        Gui.clients.pop(0, None)
        FrameContext.page = None
        FrameContext.task = None
        FrameContext.context = None
        ROW_SINK.clear()

    def _lb(self, items):
        b = Bounds(2.0, 10.0, 30.0, 90.0)
        lb = LayoutListbox(b.left, b.top, "lb", items, item_template=_two_handler_row)
        lb.tag = "lb"
        lb.bounds = b
        lb.client_id = 0
        return lb

    def test_a_row_widget_keeps_both_handlers(self):
        lb = self._lb(["A", "B"])
        lb._present(FakeEvent(0))
        node = self.page.tag_map["row-A"][1]
        self.assertIsInstance(node, MessageChain)
        self.assertEqual(len(node), 2)

    def test_the_merged_entry_is_the_composed_one(self):
        """The listbox merges its SubPage tag_map into the page with `|=`, which
        replaces rather than composes -- this pins that the composed entry is
        the one that survives."""
        lb = self._lb(["A"])
        lb._present(FakeEvent(0))
        node = self.page.tag_map["row-A"][1]
        node.on_message(FakeEvent(0))
        self.assertEqual(ROW_SINK, ["A-one", "A-two"])

    def test_rows_do_not_accumulate_across_redraws(self):
        """A fresh SubPage per draw is what keeps this from growing."""
        lb = self._lb(["A", "B"])
        for _ in range(5):
            lb.sections = []
            lb._present(FakeEvent(0))
        self.assertEqual(len(self.page.tag_map["row-A"][1]), 2)


CLEAR_ME = HEAD + """b = gui_button("Press")
gui_message_callback(b, mh_cb_a)
on gui_message(b):
    mh_hit("block")
gui_message_clear(b)
await gui()
"""


class TestClear(_Base):
    def test_gui_message_clear_removes_every_handler(self):
        self.start(CLEAR_ME)
        item = self.page.tag_map[self.find_tag("Press")][0]
        self.assertIsNone(item.on_message_cb)
        self.assertIsNone(self.node())
        self.click()
        self.assertEqual(HITS, [])


if __name__ == "__main__":
    unittest.main()
