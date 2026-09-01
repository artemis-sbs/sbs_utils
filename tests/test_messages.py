"""Messages: crew to crew, and letters from home.

The two properties that matter are addressing and read state. An announcement has to
reach everyone, a private note has to reach one console and no other, and "unread"
has to be per console - otherwise the badge on the tile is meaningless and the crew
stop trusting it.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

import cosmos_dev.mock.sbs as sbs
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.agent import clear_shared
from sbs_utils.procedural.messages import (
    message_send, message_mail, message_inbox, message_unread, message_mark_read,
    message_is_read, message_clear, message_load_amd, message_deliver_due,
    messages_count, message_revision, message_select, message_selected,
    message_answer, MAX_TEXT, MAX_KEPT)


class _Sim:
    time_tick_counter = 0


class _Page:
    def __init__(self, console):
        self.console = console
        self.client_id = 7
        self.gui_task = None


class MessagesBase(unittest.TestCase):
    def setUp(self):
        FrameContext.context = Context(_Sim(), sbs, FakeEvent(0, "test"))
        FrameContext.page = None
        clear_shared()

    def tearDown(self):
        FrameContext.page = None
        FrameContext.context = None

    def at(self, console):
        FrameContext.page = _Page(console)


class TestAddressing(MessagesBase):
    def test_an_announcement_reaches_everyone(self):
        message_send("All hands.", sender="The Captain")
        for console in ("helm", "weapons", "engineering"):
            self.assertEqual(len(message_inbox(console)), 1, console)

    def test_a_private_note_reaches_one_console(self):
        message_send("Just you.", to="helm", sender="Engineering")
        self.assertEqual(len(message_inbox("helm")), 1)
        self.assertEqual(message_inbox("weapons"), [])

    def test_a_list_reaches_each_of_them(self):
        message_send("Two of you.", to="helm, weapons", sender="The Captain")
        self.assertEqual(len(message_inbox("helm")), 1)
        self.assertEqual(len(message_inbox("weapons")), 1)
        self.assertEqual(message_inbox("science"), [])

    def test_the_engine_console_name_is_understood(self):
        """`normal_engi` is what the engine calls it; a script writes `engineering`."""
        message_send("Engine room.", to="engineering", sender="Helm")
        self.assertEqual(len(message_inbox("normal_engi")), 1)

    def test_the_sender_defaults_to_the_console_sending(self):
        self.at("normal_helm")
        msg = message_send("From me.")
        self.assertEqual(msg["from"], "helm")

    def test_newest_first(self):
        message_send("one", sender="a")
        message_send("two", sender="b")
        self.assertEqual([m["text"] for m in message_inbox("helm")], ["two", "one"])


class TestReadState(MessagesBase):
    def setUp(self):
        super().setUp()
        message_send("All hands.", sender="The Captain")
        message_send("Just helm.", to="helm", sender="The Captain")

    def test_unread_is_per_console(self):
        """The whole reason the tile badge means anything."""
        self.assertEqual(message_unread("helm"), 2)
        self.assertEqual(message_unread("weapons"), 1)

    def test_reading_one_marks_only_that_one(self):
        first = message_inbox("helm")[0]
        message_mark_read(first["id"], console="helm")
        self.assertEqual(message_unread("helm"), 1)
        self.assertTrue(message_is_read(first["id"], "helm"))

    def test_reading_it_on_helm_does_not_read_it_on_weapons(self):
        for m in message_inbox("helm"):
            message_mark_read(m["id"], console="helm")
        self.assertEqual(message_unread("helm"), 0)
        self.assertEqual(message_unread("weapons"), 1)

    def test_marking_the_whole_inbox(self):
        message_mark_read(console="helm")
        self.assertEqual(message_unread("helm"), 0)

    def test_a_new_message_is_unread_again(self):
        message_mark_read(console="helm")
        message_send("Something else.", sender="The Captain")
        self.assertEqual(message_unread("helm"), 1)


class TestLimits(MessagesBase):
    def test_a_long_message_is_cut_not_dropped(self):
        msg = message_send("x" * (MAX_TEXT + 500), sender="a")
        self.assertEqual(len(msg["text"]), MAX_TEXT)
        self.assertTrue(msg["text"].endswith("..."))

    def test_the_cut_is_ASCII(self):
        """The engine draws no ellipsis character."""
        msg = message_send("x" * (MAX_TEXT + 10), sender="a")
        self.assertTrue(all(ord(c) < 128 for c in msg["text"]))

    def test_the_oldest_are_dropped_past_the_cap(self):
        """A party runs for hours and nothing else prunes."""
        for i in range(MAX_KEPT + 20):
            message_send(f"m{i}", sender="a")
        self.assertEqual(messages_count(), MAX_KEPT)
        self.assertEqual(message_inbox("helm")[0]["text"], f"m{MAX_KEPT + 19}")

    def test_clear_empties_both_the_mail_and_the_read_marks(self):
        message_mark_read(console="helm")
        message_clear()
        self.assertEqual(messages_count(), 0)
        message_send("after", sender="a")
        self.assertEqual(message_unread("helm"), 1)


AMD = """# [Personal Messages](messages)

Mail.

## [A parcel, eventually](mail_parcel)
---
From: Your sister, Mira
To: helm
After: 240
---
The socks are in the post.

## [All hands](mail_all)
---
From: The Captain
---
Contact in ten minutes.

## [Not a message](section_note)
---
Note: this has no From, so it is not one
---
Skipped.
"""


class TestAuthoredContent(MessagesBase):
    """The half a writer touches: an .amd file, no code."""

    def doc(self):
        from sbs_utils.procedural.amd_doc import amd_document
        return amd_document(AMD)

    def test_a_heading_without_a_From_is_not_a_message(self):
        """The section heading has no From - the same rule the recipe loader uses."""
        self.assertEqual(message_load_amd(self.doc()), 2)

    def test_nothing_arrives_before_it_is_delivered(self):
        message_load_amd(self.doc())
        self.assertEqual(messages_count(), 0)

    def test_After_holds_a_message_back(self):
        """Mail that arrives while they are flying is the point; a pile that all
        landed at t=0 would be a document."""
        message_load_amd(self.doc())
        self.assertEqual(message_deliver_due(now=0), 1)
        self.assertEqual(message_deliver_due(now=100), 0)
        self.assertEqual(message_deliver_due(now=240), 1)

    def test_a_delivered_message_is_not_delivered_twice(self):
        message_load_amd(self.doc())
        message_deliver_due(now=1000)
        self.assertEqual(message_deliver_due(now=2000), 0)

    def test_the_body_and_the_subject_survive(self):
        message_load_amd(self.doc())
        message_deliver_due(now=1000)
        got = {m["subject"]: m for m in message_inbox("helm")}
        self.assertIn("A parcel, eventually", got)
        self.assertEqual(got["A parcel, eventually"]["from"], "Your sister, Mira")
        self.assertIn("socks", got["A parcel, eventually"]["text"])

    def test_authored_To_is_honoured(self):
        message_load_amd(self.doc())
        message_deliver_due(now=1000)
        self.assertEqual(len(message_inbox("helm")), 2)
        self.assertEqual(len(message_inbox("weapons")), 1)   # the all-hands one only

    def test_authored_mail_is_marked_as_mail(self):
        message_load_amd(self.doc())
        message_deliver_due(now=1000)
        self.assertTrue(all(m["kind"] == "mail" for m in message_inbox("helm")))

    def test_a_crew_message_is_not(self):
        message_send("typed by a person", sender="helm")
        self.assertEqual(message_inbox("weapons")[0]["kind"], "crew")

    def test_message_mail_is_the_same_thing_named_for_a_story(self):
        message_mail("A letter.", to="science", sender="Mum")
        self.assertEqual(message_inbox("science")[0]["kind"], "mail")


if __name__ == "__main__":
    unittest.main()


class TestTheScreenKnowsToRepaint(MessagesBase):
    """Reported from the engine: new mail did not appear, and picking a different
    message did not change the pane beside the list.

    Both are the same cause - the screen is built once and sits in `await gui()`, and
    A SIGNAL DOES NOT WAKE THAT. A live panel has to poll something that changes,
    which is why the away console watches `away_seq()`. This is the inbox's counter.
    """

    def test_new_mail_moves_it(self):
        before = message_revision("helm")
        message_send("something", sender="a")
        self.assertNotEqual(message_revision("helm"), before)

    def test_picking_a_different_message_moves_it(self):
        """The second half of the report: the reading pane is drawn from the
        selection, so the selection changing has to be a repaint."""
        message_send("one", sender="a")
        message_send("two", sender="b")
        first, second = message_inbox("helm")
        message_select(first["id"], "helm")
        before = message_revision("helm")
        message_select(second["id"], "helm")
        self.assertNotEqual(message_revision("helm"), before)

    def test_reading_one_moves_it(self):
        """The row's unread mark is on screen, so it has to redraw."""
        message_send("one", sender="a")
        before = message_revision("helm")
        message_mark_read(message_inbox("helm")[0]["id"], "helm")
        self.assertNotEqual(message_revision("helm"), before)

    def test_answering_moves_it(self):
        msg = message_send("Do we hold?", sender="a", choices=["Hold"])
        before = message_revision("helm")
        message_answer(msg["id"], 0, "helm")
        self.assertNotEqual(message_revision("helm"), before)

    def test_ONE_CONSOLE_ACTING_DOES_NOT_REPAINT_THE_OTHERS(self):
        """Six consoles rebuilding every time one crew member clicks a row is the
        difference between a counter and a broadcast."""
        message_send("one", sender="a")
        mid = message_inbox("helm")[0]["id"]
        weapons_before = message_revision("weapons")
        message_select(mid, "helm")
        message_mark_read(mid, "helm")
        self.assertEqual(message_revision("weapons"), weapons_before)

    def test_but_new_mail_wakes_everybody(self):
        weapons_before = message_revision("weapons")
        message_send("all hands", sender="The Captain")
        self.assertNotEqual(message_revision("weapons"), weapons_before)

    def test_the_selection_is_remembered_per_console(self):
        """A repaint builds a NEW listbox whose selection starts empty, so the pane
        would snap back to the newest message without this."""
        message_send("one", sender="a")
        message_send("two", sender="b")
        first, second = message_inbox("helm")
        message_select(first["id"], "helm")
        message_select(second["id"], "weapons")
        self.assertEqual(message_selected("helm"), first["id"])
        self.assertEqual(message_selected("weapons"), second["id"])

    def test_nothing_selected_reads_as_nothing(self):
        self.assertIsNone(message_selected("helm"))
