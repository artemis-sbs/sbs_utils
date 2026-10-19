"""A finished hail is written into the comms WATERFALL, so the crew has a timeline.

The rule (2026-10-19): what matters or wants an answer is an incoming hail; what the
comms officer reads is the waterfall. A hail closed and left no trace there, so the
conversation that mattered most was the one missing from the crew's own record. Now the
caller's lines arrive as received messages and the crew's answer as a transmitted one,
filed under the caller when the caller is something in the world.

    python -m unittest tests.test_hail_comms_timeline
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs as sbs
from tests.reset_helper import reset_mock

from sbs_utils.procedural import hail as H
from sbs_utils.procedural.a2x.spawn import create_enemy
from sbs_utils.procedural.query import to_id
from sbs_utils.procedural.roles import add_role


class Timeline(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)
        H.hail_echo_reset()
        self.ship = to_id(create_enemy(0, 0, 0, "tsn_light_cruiser", name="Artemis"))
        add_role(self.ship, "__player__")
        self.station = to_id(create_enemy(500, 0, 0, "starbase_command", name="DS 1"))
        self.sent = []
        self._orig = sbs.send_comms_message_to_player_ship

        def tap(contactID, playerID, otherID, faceDesc, titleText, titleColor,
                bodyText, bodyColor, tagset, name="unset"):
            self.sent.append({"contact": contactID, "player": playerID,
                              "text": bodyText, "tag": tagset, "name": name})
        sbs.send_comms_message_to_player_ship = tap

    def tearDown(self):
        sbs.send_comms_message_to_player_ship = self._orig
        H.hail_echo_reset()

    def _talk(self, subject=None, lines="We have a problem.", answer=True):
        H.hail_offer(self.ship, speaker="ds1", name="DS 1", subject=subject,
                     lines=lines, choices=["Take the case"])
        H.hail_accept(self.ship)
        if answer:
            H.hail_answer(self.ship, 0)
        else:
            H.hail_close(self.ship, declined=True)

    def test_on_by_default(self):
        self._talk(subject=self.station)
        self.assertTrue(self.sent, "a closed hail wrote nothing to the waterfall")

    def test_the_line_then_the_answer_in_order(self):
        self._talk(subject=self.station)
        self.assertEqual([(m["text"], m["tag"]) for m in self.sent],
                         [("We have a problem.", "recv"), ("Take the case", "send")])

    def test_filed_under_the_caller_on_the_ship(self):
        self._talk(subject=self.station)
        for m in self.sent:
            self.assertEqual(m["player"], self.ship)
            self.assertEqual(m["contact"], self.station)

    def test_a_caller_who_is_only_a_name_is_the_ships_own_channel(self):
        self._talk(subject=None)
        self.assertEqual(len(self.sent), 2)
        self.assertEqual(self.sent[0]["name"], "DS 1")
        for m in self.sent:
            self.assertEqual(m["player"], self.ship)

    def test_a_call_nobody_answered_still_leaves_a_line(self):
        H.hail_offer(self.ship, speaker="ds1", name="DS 1", title="X",
                     subject=self.station, lines="Hello?")
        H.hail_accept(self.ship)
        # Accepted then declined: the line WAS heard, so it is in the timeline.
        H.hail_close(self.ship, declined=True)
        self.assertEqual([m["text"] for m in self.sent], ["Hello?"])

    def test_a_brace_an_author_wrote_is_not_a_slot(self):
        self._talk(subject=self.station, lines="Codes {alpha} confirmed.")
        self.assertEqual(self.sent[0]["text"], "Codes {alpha} confirmed.")

    def test_off_writes_nothing(self):
        H.hail_echo_comms_enable(False)
        self._talk(subject=self.station)
        self.assertEqual(self.sent, [])

    def test_reset_turns_it_back_on(self):
        H.hail_echo_comms_enable(False)
        H.hail_echo_reset()
        self._talk(subject=self.station)
        self.assertTrue(self.sent)


if __name__ == "__main__":
    unittest.main()
