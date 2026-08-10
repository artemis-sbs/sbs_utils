"""An orbit hail on the COMMS console points its radar, not a camera.

The main screen gets the cinematic shot. Comms deliberately does not: it has no 3D
view, and giving it one means taking the client's SHIP ASSIGNMENT - which is what the
engine ties `comms_control` and `comms_sorted_list` to, so the console would stop being
able to do its own job in order to watch a camera move.

What it does instead is look at whoever is calling: its own 2D radar follows the
subject, through the same `comms_set_2dview_focus` science already uses. That respects
the crew's Follow checkbox, and it hands the radar back.

    python -m unittest tests.test_hail_radar
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from cosmos_dev.mock import sbs as mock_sbs
from sbs_utils.agent import Agent, clear_shared
from sbs_utils.helpers import FrameContext, Context
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.procedural import hail as H
from sbs_utils.procedural.gui import hail_gui as HG
from sbs_utils.procedural.inventory import get_inventory_value, set_inventory_value
from sbs_utils.procedural.links import link
from sbs_utils.procedural.query import to_id
from sbs_utils.procedural.roles import add_role
from sbs_utils.procedural.spawn import player_spawn, npc_spawn

C_COMMS = 0x8000000000000001
C_HELM = 0x8000000000000002
NL = "\n"


class FakeEvent:
    client_id = 0
    tag = ""
    sub_tag = ""
    origin_id = 0
    selected_id = 0
    parent_id = 0
    value_tag = ""
    extra_tag = ""
    extra_extra_tag = ""
    sub_float = 0.0
    source_point = None
    event_time = 0


SCENES = {
    "call": {
        "key": "call",
        "data": {"speaker": "raider", "when": "hail", "presentation": "orbit"},
        "description": "You are a long way from friends." + NL + "- [Say nothing]()" + NL,
    },
    "portrait_call": {
        "key": "portrait_call",
        "data": {"speaker": "raider", "when": "hail", "presentation": "portrait"},
        "description": "Just a face." + NL + "- [Say nothing]()" + NL,
    },
}


def _console(cid, ship_id, *roles):
    agent = Agent()
    agent.id = cid
    agent.add()
    for r in roles:
        add_role(cid, r)
    link(ship_id, "consoles", cid)
    return cid


class RadarBase(unittest.TestCase):
    def setUp(self):
        mock_sbs.create_new_sim()
        SpaceObject.clear()
        Agent.clear()
        clear_shared()
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent())
        H.hail_reset()
        from sbs_utils.procedural import amd_dialogue as D
        D.dialogue_scenes_registry_clear()
        D.dialogue_register_scenes(SCENES)
        self.ship = to_id(player_spawn(0, 0, 0, "Artemis", "tsn", "battle"))
        self.raider = to_id(npc_spawn(0, 0, 4000, "Vex", "raider", "battle", "behav_npcship"))
        self.comms = _console(C_COMMS, self.ship, "console", "comms")
        # The crew's Follow checkbox, which this must obey rather than override.
        set_inventory_value(self.comms, "2d_follow", 1)

    def tearDown(self):
        FrameContext.context = None
        H.hail_reset()
        from sbs_utils.procedural import amd_dialogue as D
        D.dialogue_scenes_registry_clear()

    def open(self, scene="call", where="console"):
        H.hail_where_set(self.comms, where)
        H.hail_offer(self.ship, scene=scene, speaker="raider", subject=self.raider)
        H.hail_accept(self.ship)
        while H.hail_advance(self.ship):
            pass

    def aimed_at(self, cid=C_COMMS):
        return get_inventory_value(cid, "2dview_alt_ship_prev", 0)


class TheRadarFollowsTheCaller(RadarBase):
    def test_a_hail_with_a_subject_points_the_radar_at_it(self):
        self.open()
        HG._hail_radar_follow(self.ship, self.comms)
        self.assertEqual(self.aimed_at(), self.raider)

    def test_an_orbit_on_comms_still_DRAWS_as_a_portrait(self):
        # The camera stays unproven off the main screen, so the centre panel shows a
        # face. The radar is what gives comms the "look at them" half.
        self.open()
        self.assertEqual(H.hail_form(self.ship, self.comms), "portrait")

    def test_it_records_that_the_HAIL_took_the_radar(self):
        # So the release only undoes a follow this hail started.
        self.open()
        HG._hail_radar_follow(self.ship, self.comms)
        self.assertEqual(get_inventory_value(self.comms, H.KEY_RADAR, 0), self.raider)

    def test_a_hail_with_no_subject_leaves_the_radar_alone(self):
        # Nothing to look at - and picking something would be a directing decision.
        H.hail_where_set(self.comms, "console")
        H.hail_offer(self.ship, scene="portrait_call", speaker="raider")
        H.hail_accept(self.ship)
        HG._hail_radar_follow(self.ship, self.comms)
        self.assertEqual(self.aimed_at(), 0)


class ItGivesTheRadarBack(RadarBase):
    def test_closing_the_hail_releases_it(self):
        self.open()
        HG._hail_radar_follow(self.ship, self.comms)
        H.hail_close(self.ship)
        HG.hail_view(self.ship, self.comms)      # no hail: returns before drawing
        self.assertEqual(self.aimed_at(), 0)
        self.assertEqual(get_inventory_value(self.comms, H.KEY_RADAR, 0), 0)

    def test_switching_the_dial_off_releases_it(self):
        self.open()
        HG._hail_radar_follow(self.ship, self.comms)
        self.assertEqual(self.aimed_at(), self.raider)
        H.hail_where_set(self.comms, "off")
        HG._hail_radar_follow(self.ship, self.comms)
        self.assertEqual(self.aimed_at(), 0)

    def test_it_never_releases_a_radar_it_did_not_take(self):
        # A console the crew aimed themselves must not be reset by a hail closing.
        set_inventory_value(self.comms, "2dview_alt_ship_prev", self.raider)
        HG._hail_radar_release(self.comms)
        self.assertEqual(self.aimed_at(), self.raider)


class ItRespectsTheConsole(RadarBase):
    def test_a_non_comms_console_is_untouched(self):
        helm = _console(C_HELM, self.ship, "console", "helm")
        H.hail_where_set(helm, "console")
        self.open()
        HG._hail_radar_follow(self.ship, helm)
        self.assertEqual(self.aimed_at(helm), 0)

    def test_the_follow_checkbox_still_decides(self):
        # `comms_set_2dview_focus` sends 0 when Follow is off - the crew's switch wins.
        set_inventory_value(self.comms, "2d_follow", 0)
        self.open()
        HG._hail_radar_follow(self.ship, self.comms)
        self.assertEqual(self.aimed_at(), 0)


if __name__ == "__main__":
    unittest.main()
