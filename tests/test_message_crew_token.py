"""Addressing ONE BOARDER by name.

Everything else in `messages.py` addresses a CONSOLE, which is right on a bridge: "To:
science" reaches whoever is sitting there. It falls apart on a boarding party, because
every boarded console reports the same name - `_here()` -> CONSOLE_TYPE ->
BOARDING_CONSOLE - so two crew members standing in different rooms are the same
addressee and there is no way to say "Marek, not Ana".

`crew:<lifeform>` addresses the BODY somebody is wearing, resolved when the inbox is
READ, so the letter follows the person rather than the seat.

THE TEST THAT MATTERS MOST is the second class. A `crew:` token is not in `_staffed()`,
which holds console-type names, so the obvious implementation marks every direct call
orphaned and copies it to the duty console - a silent double delivery, which is the
worst shape a delivery bug can take. It reaches one person only when somebody is
actually wearing the body.
"""
from sbs_utils.fs import test_set_exe_dir

test_set_exe_dir()

import unittest

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs
from sbs_utils.agent import clear_shared
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.procedural import boarding as BD
from sbs_utils.procedural.lifeform import lifeform_spawn
from sbs_utils.procedural.messages import (
    message_send, message_inbox, message_crew_token, message_forwarded_from,
    message_forwarding, message_clear)
from sbs_utils.procedural.query import to_id

MAREK_CID = 0x8000000000000001
ANA_CID = 0x8000000000000002
BRIDGE_CID = 0x8000000000000003


class _Page:
    def __init__(self, console, client_id):
        self.console = console
        self.client_id = client_id
        self.gui_task = None


class _CrewBase(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(0, "test"))
        FrameContext.page = None
        SpaceObject.clear()
        clear_shared()
        message_clear()
        BD.boarding_team_clear()
        self.addCleanup(BD.boarding_team_clear)
        self.addCleanup(setattr, FrameContext, "page", None)

        self.marek = lifeform_spawn("Marek Sol", "terran_male", "boarding,engineer")
        self.ana = lifeform_spawn("Ana Ruiz", "terran_female", "boarding,science")
        BD.boarding_assign(MAREK_CID, self.marek)
        BD.boarding_assign(ANA_CID, self.ana)

    def at_boarder(self, client_id):
        """Read as one of the party. Both boarded consoles report the SAME console name -
        that sameness is the whole problem this token solves, so the fixture keeps it."""
        FrameContext.page = _Page(BD.BOARDING_CONSOLE, client_id)

    def at_bridge(self, console="science"):
        FrameContext.page = _Page(console, BRIDGE_CID)

    def subjects(self):
        return [m["text"] for m in message_inbox()]


class ItReachesOnePerson(_CrewBase):
    def test_the_person_addressed_gets_it(self):
        message_send("Watch the gallery.", to=message_crew_token(self.marek),
                     sender="Artemis")
        self.at_boarder(MAREK_CID)
        self.assertIn("Watch the gallery.", self.subjects())

    def test_and_the_one_beside_them_does_NOT(self):
        """The claim the whole token exists for. Both consoles are the same console
        NAME, so anything keyed on the name alone fails here."""
        message_send("Watch the gallery.", to=message_crew_token(self.marek),
                     sender="Artemis")
        self.at_boarder(ANA_CID)
        self.assertNotIn("Watch the gallery.", self.subjects())

    def test_a_bridge_console_does_not_get_it_either(self):
        message_send("Watch the gallery.", to=message_crew_token(self.marek),
                     sender="Artemis")
        self.at_bridge()
        self.assertNotIn("Watch the gallery.", self.subjects())

    def test_the_token_takes_an_id_or_an_object(self):
        self.assertEqual(message_crew_token(self.marek),
                         message_crew_token(to_id(self.marek)))

    def test_a_console_holding_TWO_characters_gets_both_their_mail(self):
        """`boarding_assign_also` exists because a party smaller than its cast leaves
        characters nobody speaks for. Mail to a character you are carrying is mail to
        you, or those characters become unreachable the moment they are doubled up."""
        BD.boarding_team_clear()
        BD.boarding_assign(MAREK_CID, self.marek)
        BD.boarding_assign_also(MAREK_CID, self.ana)
        message_send("Ana, the manifest.", to=message_crew_token(self.ana),
                     sender="Artemis")
        self.at_boarder(MAREK_CID)
        self.assertIn("Ana, the manifest.", self.subjects())

    def test_a_broadcast_still_reaches_everybody(self):
        """The token must not narrow anything it was not asked to narrow."""
        message_send("All hands.", sender="The Captain")
        for cid in (MAREK_CID, ANA_CID):
            self.at_boarder(cid)
            self.assertIn("All hands.", self.subjects())


class ItIsNotForwardedWhileItsPersonIsThere(_CrewBase):
    """A `crew:` token is never in `_staffed()`, so the obvious implementation treats
    every direct call as mail to an empty chair and copies it to whoever is covering.
    That is a silent double delivery: the intended reader still gets it, so nothing
    looks broken until somebody notices their private mail on a colleague's screen."""

    def setUp(self):
        super().setUp()
        message_forwarding(True)
        self.addCleanup(message_forwarding, True)
        # THE DUTY CONSOLE IS THE LOWEST CLIENT ID (`boarding_duty_client`), which is
        # MAREK. So every test here addresses ANA: with Marek as both the addressee and
        # the console that would catch a forward, a double delivery is indistinguishable
        # from a correct one and the test proves nothing. It passed either way until
        # this line was written.
        self.assertEqual(MAREK_CID, BD.boarding_duty_client(),
                         "fixture assumes Marek is the duty console")

    def test_the_duty_console_does_not_get_a_copy(self):
        message_send("Between us.", to=message_crew_token(self.ana), sender="Artemis")
        self.at_boarder(MAREK_CID)
        self.assertNotIn("Between us.", self.subjects())

    def test_the_person_addressed_still_gets_it(self):
        message_send("Between us.", to=message_crew_token(self.ana), sender="Artemis")
        self.at_boarder(ANA_CID)
        self.assertIn("Between us.", self.subjects())

    def test_nor_does_a_bridge_console(self):
        message_send("Between us.", to=message_crew_token(self.ana), sender="Artemis")
        self.at_bridge("comms")
        self.assertNotIn("Between us.", self.subjects())

    def test_but_mail_for_somebody_NOT_down_there_still_forwards(self):
        """The person-shaped twin of an empty chair, and the one case where a direct
        call should reach somebody else."""
        absent = lifeform_spawn("Kai Osei", "terran_male", "boarding,medical")
        message_send("Kai, the samples.", to=message_crew_token(absent),
                     sender="Artemis")
        self.at_boarder(MAREK_CID)
        self.assertIn("Kai, the samples.", self.subjects())

    def test_and_says_WHOSE_work_was_picked_up_by_name(self):
        """"covering for crew:1074" tells a crew member nothing; the point of the label
        is that they can see whose job they took."""
        absent = lifeform_spawn("Kai Osei", "terran_male", "boarding,medical")
        message_send("Kai, the samples.", to=message_crew_token(absent),
                     sender="Artemis")
        self.at_boarder(MAREK_CID)
        msg = message_inbox()[0]
        self.assertEqual("Kai Osei", message_forwarded_from(msg))

    def test_the_person_addressed_is_not_told_they_are_covering(self):
        message_send("Between us.", to=message_crew_token(self.ana), sender="Artemis")
        self.at_boarder(ANA_CID)
        msg = message_inbox()[0]
        self.assertIsNone(message_forwarded_from(msg))


if __name__ == "__main__":
    unittest.main()
