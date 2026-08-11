"""The particle layer: descriptors, slots, budget, cleanup, and the AMD looks.

The mock draws nothing - particles are client-render-only - so nothing here is a
claim about what a frame LOOKS like. What it does test is everything around the
picture: that a descriptor is built the same way twice, that a slot cannot double
up, that an emitter is deleted in the ENGINE and not merely forgotten, that the
budget refuses rather than sprinkles, and that a build-up tears itself down even if
nobody stops it. Those are exactly the failures that are invisible in a playtest
until the third mission of a session.

The appearance is judged in the Visual Test Range (`--map visual_particles`) against
the real engine, and nowhere else.
"""

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from cosmos_dev.mock import sbs
from sbs_utils.handlerhooks import reset_mission_state, reset_mission_audit
from sbs_utils.helpers import FrameContext
from sbs_utils.tickdispatcher import TickDispatcher
from sbs_utils.procedural import particles as P
from sbs_utils.procedural import amd_effects as E
from sbs_utils.procedural.amd_doc import amd_document, amd_section
from sbs_utils.procedural.spawn import npc_spawn
from sbs_utils.procedural.query import to_object
from sbs_utils.vec import Vec3
from tests.reset_helper import reset_mock


EFFECT_DOC = (
    "# [Looks](looks)\n\n"
    "## [Effects](effects)\n\n"
    "### [Coil charge](coil)\n"
    "---\n"
    "Effect\n"
    "Look: charge\n"
    "Color: #8cf, white\n"
    "Size: 0.6 -> 2.0\n"
    "Count: 10 -> 80\n"
    "Grows over: 2 seconds\n"
    "On: hull\n"
    "---\n"
    "Drive coils biting down.\n\n"
    "### [Closing field](veil_charge)\n"
    "---\n"
    "Effect\n"
    "Look: charge\n"
    "Offset: 0, 0, 400 -> 0, 0, 0\n"
    "Size: 12 -> 2\n"
    "---\n"
    "A field closing onto the hull.\n"
)


def _tick(seconds):
    """Advance the mock sim and run the tick dispatcher for that long."""
    for _ in range(int(seconds * TickDispatcher.tps)):
        sbs.sim._time_tick_counter += 1
        TickDispatcher.dispatch_tick()


class TestParticles(unittest.TestCase):
    def setUp(self):
        reset_mock(sbs)
        P.particle_budget(24)
        self.a = npc_spawn(0, 0, 0, "A", "tsn", "tsn_light_cruiser", "behav_npcship")
        self.b = npc_spawn(5000, 0, 0, "B", "tsn", "tsn_light_cruiser", "behav_npcship")

    # --- the descriptor string -------------------------------------------------

    def test_descriptor_format(self):
        """Fixed key order, engine spelling, and no float noise."""
        self.assertEqual(
            P.particle_descriptor(count=50, color="black", align=True, smoke=True,
                                  shape="hull", lifespan=60, image_cell=4,
                                  size=12, speed=0),
            "align: True; smoke: True; shape: hull; color: black; lifespan: 60; "
            "image_cell: 4; size: 12; speed: 0; count: 50")
        # Order comes from _KEY_ORDER, NOT from the order the kwargs were typed.
        self.assertEqual(P.particle_descriptor(count=10, align=True),
                         P.particle_descriptor(align=True, count=10))
        # A pair is the grammar's "random between" - rendered with no space.
        self.assertEqual(P.particle_descriptor(image_cell=(0, 3)), "image_cell: 0,3")
        self.assertEqual(P.particle_descriptor(count=[100, 1000]), "count: 100,1000")
        self.assertEqual(P.particle_descriptor(offset=(0, 0, 200)), "offset: 0,0,200")
        # False must survive - it is meaningful, and `if v:` would drop it.
        self.assertEqual(P.particle_descriptor(align=False), "align: False")
        # No float noise, and None is omitted rather than rendered.
        self.assertEqual(P.particle_descriptor(size=0.1 + 0.7), "size: 0.8")
        self.assertEqual(P.particle_descriptor(size=None, count=1), "count: 1")
        self.assertFalse(P.particle_descriptor(count=1).endswith(";"))

    def test_preset_resolution(self):
        """A preset resolves, an override composes, an unknown one is survivable."""
        smoke = P.particle_preset("smoke")
        self.assertIn("smoke: True", smoke)
        self.assertIn("shape: hull", smoke)
        self.assertIn("count: 50", smoke)
        # An override touches only what it names.
        self.assertEqual(P.particle_preset("smoke", count=8),
                         smoke.replace("count: 50", "count: 8"))
        # Unknown: None, no raise, and nothing emitted.
        before = len(sbs.particle_emittors())
        self.assertIsNone(P.particle_preset("no_such_look"))
        self.assertIsNone(P.particle_effect(self.a.id, "no_such_look"))
        self.assertFalse(P.particle_burst(self.a.id, "no_such_look"))
        self.assertEqual(len(sbs.particle_emittors()), before)

    def test_burst_routes_to_the_right_engine_call(self):
        """A point goes to particle_at, an object to particle_on.

        Wrapped HERE rather than logged by the mock: bursts have no handle and
        nothing to clean up, so the mock has no reason to model them.
        """
        seen = []
        at, on = sbs.particle_at, sbs.particle_on
        sbs.particle_at = lambda pos, desc: seen.append(("at", desc))
        sbs.particle_on = lambda eo, desc: seen.append(("on", desc))
        try:
            P.particle_burst(Vec3(1, 2, 3), "dust")
            P.particle_burst((1, 2, 3), "dust")
            P.particle_burst(self.a.id, "pickup")
        finally:
            sbs.particle_at, sbs.particle_on = at, on
        self.assertEqual([k for k, _ in seen], ["at", "at", "on"])

    # --- the slot registry -----------------------------------------------------

    def test_effect_lifecycle(self):
        eid = P.particle_effect(self.a.id, "smoke")
        self.assertTrue(eid)                       # truthy: ids start at 1, not 0
        self.assertTrue(sbs.particle_emittor_exists(eid))
        self.assertEqual(P.particle_count(), 1)
        self.assertTrue(P.particle_effect_active(self.a.id, "smoke"))

        self.assertEqual(P.particle_effect_clear(self.a.id, "smoke"), 1)
        self.assertFalse(sbs.particle_emittor_exists(eid))
        self.assertEqual(P.particle_count(), 0)
        self.assertEqual(len(sbs.particle_emittors()), 0)

    def test_slot_replaces_instead_of_doubling(self):
        """The rule that makes this safe to call from a loop."""
        first = P.particle_effect(self.a.id, "smoke")
        second = P.particle_effect(self.a.id, "smoke")
        self.assertNotEqual(first, second)
        self.assertEqual(P.particle_count(), 1)
        self.assertEqual(len(sbs.particle_emittors()), 1)   # the engine agrees
        self.assertFalse(sbs.particle_emittor_exists(first))

        # A DIFFERENT slot on the same object is a second effect, not a replacement.
        P.particle_effect(self.a.id, "ember")
        self.assertEqual(P.particle_effect_slots(self.a.id), ["ember", "smoke"])
        self.assertEqual(P.particle_effect_clear(self.a.id), 2)

    def test_destroy_route_clears(self):
        P.particle_effect(self.a.id, "smoke")
        P._on_destroy(self.a)                      # what LifetimeDispatcher calls
        self.assertEqual(P.particle_count(), 0)
        self.assertEqual(len(sbs.particle_emittors()), 0)

    def test_janitor_catches_a_box_delete(self):
        """The case the destroy route CANNOT catch, and the reason it exists.

        OU's universe_clear_cell box-deletes a whole system, and standby culling
        removes objects too - neither routes a destroy event, and a warp jump does
        exactly that one line after a charge-up.
        """
        eid = P.particle_effect(self.a.id, "smoke")
        oid = self.a.id
        sbs.delete_object(oid)                     # no destroy route fires
        self.assertEqual(P.particle_count(), 1)    # still on the books...
        self.assertTrue(sbs.particle_emittor_exists(eid))

        _tick(P._JANITOR_SECONDS + 1)
        self.assertEqual(P.particle_count(), 0)    # ...until the janitor reconciles
        self.assertFalse(sbs.particle_emittor_exists(eid))

    def test_janitor_follows_the_engine_dropping_an_emitter(self):
        """If the engine reaps one itself, the count must not over-report."""
        eid = P.particle_effect(self.a.id, "smoke")
        sbs.delete_particle_emittor(eid)           # as if the engine had
        _tick(P._JANITOR_SECONDS + 1)
        self.assertEqual(P.particle_count(), 0)

    # --- the budget ------------------------------------------------------------

    def test_budget_refuses_rather_than_sprinkling(self):
        P.particle_budget(2)
        self.assertTrue(P.particle_effect(self.a.id, "smoke"))
        self.assertTrue(P.particle_effect(self.a.id, "ember"))
        self.assertIsNone(P.particle_effect(self.a.id, "charge"))
        self.assertEqual(P.particle_count(), 2)
        self.assertEqual(len(sbs.particle_emittors()), 2)
        self.assertEqual(P.particle_budget_refused(), 1)

    def test_budget_priority_evicts_the_oldest_lower(self):
        P.particle_budget(2)
        P.particle_effect(self.a.id, "smoke")          # oldest, priority 0
        P.particle_effect(self.a.id, "ember")          # newer, priority 0
        self.assertTrue(P.particle_effect(self.b.id, "charge", priority=10))
        self.assertEqual(P.particle_count(), 2)
        # The OLDEST low-priority row went, not an arbitrary one.
        self.assertEqual(P.particle_effect_slots(self.a.id), ["ember"])
        self.assertEqual(P.particle_effect_slots(self.b.id), ["charge"])

    def test_equal_priority_does_not_evict(self):
        """Priority is an explicit escape hatch, not a free-for-all."""
        P.particle_budget(1)
        P.particle_effect(self.a.id, "smoke", priority=5)
        self.assertIsNone(P.particle_effect(self.b.id, "ember", priority=5))
        self.assertEqual(P.particle_count(), 1)

    # --- the charge-up ---------------------------------------------------------

    def test_charge_ramps_and_ends_itself(self):
        """Monotonic, one emitter throughout, and self-limiting."""
        self.assertTrue(P.particle_charge_start(self.a.id, "coil", seconds=2.0,
                                                color="#cc2244", steps=5))
        counts, sizes, live_seen = [], [], []
        for _ in range(5):
            rows = list(P._LIVE.values())
            live_seen.append(len(rows))
            desc = rows[0]["desc"]
            counts.append(int(desc.split("count: ")[1].split(";")[0]))
            sizes.append(float(desc.split("size: ")[1].split(";")[0]))
            _tick(0.4)
        self.assertEqual(counts, sorted(counts))
        self.assertEqual(sizes, sorted(sizes))
        self.assertLess(counts[0], counts[-1])
        self.assertEqual(set(live_seen), {1})      # never two at once

        # NOBODY calls stop. It has to end anyway.
        _tick(1.0)
        self.assertEqual(P.particle_count(), 0)
        self.assertEqual(P.particle_charge_count(), 0)
        self.assertEqual(len(sbs.particle_emittors()), 0)

    def test_charge_survives_its_ship_being_deleted(self):
        """An aborted jump / culled cell must not leave one burning."""
        P.particle_charge_start(self.a.id, "coil", seconds=2.0)
        sbs.delete_object(self.a.id)
        _tick(3.0)
        self.assertEqual(P.particle_count(), 0)
        self.assertEqual(P.particle_charge_count(), 0)

    def test_charge_falls_back_to_pulse_when_refused(self):
        """Going silent would read as a bug; the degrade path holds no emitter."""
        P.particle_budget(1)
        P.particle_effect(self.b.id, "smoke", priority=99)   # fill it with a winner
        self.assertTrue(P.particle_charge_start(self.a.id, "coil", seconds=1.0, steps=3))
        _tick(1.5)
        self.assertEqual(P.particle_effect_slots(self.a.id), [])
        self.assertEqual(P.particle_budget_refused(), 1)     # refused ONCE, then bursts

    def test_charge_seconds_zero_is_the_off_valve(self):
        """Setting the duration to 0 restores a hard cut exactly."""
        self.assertFalse(P.particle_charge_start(self.a.id, "coil", seconds=0))
        self.assertEqual(P.particle_count(), 0)
        self.assertEqual(P.particle_charge_count(), 0)

    def test_unknown_charge_look_still_charges(self):
        self.assertTrue(P.particle_charge_start(self.a.id, "no_such_look", seconds=1.0))
        self.assertEqual(P.particle_count(), 1)
        P.particle_charge_stop(self.a.id)

    # --- mission reset ---------------------------------------------------------

    def test_reset_leaves_nothing_in_the_engine(self):
        """The half that is easy to skip: emptying the dict is not deleting them."""
        P.particle_effect(self.a.id, "smoke")
        P.particle_effect(self.a.id, "ember")
        P.particle_charge_start(self.b.id, "coil", seconds=5.0)
        P.particle_preset_define("mission_only", color="red", count=5)
        E.amd_effects(amd_section(amd_document(EFFECT_DOC), "effects"))
        self.assertTrue(sbs.particle_emittors())

        reset_mission_state()

        # Nothing this layer owns is left on the books. (The audit still lists the
        # mock's own space objects - clearing those is create_new_sim's job, not
        # reset_mission_state's, so scope the assertion to what is under test.)
        audit = reset_mission_audit()
        self.assertEqual({k: v for k, v in audit.items()
                          if "particle" in k or "effect" in k}, {})
        self.assertEqual(len(sbs.particle_emittors()), 0)   # deleted, not just forgotten
        self.assertEqual(P.particle_charge_count(), 0)
        self.assertIsNone(P.particle_preset("mission_only"))
        self.assertEqual(E.effect_amd_names(), [])
        self.assertIsNotNone(P.particle_preset("smoke"))    # built-ins survive

    # --- the AMD layer ---------------------------------------------------------

    def test_amd_effect_types_as_effect_not_landmark(self):
        """`Kind:` infers landmark - the trap the bare `Effect` noun exists to dodge."""
        from sbs_utils.procedural.amd_schema import archetype_for_section, infer_archetype
        self.assertEqual(archetype_for_section("Effects"), "effect")
        self.assertEqual(archetype_for_section("Looks"), "effect")
        # A flat record with no section to name it is typed by carrying `Look:`.
        self.assertEqual(infer_archetype(["look"]), "effect")
        # And the trap itself is still live, which is WHY the bare noun is used.
        self.assertEqual(infer_archetype(["kind"]), "landmark")

    def test_amd_ramp_is_pure_arithmetic(self):
        n = E.amd_effects(amd_section(amd_document(EFFECT_DOC), "effects"))
        self.assertEqual(n, 2)
        self.assertEqual(E.effect_amd_names(), ["coil", "veil_charge"])

        lo = E.effect_amd_descriptor("coil", 0.0)
        hi = E.effect_amd_descriptor("coil", 1.0)
        self.assertIn("count: 10", lo)
        self.assertIn("count: 80", hi)
        self.assertIn("size: 0.6", lo)
        self.assertIn("size: 2", hi)
        # `Look: charge` supplied the base the record never restated.
        self.assertIn("shape: hull", lo)
        # A comma pair is "random between" - normalized, and NOT interpolated.
        self.assertIn("color: #8cf,white", lo)
        self.assertIn("color: #8cf,white", hi)
        # No engine was touched.
        self.assertEqual(len(sbs.particle_emittors()), 0)

    def test_amd_offset_ramp_closes_in(self):
        E.amd_effects(amd_section(amd_document(EFFECT_DOC), "effects"))
        self.assertIn("offset: 0,0,400", E.effect_amd_descriptor("veil_charge", 0.0))
        self.assertIn("offset: 0,0,200", E.effect_amd_descriptor("veil_charge", 0.5))
        self.assertIn("offset: 0,0,0", E.effect_amd_descriptor("veil_charge", 1.0))

    def test_amd_record_shadows_a_builtin_look(self):
        """The resolution contract: authored first, shipped second.

        All three layers are nameable, so all three have to answer - a side writing
        `Jump Charge: coil` names a built-in CHARGE look, and a caller asking "does
        this resolve?" has to get a truthful yes for it rather than None.
        """
        self.assertEqual(E.effect_amd_look("smoke"), "preset")   # attachable table
        self.assertEqual(E.effect_amd_look("coil"), "charge")    # built-in build-up
        self.assertIsNone(E.effect_amd_look("no_such_look"))

        E.amd_effects(amd_section(amd_document(EFFECT_DOC), "effects"))
        self.assertEqual(E.effect_amd_look("coil"), "amd")       # authored wins
        E.amd_effects_clear()
        self.assertEqual(E.effect_amd_look("coil"), "charge")    # and falls back

    def test_amd_charge_falls_through_to_a_builtin_look(self):
        """`Jump Charge: coil` has to work with nothing authored at all."""
        self.assertTrue(E.effect_amd_charge("coil", self.a.id, seconds=1.0))
        self.assertEqual(P.particle_count(), 1)
        P.particle_charge_stop(self.a.id)
        self.assertEqual(P.particle_count(), 0)

    def test_amd_charge_uses_a_declared_look(self):
        E.amd_effects(amd_section(amd_document(EFFECT_DOC), "effects"))
        self.assertTrue(E.effect_amd_charge("coil", self.a.id))
        rows = list(P._LIVE.values())
        self.assertEqual(len(rows), 1)
        self.assertIn("count: 10", rows[0]["desc"])   # starts at the ramp's floor
        P.particle_charge_stop(self.a.id)


if __name__ == "__main__":
    unittest.main()
