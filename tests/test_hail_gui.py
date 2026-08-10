"""Incoming hails, the widgets (sbs_utils.procedural.gui.hail_gui) - Phase 3.

The layout assertions drive the builders DIRECTLY. Their gui_* imports are inside the
functions, so patching the source modules records exactly what each one asks for - which
keeps these tests about which widgets appear, in what order, carrying what data, rather
than about pixel output.

    python -m unittest tests.test_hail_gui
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from cosmos_dev.mock import sbs as mock_sbs
from sbs_utils.agent import Agent
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.procedural import hail as H
from sbs_utils.procedural.gui import hail_gui as V
from sbs_utils.procedural.gui import button as BUTTON
from sbs_utils.procedural.gui import dropdown as DROPDOWN
from sbs_utils.procedural.gui import face as FACE
from sbs_utils.procedural.gui import image as IMAGE
from sbs_utils.procedural.gui import message as MESSAGE
from sbs_utils.procedural.gui import listbox as LISTBOX
from sbs_utils.procedural.gui import row as ROW
from sbs_utils.procedural.gui import text as TEXT
from sbs_utils.procedural.inventory import set_inventory_value
from sbs_utils.procedural.links import link
from sbs_utils.procedural.query import to_id
from sbs_utils.procedural.roles import add_role
from sbs_utils.procedural.spawn import player_spawn

NL = chr(10)

C_COMMS = 0x8000000000000001
C_MAIN = 0x8000000000000002

SCENES = {
    "open": {
        "data": {"speaker": "ashfang", "when": "hail", "presentation": "portrait"},
        "description": NL.join([
            "@Ashfang",
            "% You are a long way from friends.",
            "",
            "@Vell",
            "Captain, their weapons are hot.",
            "",
            "- [Stand down](backoff)",
            "- [Fight](backoff)",
        ]),
    },
    "backoff": {"data": {"speaker": "ashfang"},
                "description": "@Ashfang" + NL + "% Wise." + NL},
}


class _FakeItem:
    def __init__(self, data):
        self.data = data


class _FakeListbox:
    """Stands in for the listbox: what matters is the row the user picked."""

    def __init__(self, items):
        self.items = list(items)

    def get_value(self):
        return self.items[0] if self.items else None


class _FakeTask:
    def __init__(self):
        self.vars = {}

    def set_variable(self, name, value):
        self.vars[name] = value

    def get_variable(self, name, default=None):
        return self.vars.get(name, default)


def _console(cid, ship_id, *roles):
    agent = Agent()
    agent.id = cid
    agent.add()
    for r in roles:
        add_role(cid, r)
    link(ship_id, "consoles", cid)
    set_inventory_value(cid, "VIEWER_HOME_SHIP", ship_id)
    return cid


class HailViewBase(unittest.TestCase):
    def setUp(self):
        mock_sbs.create_new_sim()
        SpaceObject.clear()
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent())
        H.hail_reset()
        self.ship = to_id(player_spawn(0, 0, 0, "Artemis", "tsn", "battle"))
        self.comms = _console(C_COMMS, self.ship, "console", "comms")
        self.main = _console(C_MAIN, self.ship, "console", "mainscreen")

        self.trace = []
        self._saved = {}
        t = self.trace

        def patch(mod, name, fn):
            self._saved[(mod, name)] = getattr(mod, name)
            setattr(mod, name, fn)

        patch(ROW, "gui_row", lambda style=None: t.append(("row", style)))
        patch(TEXT, "gui_text", lambda s, *a, **k: t.append(("text", s)))
        patch(TEXT, "gui_text_area", lambda s, *a, **k: t.append(("text_area", s)))
        patch(FACE, "gui_face", lambda f, style=None: t.append(("face", f)))
        patch(IMAGE, "gui_image_keep_aspect_ratio_center",
              lambda f, style=None: t.append(("image", f)))
        def _btn(props, style=None, data=None, on_press=None, is_sub_task=False):
            item = _FakeItem(data)
            t.append(("button", props, data, item))
            return item
        patch(BUTTON, "gui_button", _btn)

        def _dd(props, style=None, var=None, data=None):
            item = _FakeItem(data)
            t.append(("dropdown", props, data, item))
            return item
        patch(DROPDOWN, "gui_drop_down", _dd)

        def _lb(items, style=None, **kw):
            items = list(items)
            t.append(("listbox", items))
            return _FakeListbox(items)
        patch(LISTBOX, "gui_list_box", _lb)
        patch(MESSAGE, "gui_message_callback",
              lambda item, cb: t.append(("callback", item, cb)))

    def tearDown(self):
        for (mod, name), fn in self._saved.items():
            setattr(mod, name, fn)
        FrameContext.context = None
        FrameContext.task = None
        H.hail_reset()

    # helpers ---------------------------------------------------------------
    def kinds(self):
        return [e[0] for e in self.trace]

    def buttons(self):
        return [e for e in self.trace if e[0] == "button"]

    def offer(self, **kw):
        kw.setdefault("scenes", SCENES)
        kw.setdefault("scene", "open")
        kw.setdefault("speaker", "ashfang")
        return H.hail_offer(self.ship, **kw)

    def open_to_choices(self):
        self.offer()
        H.hail_accept(self.ship)
        while H.hail_advance(self.ship):
            pass


class ChoiceStripTests(HailViewBase):
    def test_an_idle_ship_draws_nothing_at_all(self):
        self.assertEqual(V.hail_choice_strip(self.ship, self.comms), 0)
        self.assertEqual(self.trace, [])

    def test_a_waiting_hail_becomes_an_Answer_button(self):
        self.offer(name="Ashfang")
        self.assertEqual(V.hail_choice_strip(self.ship, self.comms), 1)
        props = self.buttons()[0][1]
        # No colon: the engine parses a button label as a style-property string.
        self.assertIn("Answer Ashfang", props)
        self.assertNotIn("`", props)

    def test_every_waiting_hail_gets_its_own_entry(self):
        for i in range(3):
            self.offer(name=f"Caller{i}")
        self.assertEqual(V.hail_choice_strip(self.ship, self.comms), 3)

    def test_the_queue_never_draws_more_than_the_strip_can_show(self):
        for i in range(7):
            self.offer(name=f"Caller{i}")
        self.assertEqual(V.hail_choice_strip(self.ship, self.comms),
                         H.HAIL_MAX_CHOICES)

    def test_nothing_is_ANSWERABLE_while_the_beats_run(self):
        self.offer()
        H.hail_accept(self.ship)
        V.hail_choice_strip(self.ship, self.comms)
        kinds = [b[2]["hail_kind"] for b in self.buttons()]
        self.assertNotIn("answer", kinds)

    def test_a_multi_beat_hail_offers_a_way_to_READ_ON(self):
        # Without this the conversation is a dead end: the choices are not live while
        # beats remain, so the strip would be empty and nothing on the console advances
        # a hail.
        self.offer()                       # two beats
        H.hail_accept(self.ship)
        self.assertEqual(V.hail_choice_strip(self.ship, self.comms), 1)
        self.assertIn("Continue", self.buttons()[0][1])
        self.assertEqual(self.buttons()[0][2]["hail_kind"], "advance")

    def test_continue_gives_way_to_the_choices_on_the_last_beat(self):
        self.offer()
        H.hail_accept(self.ship)
        H.hail_advance(self.ship)          # now on the final beat
        self.trace.clear()
        V.hail_choice_strip(self.ship, self.comms)
        self.assertEqual([b[2]["hail_kind"] for b in self.buttons()],
                         ["answer", "answer"])

    def test_a_console_that_may_not_answer_cannot_read_on_either(self):
        self.offer()
        H.hail_accept(self.ship)
        self.assertEqual(V.hail_choice_strip(self.ship, self.main), 0)

    def test_the_choices_appear_once_the_talking_stops(self):
        self.open_to_choices()
        self.assertEqual(V.hail_choice_strip(self.ship, self.comms), 2)
        self.assertIn("Stand down", self.buttons()[0][1])
        self.assertIn("Fight", self.buttons()[1][1])

    def test_a_console_that_may_not_answer_gets_no_buttons(self):
        self.open_to_choices()
        self.assertEqual(V.hail_choice_strip(self.ship, self.main), 0)
        self.assertEqual(self.buttons(), [])

    def test_every_button_shares_ONE_handler_object(self):
        # A per-iteration closure is the classic for-loop handler trap: every button
        # would capture the last value. One module-level callable cannot.
        self.open_to_choices()
        V.hail_choice_strip(self.ship, self.comms)
        handlers = {id(b[3]) for b in self.buttons()}
        # Every button is wired to the SAME module-level callable - a per-iteration
        # closure would make each one answer for the last.
        cbs = [e[2] for e in self.trace if e[0] == "callback"]
        self.assertEqual(len(cbs), 2)
        self.assertEqual({id(c) for c in cbs}, {id(V._hail_view_press)})

    def test_each_button_carries_its_own_index(self):
        self.open_to_choices()
        V.hail_choice_strip(self.ship, self.comms)
        self.assertEqual([b[2]["hail_index"] for b in self.buttons()], [0, 1])

    def test_every_button_carries_the_current_token(self):
        self.open_to_choices()
        V.hail_choice_strip(self.ship, self.comms)
        seq = H.hail_seq(self.ship)
        self.assertTrue(all(b[2]["hail_seq"] == seq for b in self.buttons()))

    def test_the_data_keys_cannot_clobber_the_consoles_own_variables(self):
        # A dict `data` is splatted into the task's variables, so an unprefixed `ship`
        # or `index` would quietly overwrite what the console layout is using.
        self.open_to_choices()
        V.hail_choice_strip(self.ship, self.comms)
        for b in self.buttons():
            for key in b[2]:
                self.assertTrue(key.startswith("hail_"), key)


class PressDispatchTests(HailViewBase):
    def _press(self, data, client_id):
        # Exactly how Column.on_message invokes it: (event, widget), from the LIVE gui
        # task - no __ITEM__ and no dependence on the task that built the widget.
        V._hail_view_press(FakeEvent(client_id=client_id), _FakeItem(data))

    def test_an_accept_press_opens_that_hail(self):
        hid = self.offer()
        self._press({"hail_kind": "accept", "hail_ship": self.ship, "hail_id": hid},
                    self.comms)
        self.assertTrue(H.hail_is_active(self.ship))

    def test_an_answer_press_takes_that_choice(self):
        self.open_to_choices()
        seq = H.hail_seq(self.ship)
        self._press({"hail_kind": "answer", "hail_ship": self.ship,
                     "hail_index": 0, "hail_seq": seq}, self.comms)
        self.assertEqual(H.hail_active(self.ship).scene, "backoff")

    def test_a_stale_press_is_refused_by_the_server_not_the_widget(self):
        self.open_to_choices()
        stale = H.hail_seq(self.ship) - 1
        self._press({"hail_kind": "answer", "hail_ship": self.ship,
                     "hail_index": 0, "hail_seq": stale}, self.comms)
        self.assertEqual(H.hail_active(self.ship).scene, "open")

    def test_a_press_from_a_console_that_may_not_answer_is_refused(self):
        self.open_to_choices()
        seq = H.hail_seq(self.ship)
        self._press({"hail_kind": "answer", "hail_ship": self.ship,
                     "hail_index": 0, "hail_seq": seq}, self.main)
        self.assertEqual(H.hail_active(self.ship).scene, "open")

    def test_a_continue_press_moves_to_the_next_beat(self):
        self.offer()
        H.hail_accept(self.ship)
        self._press({"hail_kind": "advance", "hail_ship": self.ship,
                     "hail_seq": H.hail_seq(self.ship)}, self.comms)
        self.assertEqual(H.hail_beat(self.ship).speaker, "vell")

    def test_a_stale_continue_cannot_skip_a_line(self):
        # Two officers pressing Continue in the same frame must not skip a beat
        # between them.
        self.offer()
        H.hail_accept(self.ship)
        stale = H.hail_seq(self.ship) - 1
        self._press({"hail_kind": "advance", "hail_ship": self.ship,
                     "hail_seq": stale}, self.comms)
        self.assertEqual(H.hail_beat(self.ship).speaker, "ashfang")

    def test_a_press_with_no_data_does_not_raise(self):
        V._hail_view_press(FakeEvent(client_id=self.comms), _FakeItem(None))


class PlacementDialTests(HailViewBase):
    def test_the_dial_shows_what_this_console_is_set_to(self):
        H.hail_where_set(self.comms, "both")
        V.hail_where_dropdown(self.comms)
        props = [e for e in self.trace if e[0] == "dropdown"][0][1]
        self.assertTrue(props.startswith("text:Both;"))
        self.assertIn("list:", props)

    def test_a_console_that_cannot_place_a_hail_gets_no_dial(self):
        self.assertIsNone(V.hail_where_dropdown(self.main))
        self.assertEqual(self.trace, [])

    def test_the_dial_owns_its_own_change_handler(self):
        # The console never writes an `on change`, so it cannot disagree with the
        # library about what the labels mean.
        V.hail_where_dropdown(self.comms)
        cbs = [e for e in self.trace if e[0] == "callback"]
        self.assertEqual(len(cbs), 1)
        self.assertIs(cbs[0][2], V._hail_where_changed)

    def test_moving_the_dial_moves_the_state(self):
        item = V.hail_where_dropdown(self.comms)
        V._hail_where_changed(FakeEvent(client_id=0, value_tag="This Console"), item)
        self.assertEqual(H.hail_where(self.comms), "console")

    def test_the_console_comes_from_the_widget_not_the_frame(self):
        # A server-rendered frame reports client 0; the dial must still move the
        # console it was drawn for.
        item = V.hail_where_dropdown(self.comms)
        V._hail_where_changed(FakeEvent(client_id=0, value_tag="Main Screen"), item)
        self.assertEqual(H.hail_where(self.comms), "main")


class ConversationViewTests(HailViewBase):
    def test_nothing_is_built_when_no_hail_is_open(self):
        self.assertIsNone(V.hail_view(self.ship, self.comms))
        self.assertEqual(self.trace, [])

    def test_an_orbit_builds_NOTHING_inline(self):
        # A live 3D view cannot be layered over at any draw layer, so the band is an
        # overlay and the console leaves its view alone.
        self.offer(presentation="orbit", subject="raider_lead")
        H.hail_accept(self.ship)
        set_inventory_value(self.ship, "HAIL_COMMS_ORBIT", True)
        self.assertEqual(V.hail_view(self.ship, self.comms), "orbit")
        self.assertEqual(self.trace, [])

    def test_a_portrait_draws_the_face_the_name_and_the_line(self):
        self.offer(presentation="portrait", face="ter #fff 0 0;", name="Ashfang")
        H.hail_accept(self.ship)
        self.assertEqual(V.hail_view(self.ship, self.comms), "portrait")
        self.assertIn("face", self.kinds())
        self.assertIn("text_area", self.kinds())
        self.assertTrue(any("Ashfang" in e[1] for e in self.trace if e[0] == "text"))

    def test_a_still_draws_its_backdrop(self):
        self.offer(presentation="still", backdrop="nebula_wide")
        H.hail_accept(self.ship)
        self.assertEqual(V.hail_view(self.ship, self.comms), "still")
        self.assertIn(("image", "nebula_wide"), self.trace)

    def test_the_spoken_line_reaches_the_widget_unassigned(self):
        # Dialogue text may contain braces; it goes straight into the widget rather
        # than through a MAST variable that would re-format it as an f-string.
        self.offer(lines="Brace yourself {captain}", choices=["ok"])
        H.hail_accept(self.ship)
        V.hail_view(self.ship, self.comms)
        areas = [e[1] for e in self.trace if e[0] == "text_area"]
        self.assertIn("Brace yourself {captain}", areas)

    def test_a_console_that_cannot_answer_sees_the_choices_read_only(self):
        self.open_to_choices()
        V.hail_view(self.ship, self.main)
        areas = NL.join(e[1] for e in self.trace if e[0] == "text_area")
        self.assertIn("1. Stand down", areas)
        self.assertIn("2. Fight", areas)
        self.assertEqual(self.buttons(), [])

    def test_comms_does_not_get_the_readout_because_it_has_the_strip(self):
        self.open_to_choices()
        V.hail_view(self.ship, self.comms)
        areas = NL.join(e[1] for e in self.trace if e[0] == "text_area")
        self.assertNotIn("1. Stand down", areas)


class HistoryPanelTests(HailViewBase):
    def _archive(self, n=1):
        for i in range(n):
            self.offer(name=f"Caller{i}")
            H.hail_accept(self.ship)
            H.hail_close(self.ship)
        self.trace.clear()

    def test_an_empty_log_says_so_rather_than_drawing_nothing(self):
        V.hail_panel_history(self.comms)
        self.assertTrue(any("No hails yet." in e[1]
                            for e in self.trace if e[0] == "text"))

    def test_past_conversations_go_in_a_listbox(self):
        self._archive(3)
        V.hail_panel_history(self.comms)
        boxes = [e for e in self.trace if e[0] == "listbox"]
        self.assertEqual(len(boxes), 1)
        self.assertEqual(len(boxes[0][1]), 3)

    def test_choosing_a_row_starts_a_replay(self):
        self._archive(1)
        entry = H.hail_log(self.ship)[0]
        V._hail_log_pick(FakeEvent(client_id=self.comms), _FakeListbox([entry]))
        self.assertEqual(H.hail_replaying(self.comms), entry.id)

    def test_a_replay_shows_the_transcript_and_no_list(self):
        self._archive(1)
        H.hail_replay_start(self.comms, H.hail_log(self.ship)[0].id)
        self.trace.clear()
        V.hail_panel_history(self.comms)
        self.assertEqual([e for e in self.trace if e[0] == "listbox"], [])
        self.assertTrue(any(e[0] == "text_area" for e in self.trace))

    def test_a_replay_offers_no_control_that_could_answer(self):
        # hail_answer refuses a replaying console anyway; not drawing anything that
        # LOOKS answerable is the belt to that braces.
        self._archive(1)
        H.hail_replay_start(self.comms, H.hail_log(self.ship)[0].id)
        self.trace.clear()
        V.hail_panel_history(self.comms)
        labels = [b[1] for b in self.buttons()]
        self.assertEqual(len(labels), 1)
        self.assertIn("Back to hails", labels[0])

    def test_back_leaves_the_replay(self):
        self._archive(1)
        H.hail_replay_start(self.comms, H.hail_log(self.ship)[0].id)
        V._hail_replay_back(FakeEvent(client_id=self.comms),
                            _FakeItem({"hail_client": self.comms}))
        self.assertIsNone(H.hail_replaying(self.comms))

    def test_a_replay_of_a_conversation_that_rolled_off_falls_back_to_the_list(self):
        self._archive(1)
        H.hail_replay_start(self.comms, 9999)
        V.hail_panel_history(self.comms)
        self.assertIsNone(H.hail_replaying(self.comms))


class TranscriptTextTests(HailViewBase):
    def test_a_line_carries_its_speaker(self):
        text = V.hail_transcript_text(
            {"transcript": [{"kind": "line", "name": "Ashfang", "text": "Hold."}]})
        self.assertIn("Ashfang", text)
        self.assertIn("Hold.", text)

    def test_an_answer_is_marked_as_the_crews_own(self):
        text = V.hail_transcript_text(
            {"transcript": [{"kind": "choice", "name": "", "text": "Stand down"}]})
        self.assertTrue(text.startswith(">"))
        self.assertIn("Stand down", text)

    def test_an_empty_conversation_still_renders(self):
        self.assertIn("nothing was said", V.hail_transcript_text({}))


class BandTests(HailViewBase):
    def test_every_row_of_the_band_is_opaque(self):
        # This is the one panel that sits over a LIVE engine view, where layering
        # cannot clip anything. The fill IS the clip.
        V._hail_band_builder(C_MAIN, {"name": "Ashfang", "line": "Hold still.",
                                      "choices": ["1. Run"]})
        rows = [e[1] for e in self.trace if e[0] == "row"]
        self.assertTrue(rows)
        for style in rows:
            self.assertIn(V.BAND_BACKGROUND, style)

    def test_the_band_carries_the_name_the_line_and_the_choices(self):
        V._hail_band_builder(C_MAIN, {"name": "Ashfang", "line": "Hold still.",
                                      "choices": ["1. Run", "2. Fight"]})
        self.assertTrue(any("Ashfang" in e[1] for e in self.trace if e[0] == "text"))
        areas = NL.join(e[1] for e in self.trace if e[0] == "text_area")
        self.assertIn("Hold still.", areas)
        self.assertIn("2. Fight", areas)

    def test_a_band_with_no_choices_omits_that_row(self):
        V._hail_band_builder(C_MAIN, {"name": "A", "line": "B", "choices": []})
        self.assertEqual(len([e for e in self.trace if e[0] == "text_area"]), 1)

    def test_the_slot_clears_the_viewscreen_data_column(self):
        from sbs_utils.procedural.gui.viewscreen import COLUMN_RECT
        self.assertLess(V.HAIL_BAND_RECT[2], COLUMN_RECT[0],
                        "the band must not overlap the science read-out")

    def test_the_band_sits_above_the_view_and_below_a_cutscene(self):
        self.assertGreater(V.HAIL_BAND_LAYER, 20000)
        self.assertLess(V.HAIL_BAND_LAYER, 26000)

    def test_showing_a_band_with_no_hail_does_nothing(self):
        self.assertFalse(V.hail_band_show(self.ship))


if __name__ == "__main__":
    unittest.main()
