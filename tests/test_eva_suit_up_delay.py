"""SUIT UP waits before it hands the console its suit.

Measured in the engine (2026-10-17, exe 2026-10-14): assigning a client to a PLAYER ship
in the same frame the ship was spawned kills that client (0xC0000005, 3 of 3, stock hull
or mod hull alike). The same assignment one or two seconds later survives 6 of 6, with
the suit console's 3D view and camera too. So `eva_go_out` spawns the suit at once and
hands it over EVA_ASSIGN_DELAY seconds later - the assignment, the autopilot watch and
`eva_went_out` (which brings in the suit console) all move to that moment.

    python -m unittest tests.test_eva_suit_up_delay
"""
import unittest
from unittest import mock

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from tests.test_eva_rails import _Base, RELIC
from cosmos_dev.mock import sbs
from sbs_utils.gui import GuiClient
from sbs_utils.procedural import eva as E
from sbs_utils.procedural.gui import eva_gui as EG
from sbs_utils.procedural.query import to_id

CID = 0x8000000000000011          # a real client id: the 0x8000 bit is what is_client_id tests


class SuitUpWaits(_Base):
    def setUp(self):
        super().setUp()
        from sbs_utils.tickdispatcher import TickDispatcher
        from sbs_utils.delete_queue import DeleteQueue
        TickDispatcher.clear()   # a handover queued by the previous test is not this one's
        DeleteQueue.clear()      # nor its suit's queued delete: ids recycle across tests
        GuiClient(CID)
        self.suit = self.suit_up(CID)
        self.assigned, self.emitted = [], []
        real_assign = sbs.assign_client_to_ship

        def assign(cid, ship):
            self.assigned.append((cid, ship))
            return real_assign(cid, ship)

        def emit(name, data=None, *a, **k):
            self.emitted.append(name)

        self.patches = [
            mock.patch.object(sbs, "assign_client_to_ship", assign),
            mock.patch("sbs_utils.procedural.boarding.boarding_held", lambda cid: True),
            mock.patch("sbs_utils.procedural.boarding.boarding_me", lambda cid: None),
            mock.patch("sbs_utils.procedural.eva.eva_offered", lambda **k: {"relic": RELIC}),
            mock.patch.object(EG, "_give_a_suit", lambda *a: self.suit),
            mock.patch("sbs_utils.procedural.gui.console.gui_console_enter", lambda *a, **k: False),
            mock.patch("sbs_utils.procedural.signal.signal_emit", emit),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        from sbs_utils.tickdispatcher import TickDispatcher
        TickDispatcher.clear()
        super().tearDown()

    def to_suit(self):
        return [a for a in self.assigned if a == (CID, to_id(self.suit))]

    def test_the_console_is_not_handed_the_suit_in_the_frame_it_spawned(self):
        self.assertTrue(EG.eva_go_out(CID))
        self.assertEqual(self.to_suit(), [], "assigned in the spawn frame: the crash")
        self.assertNotIn("eva_went_out", self.emitted)

    def test_it_is_handed_over_after_the_delay_once(self):
        EG.eva_go_out(CID)
        self.fly(EG.EVA_ASSIGN_DELAY + 1.0)
        self.assertEqual(len(self.to_suit()), 1)
        self.assertEqual(self.emitted.count("eva_went_out"), 1)

    def test_a_suit_gone_before_the_handover_hands_over_nothing(self):
        EG.eva_go_out(CID)
        E.eva_clear()                       # the ruin cleared, the suit deleted
        self.fly(EG.EVA_ASSIGN_DELAY + 1.0)  # must not raise: a raising tick freezes the game
        self.assertEqual(self.to_suit(), [])


if __name__ == "__main__":
    unittest.main()
