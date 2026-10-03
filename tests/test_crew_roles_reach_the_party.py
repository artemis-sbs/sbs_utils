"""A crew member's `Roles:` reaches the console they sit at, and the body they board as.

`Roles:` on a roster member is what a boarding scene guards on - `if medical` - and it
went no further than the record it was read into. `crew_member_record` kept it inside
`data`; `_member_post` asked the member for `roles`; the post came back with none. So the
ship's surgeon boarded as "science", because that was the seat she left.

Nothing failed. `tests/test_boarding_crew.py` writes `CREW_ROLES` onto the client by hand,
which is the thing `crew_assign` is supposed to publish, so it passed throughout; and a
crew party turns job forwarding on, so in play the medic's line still appeared - on
whichever console was lowest, marked as covering for somebody who was standing right there.

Everything here goes in the front door: a roster written as AMD, `crew_assign`, then the
party built from the consoles.

    python -m unittest tests.test_crew_roles_reach_the_party
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs as sbs
from tests.reset_helper import reset_mock

from sbs_utils.gui import GuiClient
from sbs_utils.procedural import boarding as A
from sbs_utils.procedural import crew
from sbs_utils.procedural.amd_crew import amd_crew_data
from sbs_utils.procedural.amd_doc import amd_document
from sbs_utils.procedural.inventory import get_inventory_value, set_inventory_value
from sbs_utils.procedural.query import to_id
from sbs_utils.procedural.roles import has_role
from sbs_utils.procedural.sides import side_ensure
from sbs_utils.procedural.spawn import player_spawn

SCI = 0x8000000000000001
ENG = 0x8000000000000002
HELM = 0x8000000000000003

ROSTER = """# [Mission](mission)

## [The Watch](watch)
---
crew
Ship: Artemis
---
The bridge crew.

### [Dr Hale](hale)
---
Rank: Lieutenant
Console: science
Roles: medical
---

### [Chief Okoro](okoro)
---
Console: engineering
Roles: engineering, security
---

### [Ensign Vale](vale)
---
Console: helm
---
"""


class RolesReachThePartyTests(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)
        crew.crew_clear()
        A.boarding_clear()
        self.addCleanup(crew.crew_clear)
        self.addCleanup(A.boarding_clear)
        side_ensure("tsn")
        self.ship = to_id(player_spawn(0, 0, 0, "Artemis", "tsn", "tsn_light_cruiser"))
        crew.crew_declare_amd(amd_document(ROSTER, data_parser=amd_crew_data))

    def sit(self, client_id, console):
        GuiClient(client_id)
        set_inventory_value(client_id, "CONSOLE_TYPE", console)
        return crew.crew_assign(client_id, self.ship, console)

    def body_of(self, client_id):
        bodies = A.boarding_crew_roster(self.ship, consoles=[client_id], assign_missing=False)
        self.assertEqual(len(bodies), 1)
        return bodies[0]

    def test_the_roster_seats_the_person_it_says(self):
        """The fixture is real: this is the cast, by console."""
        self.assertEqual(self.sit(SCI, "science").name, "Dr Hale")

    def test_roles_are_published_on_the_console(self):
        self.sit(SCI, "science")
        self.assertEqual(get_inventory_value(SCI, "CREW_ROLES", None), "medical")

    def test_several_roles_all_arrive(self):
        self.sit(ENG, "engineering")
        published = [w.strip() for w in get_inventory_value(ENG, "CREW_ROLES", "").split(",")]
        self.assertEqual(published, ["engineering", "security"])

    def test_the_body_wears_the_authored_role_not_the_seat(self):
        """The surgeon boards as a medic. She sat at science; that is not what she is."""
        self.sit(SCI, "science")
        body = self.body_of(SCI)
        self.assertTrue(has_role(body, "medical"))
        self.assertIn("medical", A.boarding_jobs(body))
        self.assertFalse(has_role(body, "science"))

    def test_a_member_with_no_roles_still_falls_back_to_the_seat(self):
        self.sit(HELM, "helm")
        self.assertTrue(has_role(self.body_of(HELM), "helm"))


if __name__ == "__main__":
    unittest.main()
