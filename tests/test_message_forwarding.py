"""Mail addressed to somebody who is not at their post.

A mission writes `To: science` and then the science officer beams down. Nobody is at
science any more, so the letter is delivered to an empty chair - it sits in the store,
matches no reader, and nobody ever learns it existed. A party short of people makes it
worse: the fewer consoles are staffed, the more of the mission's own mail disappears.

A ship forwards. The letter goes to whoever is covering, and it goes to exactly ONE
console - the same one `away.py` hands a forwarded job to, so one person is covering
rather than two halves of the job landing in different places.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

import cosmos_dev.mock.sbs as sbs
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.agent import clear_shared
from sbs_utils.gui import GuiClient
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.procedural import away as A
from sbs_utils.procedural import messages as M
from sbs_utils.procedural.inventory import set_inventory_value
from sbs_utils.procedural.roles import add_role

HELM, SCI, ENG = 7, 8, 9


class _Sim:
    time_tick_counter = 0


class _Page:
    def __init__(self, client_id, console):
        self.client_id = client_id
        self.console = console
        self.gui_task = None


class ForwardBase(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        SpaceObject.clear()
        clear_shared()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(0, "test"))
        FrameContext.page = None
        A.away_clear()
        A._TEAM.clear()
        M.message_forwarding(True)
        self.addCleanup(A.away_clear)
        self.addCleanup(A._TEAM.clear)
        self.addCleanup(M.message_forwarding, True)

    def tearDown(self):
        FrameContext.page = None
        FrameContext.context = None

    def sit(self, client_id, console):
        """The pair `gui_console_enter` writes: the role AND CONSOLE_TYPE.

        Both, deliberately - `gui/console.py` documents them as a pair, and "who is
        at a post" is read from the role.
        """
        GuiClient(client_id)
        add_role(client_id, "console, %s" % console)
        set_inventory_value(client_id, "CONSOLE_TYPE", console)

    def at(self, client_id, console):
        FrameContext.page = _Page(client_id, console)

    def send_to_science(self):
        return M.message_send("Your results are in.", to="science", sender="The Lab")


class TestNobodyIsAtThatPost(ForwardBase):
    """Helm and engineering are on the bridge; the science officer went down."""

    def setUp(self):
        super().setUp()
        self.sit(HELM, "helm")
        self.sit(ENG, "engineering")
        self.sit(SCI, "away")
        A._TEAM[SCI] = [501]
        self.send_to_science()

    def test_the_letter_is_not_simply_lost(self):
        """The whole point. Without forwarding this inbox is empty on every console."""
        self.at(HELM, "helm")
        reached = M.message_inbox("helm")
        self.at(ENG, "engineering")
        reached += M.message_inbox("engineering")
        self.at(SCI, "away")
        reached += M.message_inbox("away")
        self.assertTrue(reached)

    def test_it_reaches_the_console_that_is_covering(self):
        self.at(SCI, "away")
        self.assertEqual(len(M.message_inbox("away")), 1)

    def test_AND_ONLY_THAT_ONE(self):
        """Forwarded to everybody, a private letter becomes an announcement."""
        self.at(HELM, "helm")
        self.assertEqual(M.message_inbox("helm"), [])

    def test_the_reader_can_be_told_it_was_not_for_them(self):
        self.at(SCI, "away")
        msg = M.message_inbox("away")[0]
        self.assertEqual(M.message_forwarded_from(msg, "away", SCI), "science")

    def test_turning_forwarding_off_leaves_it_undelivered(self):
        M.message_forwarding(False)
        self.at(SCI, "away")
        self.assertEqual(M.message_inbox("away"), [])


class TestSomebodyIsAtThatPost(ForwardBase):
    """The ordinary case has to be untouched, or every private note leaks."""

    def setUp(self):
        super().setUp()
        self.sit(HELM, "helm")
        self.sit(SCI, "science")
        self.sit(ENG, "away")
        A._TEAM[ENG] = [501]
        self.send_to_science()

    def test_it_goes_to_science_as_always(self):
        self.at(SCI, "science")
        self.assertEqual(len(M.message_inbox("science")), 1)

    def test_and_is_not_also_forwarded(self):
        self.at(ENG, "away")
        self.assertEqual(M.message_inbox("away"), [])

    def test_a_reader_it_was_addressed_to_is_not_told_it_was_forwarded(self):
        self.at(SCI, "science")
        msg = M.message_inbox("science")[0]
        self.assertIsNone(M.message_forwarded_from(msg, "science", SCI))


class TestNobodyIsAway(ForwardBase):
    """No landing party, so nobody is missing and nothing is covering."""

    def setUp(self):
        super().setUp()
        self.sit(HELM, "helm")
        self.send_to_science()

    def test_an_unstaffed_post_forwards_nowhere(self):
        self.at(HELM, "helm")
        self.assertEqual(M.message_inbox("helm"), [])


class TestTheLiveAudiencesAreNeverForwarded(ForwardBase):
    """`away` and `ship` address whoever is there BY DEFINITION, so they can never be
    orphaned - and forwarding one would deliver every away broadcast twice."""

    def setUp(self):
        super().setUp()
        self.sit(HELM, "helm")
        self.sit(SCI, "away")
        A._TEAM[SCI] = [501]

    def test_an_away_broadcast_arrives_once(self):
        M.message_send("Report.", to="away", sender="The Bridge")
        self.at(SCI, "away")
        self.assertEqual(len(M.message_inbox("away")), 1)

    def test_a_ship_message_does_not_follow_them_down(self):
        M.message_send("Bridge only.", to="ship", sender="The Captain")
        self.at(SCI, "away")
        self.assertEqual(M.message_inbox("away"), [])

    def test_an_announcement_still_reaches_everyone(self):
        M.message_send("All hands.", sender="The Captain")
        self.at(HELM, "helm")
        self.assertEqual(len(M.message_inbox("helm")), 1)
        self.at(SCI, "away")
        self.assertEqual(len(M.message_inbox("away")), 1)


if __name__ == "__main__":
    unittest.main()
