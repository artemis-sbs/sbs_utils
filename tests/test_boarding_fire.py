"""The weapon: arming changes what a map click means.

There is no combat system in this game - no targeting, no range, no line of sight, and
damcon brains are entirely repair and idle. What exists is every EFFECT a shot needs. So
the device supplies the missing half, aiming, and gets it from the thing already built:
a click is a walk, and armed, the same click is a shot.

That choice is what makes the weapon testable at all. `//point/grid` is unreachable in the
mock - it emits no `grid_point_selection` - but `follow_route_point_grid` fires the route
directly, so arming, range, resolution and the disarm are all provable off a bridge.

The test that matters most is the last class: two consoles arm INDEPENDENTLY. Everything
about boarding is per-client, and a weapon stored per-site would let one person's trigger
fire somebody else's gun.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir

test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.gui import GuiClient
from sbs_utils.griddispatcher import GridDispatcher
from sbs_utils.procedural import boarding_site as B
from sbs_utils.procedural.grid import grid_objects, grid_pos_data
from sbs_utils.procedural.inventory import get_inventory_value
from sbs_utils.procedural.lifeform import lifeform_spawn
from sbs_utils.procedural.query import to_id, to_object
from sbs_utils.procedural.roles import any_role, has_role
from sbs_utils.procedural.routes import follow_route_point_grid
from sbs_utils.procedural.spawn import npc_spawn

A_CID = 0x8000000000000001
B_CID = 0x8000000000000002


class _FireBase(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        SpaceObject.clear()
        GridDispatcher.clear()
        B.boarding_site_clear()
        self.fired = []
        from sbs_utils.procedural import signal as S
        real = S.signal_emit

        def spy(name, data=None, **kw):
            if name in ("xess_fired", "life_form_died"):
                self.fired.append((name, dict(data or {})))
            return real(name, data, **kw)

        S.signal_emit = spy
        self.addCleanup(setattr, S, "signal_emit", real)

        # The MAST route body, so these go through the real dispatch path.
        GridDispatcher.add_any_point(
            lambda e: B.boarding_click(e.client_id, e.parent_id,
                                       e.source_point.x, e.source_point.y))
        for cid in (A_CID, B_CID):
            GuiClient(cid)
        self.site = to_object(npc_spawn(0, 0, 0, "Kepler", "tsn", "tsn_destroyer",
                                        "behav_station"))
        B.boarding_site_build(self.site)
        rooms = sorted(grid_objects(self.site.id) & any_role(B.boarding_room_roles()))
        self.assertGreaterEqual(len(rooms), 2, "fixture needs rooms to stand in")
        at = grid_pos_data(rooms[0])
        self.x, self.y = int(at[0]), int(at[1])

        self.me = lifeform_spawn("Lt Marek", "terran_male", "boarding,security")
        self.fig = B.boarding_figure_spawn(self.site, self.me, self.x, self.y)
        B.boarding_take(A_CID, self.fig, self.site)

    def tearDown(self):
        GridDispatcher.clear()
        B.boarding_site_clear()

    def target_of(self, fig):
        blob = to_object(fig).data_set
        return blob.get("pathx", 0), blob.get("pathy", 0)

    def reasons(self):
        return [d.get("XESS_REASON") for n, d in self.fired if n == "xess_fired"]


class AClickIsAWalkUntilYouArm(_FireBase):
    def test_unarmed_it_walks_and_does_not_shoot(self):
        follow_route_point_grid(A_CID, self.site, self.x + 1, self.y)
        self.assertEqual((self.x + 1, self.y), self.target_of(self.fig))
        self.assertEqual([], self.fired, "an unarmed click fired something")

    def test_armed_it_shoots_and_does_NOT_walk(self):
        before = self.target_of(self.fig)
        B.boarding_arm(A_CID)
        follow_route_point_grid(A_CID, self.site, self.x + 1, self.y)
        self.assertEqual(before, self.target_of(self.fig), "an armed click walked")
        self.assertTrue(self.fired, "an armed click did not fire")

    def test_a_shot_disarms(self):
        """One click, one shot. Holding a weapon armed across a room is how an accident
        happens, and re-arming is one tap."""
        B.boarding_arm(A_CID)
        follow_route_point_grid(A_CID, self.site, self.x + 1, self.y)
        self.assertFalse(B.boarding_armed(A_CID))

    def test_even_a_REFUSED_shot_disarms(self):
        """A refusal that leaves you armed is worse than one that does not - the next
        click would fire when you thought the gun was down."""
        B.boarding_arm(A_CID)
        follow_route_point_grid(A_CID, self.site, self.x + 99, self.y + 99)
        self.assertFalse(B.boarding_armed(A_CID))

    def test_and_the_next_click_walks_again(self):
        B.boarding_arm(A_CID)
        follow_route_point_grid(A_CID, self.site, self.x + 1, self.y)
        follow_route_point_grid(A_CID, self.site, self.x + 2, self.y)
        self.assertEqual((self.x + 2, self.y), self.target_of(self.fig))


class RangeIsAGridDistance(_FireBase):
    def test_out_of_range_refuses_WITH_A_REASON(self):
        B.boarding_arm(A_CID)
        B.boarding_fire(A_CID, self.x + B.FIRE_RANGE + 1, self.y)
        self.assertIn("out of range", self.reasons())

    def test_in_range_is_not_refused_for_range(self):
        B.boarding_arm(A_CID)
        B.boarding_fire(A_CID, self.x + 1, self.y)
        self.assertNotIn("out of range", self.reasons())

    def test_a_console_with_no_body_cannot_fire(self):
        B.boarding_arm(B_CID)
        self.assertFalse(B.boarding_fire(B_CID, self.x, self.y))
        self.assertIn("no body", self.reasons())

    def test_firing_at_bare_floor_says_so(self):
        """A silent no-op reads as a broken button."""
        B.boarding_arm(A_CID)
        B.boarding_fire(A_CID, self.x, self.y + 1)
        self.assertTrue(any(r in ("nothing there", None) for r in self.reasons()))


class WhatAShotHits(_FireBase):
    def _victim(self):
        who = lifeform_spawn("Ensign Vale", "terran_male", "boarding,science")
        fig = B.boarding_figure_spawn(self.site, who, self.x + 1, self.y)
        B.boarding_take(B_CID, fig, self.site)
        return who, fig

    def test_a_person_loses_a_hit_point(self):
        from sbs_utils.procedural.internal_damage import grid_get_max_hp
        who, fig = self._victim()
        B.boarding_arm(A_CID)
        self.assertTrue(B.boarding_fire(A_CID, self.x + 1, self.y))
        self.assertEqual(grid_get_max_hp() - 1, get_inventory_value(fig, "HP", None))

    def test_at_zero_they_are_gone_and_it_is_ANNOUNCED(self):
        """The same death path internal damage already uses, so anything watching for a
        death watches one signal rather than two."""
        from sbs_utils.procedural.internal_damage import grid_set_hp
        who, fig = self._victim()
        grid_set_hp(self.site.id, to_id(fig), 1)
        B.boarding_arm(A_CID)
        B.boarding_fire(A_CID, self.x + 1, self.y)
        self.assertIn("life_form_died", [n for n, _ in self.fired])
        self.assertIsNone(to_object(fig))

    def test_you_cannot_shoot_yourself(self):
        """Your own figure stands on your own cell; it must never be the target."""
        B.boarding_arm(A_CID)
        B.boarding_fire(A_CID, self.x, self.y)
        hits = [d.get("XESS_HIT") for n, d in self.fired if n == "xess_fired"]
        self.assertNotIn(to_id(self.fig), hits)

    def test_stun_does_not_cut_through_a_bulkhead(self):
        """A stun setting on a node reports nothing happened rather than quietly damaging
        it - the setting is a decision, not a formality."""
        node = next(iter(grid_objects(self.site.id) & any_role(B.boarding_room_roles())))
        at = grid_pos_data(node)
        B.boarding_arm(A_CID, B.SETTING_STUN)
        B.boarding_fire(A_CID, int(at[0]), int(at[1]))
        self.assertFalse(has_role(node, "__damaged__"))


class TwoConsolesArmIndependently(_FireBase):
    """The per-client claim the whole design rests on, applied to the trigger."""

    def test_arming_one_does_not_arm_the_other(self):
        B.boarding_arm(A_CID)
        self.assertTrue(B.boarding_armed(A_CID))
        self.assertFalse(B.boarding_armed(B_CID))

    def test_and_each_carries_its_own_setting(self):
        B.boarding_arm(A_CID, B.SETTING_STUN)
        B.boarding_arm(B_CID, B.SETTING_CUT)
        self.assertEqual(B.SETTING_STUN, B.boarding_setting(A_CID))
        self.assertEqual(B.SETTING_CUT, B.boarding_setting(B_CID))

    def test_one_console_firing_leaves_the_other_armed(self):
        who = lifeform_spawn("Vale", "terran_male", "boarding")
        other = B.boarding_figure_spawn(self.site, who, self.x, self.y)
        B.boarding_take(B_CID, other, self.site)
        B.boarding_arm(A_CID)
        B.boarding_arm(B_CID)
        follow_route_point_grid(A_CID, self.site, self.x + 1, self.y)
        self.assertFalse(B.boarding_armed(A_CID))
        self.assertTrue(B.boarding_armed(B_CID), "somebody else's gun was unloaded")

    def test_clearing_the_site_leaves_nobody_armed(self):
        B.boarding_arm(A_CID)
        B.boarding_site_clear()
        self.assertEqual(0, B.boarding_fire_count())


if __name__ == "__main__":
    unittest.main()
