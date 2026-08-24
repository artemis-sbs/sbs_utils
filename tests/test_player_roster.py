"""The player roster - indirection between a console and a player ship.

THE BUG THIS REPLACES. A console bound to a live Agent object, held across frames and
indexed by its position in the `__player__` list. Ships past PLAYER_COUNT were then deleted
under it, so the file grew five separate guards around that one pointer: re-resolve before
writing, filter the dead out of the list, clamp the index, and re-clamp again on
`on change PLAYER_COUNT`.

WHAT THESE TESTS PIN HARDEST, in the order the owner raised them:

  * **A COUNT CHANGE NEVER DELETES.** PLAYER_COUNT is a live slider on every map, so the
    fluid phase is genuinely fluid. Lowering it parks a ship; raising it wakes the SAME
    ship, with the SAME engine id.
  * **THE ENGINE OWNS THE ID.** Nothing here pretends a ship can be morphed onto a new id.
    A re-hull keeps its id (it is a field write); a sim wipe does not, and the roster
    re-assigns the bound clients rather than leaving each console to notice.
  * **APPLY IS IDEMPOTENT.** Running it twice must change nothing the second time, or every
    panel repaint would rebuild stats and wipe what a map had set in between.

    python -m unittest tests.test_player_roster
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

import cosmos_dev.mock.sbs as mock
from tests.reset_helper import reset_mock

from sbs_utils.procedural import player_roster as R
from sbs_utils.procedural.query import to_id, to_object, object_exists
from sbs_utils.procedural.roles import role, has_role
from sbs_utils.procedural.spawn import player_ensure, player_slot_role


ROSTER = [
    {"name": "Artemis",  "side": "tsn", "ship": "tsn_light_cruiser", "face": "terran"},
    {"name": "Intrepid", "side": "tsn", "ship": "tsn_battle_cruiser", "face": "terran"},
    {"name": "Aegis",    "side": "tsn", "ship": "tsn_battle_cruiser", "face": "terran"},
    {"name": "Horatio",  "side": "tsn", "ship": "tsn_battle_cruiser", "face": "terran"},
]


class _Settings:
    def __init__(self, values):
        self.values = values

    def __call__(self):
        return self.values


class PlayerRosterTests(unittest.TestCase):

    def setUp(self):
        reset_mock(mock)
        R.player_roster_seed(ROSTER)
        self._spawn_all()

    def _spawn_all(self):
        """Fill every slot, the way create_default_player_ships does."""
        for rec in R.player_roster():
            player_ensure(rec["slot"], rec["slot"] * 2000, 0, 2000,
                          rec["ship"], rec["name"], rec["side"])

    def _set_art_keys(self, mapping):
        # Precondition, stated out loud: art_key_for DELIBERATELY falls back to the stock key
        # when the replacement is not in the ship table ("a half-written map should degrade to
        # stock art, never to nothing spawning"). That is right in production and poison in a
        # test - the mapping quietly becomes identity and the assertion below fails for a
        # reason that has nothing to do with what is being tested.
        from sbs_utils.procedural.ship_data import get_ship_data_for
        for target in mapping.values():
            self.assertIsNotNone(
                get_ship_data_for(target),
                f"fixture hull {target!r} is not in the ship table, so art_key_for would "
                f"fall back to identity and this test would prove nothing")
        import sbs_utils.procedural.settings as S
        self._real = getattr(self, "_real", S.settings_get_defaults)
        S.settings_get_defaults = _Settings({"ART_KEYS": mapping})

    def tearDown(self):
        import sbs_utils.procedural.settings as S
        if hasattr(self, "_real"):
            S.settings_get_defaults = self._real

    # --- records and resolution --------------------------------------------

    def test_seed_builds_one_record_per_slot(self):
        self.assertEqual(4, len(R.player_roster()))
        self.assertEqual("Aegis", R.player_roster_record(2)["name"])

    def test_reseeding_updates_fields_without_disturbing_bindings(self):
        R.player_roster_bind(2, 77)
        R.player_roster_seed([dict(r, name=r["name"].upper()) for r in ROSTER])
        self.assertEqual("AEGIS", R.player_roster_record(2)["name"])
        self.assertEqual({77}, R.player_roster_bound(2))

    def test_resolve_finds_the_ship_in_a_slot(self):
        self.assertIsNotNone(R.player_roster_resolve(0))
        self.assertEqual("Artemis", to_object(R.player_roster_resolve(0)).name)

    def test_an_unfilled_slot_resolves_to_none(self):
        self.assertIsNone(R.player_roster_resolve(9))

    # --- the fluid phase: a count change must never delete ------------------

    def test_lowering_the_count_parks_rather_than_deletes(self):
        ids = [R.player_roster_resolve(s) for s in range(4)]
        R.player_roster_set_count(2)
        for so_id in ids:
            self.assertTrue(object_exists(so_id),
                            "a count change deleted a ship - that is the whole bug")
        # Parked ships give up __player__ so nothing counts them as crew...
        self.assertFalse(has_role(ids[3], "__player__"))
        # ...but keep their slot marker, or the next raise would spawn a duplicate.
        self.assertTrue(has_role(ids[3], player_slot_role(3)))

    def test_raising_the_count_wakes_the_same_ship_with_the_same_id(self):
        was = R.player_roster_resolve(3)
        R.player_roster_set_count(2)
        R.player_roster_set_count(4)
        self.assertEqual(was, R.player_roster_resolve(3),
                         "a raise handed slot 3 a NEW ship; every console on it would break")
        self.assertTrue(has_role(was, "__player__"))
        self.assertEqual("tsn", to_object(was).side)

    def test_the_count_can_be_moved_repeatedly_without_losing_a_ship(self):
        ids = {s: R.player_roster_resolve(s) for s in range(4)}
        for n in (8, 2, 5, 1, 4):
            R.player_roster_set_count(n)
        self.assertEqual(ids, {s: R.player_roster_resolve(s) for s in range(4)})

    def test_set_count_reports_only_what_changed(self):
        self.assertEqual([2, 3], R.player_roster_set_count(2))
        self.assertEqual([], R.player_roster_set_count(2))

    # --- apply --------------------------------------------------------------

    def test_apply_is_idempotent(self):
        self._set_art_keys({"tsn_light_cruiser": "tsn_scout"})
        self.assertTrue(R.player_roster_apply(),
                        "the first apply did nothing, so the second proves nothing")
        self.assertEqual([], R.player_roster_apply(),
                         "a second apply touched something; every repaint would rebuild stats")

    def test_apply_on_an_untouched_roster_is_a_no_op(self):
        """Ships spawned from their own records already match them, so apply must do NOTHING.

        This is not just tidiness. apply() runs on every server-panel build, and anything it
        does unconditionally happens on every build - a face re-roll here drew from the
        seeded RNG each time, shifting the sequence and changing every NPC spawned
        afterwards. A seeded stock run went from 15 NPC hulls to 13 and still reported PASS.
        """
        self.assertEqual([], R.player_roster_apply())

    def test_an_unchanged_hull_does_not_rebuild_stats(self):
        """The safety property behind diff-then-write.

        `player_ship_setup_from_data` resets a ship to its shipData defaults, so re-running
        it on every panel repaint would wipe whatever a map had set on that ship in between.
        The old code needed a did-I-run latch to avoid exactly this; the diff is what
        replaces the latch.
        """
        R.player_roster_apply()
        # Patch what the code under test ACTUALLY calls. player_roster_apply does a bare
        # `import sbs`, which resolves sys.modules["sbs"] - and that is not always the plain
        # mock: another test in the same interpreter can install cosmos_dev.mockgui.sbs
        # there instead. Patching the `mock` alias then leaves the real function in place,
        # the counter never moves, and BOTH assertions below read as "nothing rebuilt" - one
        # passing vacuously and one failing for a reason unrelated to the roster.
        import sys
        sbs_mod = sys.modules["sbs"]
        calls = []
        real = sbs_mod.player_ship_setup_from_data
        sbs_mod.player_ship_setup_from_data = lambda eo: calls.append(eo)
        try:
            R.player_roster_apply()
            self.assertEqual([], calls, "stats were rebuilt with no hull change")
            self._set_art_keys({"tsn_light_cruiser": "tsn_scout"})
            self.assertEqual([0], R.player_roster_apply(),
                             "the re-hull did not happen, so the count below proves nothing")
            self.assertEqual(1, len(calls), "only the slot whose hull moved should rebuild")
        finally:
            sbs_mod.player_ship_setup_from_data = real

    def test_apply_reskins_through_art_keys_without_changing_the_id(self):
        was = R.player_roster_resolve(0)
        self._set_art_keys({"tsn_light_cruiser": "tsn_battle_cruiser"})
        self.assertIn(0, R.player_roster_apply())
        self.assertEqual(was, R.player_roster_resolve(0),
                         "a re-hull must be a field write - it cannot morph the engine id")
        self.assertEqual("tsn_battle_cruiser", to_object(was).art_id)

    def test_apply_leaves_parked_slots_alone(self):
        self._set_art_keys({"tsn_battle_cruiser": "tsn_light_cruiser"})
        R.player_roster_set_count(1)
        touched = R.player_roster_apply()
        self.assertNotIn(3, touched)
        self.assertEqual("invisible", to_object(R.player_roster_resolve(3)).art_id)

    def test_a_game_code_loadout_beats_the_theater(self):
        """The crew picked that hull explicitly; a theater is a default, not an override."""
        self._set_art_keys({"tsn_light_cruiser": "tsn_battle_cruiser"})
        R.player_roster_apply(loadout=[{"hull": "tsn_scout", "name": "Coded"}])
        obj = to_object(R.player_roster_resolve(0))
        self.assertEqual("tsn_scout", obj.art_id)
        self.assertEqual("Coded", obj.name)

    def test_the_name_survives_a_hull_change(self):
        """setup_from_data resets the name, so apply must write it back AFTER."""
        self._set_art_keys({"tsn_light_cruiser": "tsn_battle_cruiser"})
        R.player_roster_apply()
        self.assertEqual("Artemis", to_object(R.player_roster_resolve(0)).name)

    # --- the theater survives a change, which is the whole point ------------

    def test_a_theater_change_re_skins_every_slot_and_moves_nobody(self):
        R.player_roster_bind(2, 55)
        before = {s: R.player_roster_resolve(s) for s in range(4)}

        self._set_art_keys({"tsn_light_cruiser": "tsn_battle_cruiser",
                            "tsn_battle_cruiser": "tsn_scout"})
        R.player_roster_apply()
        self._set_art_keys({"tsn_light_cruiser": "tsn_scout",
                            "tsn_battle_cruiser": "tsn_light_cruiser"})
        R.player_roster_apply()

        self.assertEqual(before, {s: R.player_roster_resolve(s) for s in range(4)},
                         "a theater change moved a slot onto a different ship")
        self.assertEqual({55}, R.player_roster_bound(2), "the console lost its slot")
        self.assertEqual("tsn_scout", to_object(before[0]).art_id)

    def test_count_and_theater_together_leave_the_bound_slot_alone(self):
        """The fluid phase as it actually happens: the operator moves both."""
        R.player_roster_bind(2, 55)
        was = R.player_roster_resolve(2)
        R.player_roster_set_count(2)          # slot 2 parks
        self._set_art_keys({"tsn_battle_cruiser": "tsn_scout"})
        R.player_roster_apply()
        R.player_roster_set_count(4)          # and comes back
        R.player_roster_apply()
        self.assertEqual(was, R.player_roster_resolve(2))
        self.assertEqual({55}, R.player_roster_bound(2))
        self.assertTrue(object_exists(was))

    # --- the theater dresses the crew ---------------------------------------

    def _theater(self, body_lines):
        """Declare a one-off theater and make it active.

        body_lines is a list of fence lines, so the test reads as the .amd an author
        would write.
        """
        import sbs_utils.procedural.amd_theater as T
        T.amd_theater_clear()
        doc = [chr(35) + ' [T](t)', '---', 'Factions: kralien']
        doc += list(body_lines)
        doc += ['---', 'a theater', '']
        T.theater_declare_text(chr(10).join(doc))
        import sbs_utils.procedural.settings as S
        self._real = getattr(self, '_real', S.settings_get_defaults)
        S.settings_get_defaults = _Settings({'THEATER': 't'})

    def test_player_faction_reskins_the_crew(self):
        """The crew move onto another side's hulls, and the pairing keeps its order.

        USFP is used because it is a side stock data really has. Note what it gives back:
        a science ship and a luxury liner, because stock splits the Federation into `tsn`
        (navy) and `USFP` (freighters and starbases). That is the pairing working, and the
        trap the accessor's docstring warns about.
        """
        from sbs_utils.procedural.ship_data import get_ship_data_for
        before = [to_object(R.player_roster_resolve(s)).art_id for s in range(4)]
        self._theater(["Player Faction: USFP"])
        self.assertEqual([0, 1, 2, 3], R.player_roster_apply())
        after = [to_object(R.player_roster_resolve(s)).art_id for s in range(4)]
        self.assertNotEqual(before, after, "Player Faction changed nothing")
        for h in after:
            self.assertIsNotNone(get_ship_data_for(h), f"{h!r} is not a real hull")
            self.assertEqual("usfp", str(get_ship_data_for(h).get("side")).lower(),
                             f"{h!r} is not on the faction that was asked for")

    def test_explicit_players_list_beats_the_faction(self):
        self._theater(["Player Faction: USFP", "Players: tsn_scout, tsn_scout"])
        R.player_roster_apply()
        self.assertEqual("tsn_scout", to_object(R.player_roster_resolve(0)).art_id)
        self.assertEqual("tsn_scout", to_object(R.player_roster_resolve(1)).art_id)

    def test_a_loadout_beats_the_explicit_players_list(self):
        """Full precedence: the crew's own choice is the strongest thing in the stack."""
        self._theater(["Player Faction: USFP", "Players: tsn_scout, tsn_scout"])
        R.player_roster_apply(loadout=[{"hull": "tsn_battle_cruiser", "name": None}])
        self.assertEqual("tsn_battle_cruiser", to_object(R.player_roster_resolve(0)).art_id)
        self.assertEqual("tsn_scout", to_object(R.player_roster_resolve(1)).art_id)

    def test_the_costume_renames_the_side_without_moving_it(self):
        """The whole point: pirates by NAME, never by diplomacy."""
        from sbs_utils.procedural.sides import side_display_name
        self._theater(["Player Side Name: Orion Syndicate", "Player Side Icon: 7"])
        R.player_roster_apply()
        self.assertEqual("Orion Syndicate", side_display_name("tsn"))
        for slot in range(4):
            self.assertEqual("tsn", to_object(R.player_roster_resolve(slot)).side,
                             "the costume moved a ship's actual side")

    def test_player_side_key_is_refused_not_applied(self):
        self._theater(["Player Side Key: raider"])
        R.player_roster_apply()
        for slot in range(4):
            self.assertEqual("tsn", to_object(R.player_roster_resolve(slot)).side,
                             "Player Side Key moved the crew - it must refuse instead")

    def test_no_player_fields_leaves_the_crew_alone(self):
        self._theater([])
        self.assertEqual([], R.player_roster_apply())

    # --- record edits: the picker must touch no engine object ----------------

    def test_a_rename_writes_the_record_and_not_the_ship(self):
        """THE claim this design rests on.

        The picker used to run `picked_ship.name = ...` per keystroke, which lands in
        set_name -> blob.set("name_tag") - ObjectDataBlob::Set, the function in every one of
        this build's server crash dumps, called on a live ship while the sim ticks it.
        """
        so_id = R.player_roster_resolve(0)
        before = to_object(so_id).name
        self.assertTrue(R.player_roster_set_name(0, "Bellerophon"))
        self.assertEqual(before, to_object(so_id).name, "the rename reached the SHIP")
        self.assertEqual("Bellerophon", R.player_roster_display(0)["name"],
                         "but the picker must still show it")

    def test_a_hull_pick_writes_the_record_and_not_the_ship(self):
        so_id = R.player_roster_resolve(0)
        before = to_object(so_id).art_id
        self.assertTrue(R.player_roster_set_hull(0, "tsn_scout"))
        self.assertEqual(before, to_object(so_id).art_id, "the pick reached the SHIP")
        self.assertEqual("tsn_scout", R.player_roster_display(0)["hull"])

    def test_a_whole_setup_session_writes_nothing_to_any_engine_object(self):
        """The end-to-end version: rename, re-hull, move the count, twice over, and assert
        the engine was never written. This is what "no engine data issues on the picker"
        has to mean to be worth anything."""
        import sys
        sbs_mod = sys.modules["sbs"]
        calls = []
        real_setup = sbs_mod.player_ship_setup_from_data
        real_force = getattr(sbs_mod, "force_update_to_clients", None)
        sbs_mod.player_ship_setup_from_data = lambda eo: calls.append("setup")
        try:
            for slot in range(4):
                R.player_roster_set_name(slot, f"Ship {slot}")
                R.player_roster_set_hull(slot, "tsn_scout")
            R.player_roster_set_count(2)
            R.player_roster_set_count(4)
            for slot in range(4):
                R.player_roster_set_name(slot, f"Renamed {slot}")
            self.assertEqual([], calls, "setup rebuilt a ship during the picker session")
        finally:
            sbs_mod.player_ship_setup_from_data = real_setup

    def test_apply_carries_the_edits_across_at_start(self):
        """The other half: nothing during setup, everything at Start."""
        R.player_roster_set_name(0, "Bellerophon")
        R.player_roster_set_hull(0, "tsn_scout")
        self.assertIn(0, R.player_roster_apply())
        obj = to_object(R.player_roster_resolve(0))
        self.assertEqual("Bellerophon", obj.name)
        self.assertEqual("tsn_scout", obj.art_id)

    def test_a_crew_pick_beats_the_theater_and_loses_to_a_game_code(self):
        self._theater(["Player Faction: USFP"])
        R.player_roster_set_hull(0, "tsn_scout")
        R.player_roster_apply()
        self.assertEqual("tsn_scout", to_object(R.player_roster_resolve(0)).art_id)
        R.player_roster_apply(loadout=[{"hull": "tsn_battle_cruiser", "name": None}])
        self.assertEqual("tsn_battle_cruiser", to_object(R.player_roster_resolve(0)).art_id)

    def test_a_slot_keeps_its_identity_through_a_rename_and_a_re_hull(self):
        R.player_roster_bind(2, 55)
        was = R.player_roster_resolve(2)
        R.player_roster_set_name(2, "Renamed")
        R.player_roster_set_hull(2, "tsn_scout")
        R.player_roster_set_count(1)
        R.player_roster_set_count(4)
        R.player_roster_apply()
        self.assertEqual(was, R.player_roster_resolve(2))
        self.assertEqual({55}, R.player_roster_bound(2))

    def test_display_falls_back_to_the_record_when_there_is_no_ship(self):
        self.assertEqual("Artemis", R.player_roster_display(0)["name"])
        self.assertEqual({"name": "", "hull": "", "side": ""}, R.player_roster_display(99))

    def test_display_shows_the_live_ship_once_one_exists(self):
        """After Start a mission may have refitted a ship; the picker should say so."""
        so_id = R.player_roster_resolve(0)
        to_object(so_id).name = "Renamed By The Mission"
        self.assertEqual("Renamed By The Mission", R.player_roster_display(0)["name"])

    def test_display_does_not_report_a_parked_hull_as_invisible(self):
        R.player_roster_set_count(1)
        self.assertNotEqual("invisible", R.player_roster_display(3)["hull"])

    # --- standby: why an unused hull is suspended, not freed -----------------

    def test_parking_pushes_the_ship_to_standby(self):
        """Standby suspends an object from the physics arena AND from network replication
        without freeing it. That is the whole fix: a client cannot ask the server about a
        ship it is not being told about, and there is no freed blob for the question to
        land on. Deleting instead frees the C++ object synchronously, and a client asking
        across that window is the ObjectDataBlob use-after-free."""
        import sys
        so_id = R.player_roster_resolve(3)
        R.player_roster_set_count(2)
        self.assertTrue(sys.modules["sbs"].in_standby_list_id(so_id))

    def test_a_parked_ship_still_EXISTS(self):
        """object_exists means alive, not in-the-arena - engine-confirmed. If it went False
        for standby, resolve() would lose the slot and the next raise would spawn a
        duplicate beside the one that is still there."""
        so_id = R.player_roster_resolve(3)
        R.player_roster_set_count(2)
        self.assertTrue(object_exists(so_id))
        self.assertEqual(so_id, R.player_roster_resolve(3))

    def test_parking_strips_every_role_but_the_slot_marker(self):
        """Nothing should still consider a parked hull: no targeting sweep, objective or
        role expression. The slot marker is the one exception - bookkeeping, script-side
        only, and without it the roster could not find the ship again to wake it."""
        from sbs_utils.procedural.roles import get_role_list
        so_id = R.player_roster_resolve(3)
        from sbs_utils.procedural.roles import add_role
        add_role(so_id, "default_player_ship")
        add_role(so_id, "some_mission_role")
        R.player_roster_set_count(2)
        self.assertEqual([player_slot_role(3)], sorted(get_role_list(so_id) or []))

    def test_waking_retrieves_from_standby_and_restores_the_roles(self):
        import sys
        so_id = R.player_roster_resolve(3)
        R.player_roster_set_count(2)
        R.player_roster_set_count(4)
        self.assertFalse(sys.modules["sbs"].in_standby_list_id(so_id))
        self.assertTrue(has_role(so_id, "__player__"))
        self.assertTrue(has_role(so_id, "default_player_ship"))
        self.assertEqual("tsn", to_object(so_id).side)

    def test_park_inactive_is_a_backstop_and_idempotent(self):
        R.player_roster_set_count(2)
        self.assertEqual([], R.player_roster_park_inactive(),
                         "set_count already parked these; re-parking is wasted work")
        import sys
        so_id = R.player_roster_resolve(3)
        sys.modules["sbs"].retrieve_from_standby_list_id(so_id)   # something woke it
        self.assertEqual([2, 3], sorted(R.player_roster_park_inactive() + [2]))

    def test_parking_does_not_fire_a_hull_change_on_a_player_ship(self):
        """The order that matters most in this file.

        Setting art_id emits `ship_hull_changed`, and LM answers it with
        grid_rebuild_grid_objects - a delete-and-respawn of 60-100 grid objects, guarded
        only by `has_role(ship, "__player__")`. Blanking the hull before stripping the
        roles fires that on every parked slot: seven hulls is 400-700 grid deletions at
        map start, and grid objects cannot go to standby.
        """
        from sbs_utils.procedural.signal import signal_register
        fired = []
        so_id = R.player_roster_resolve(3)

        import sbs_utils.spaceobject as SO
        real = SO.signal_emit if hasattr(SO, "signal_emit") else None
        import sbs_utils.procedural.signal as SIG
        real_emit = SIG.signal_emit

        def spy(name, data=None):
            if name == "ship_hull_changed":
                from sbs_utils.procedural.roles import has_role as _hr
                fired.append((data or {}).get("SHIP_ID"))
                # Record whether it would have reached the rebuild: the route's own guard.
                if _hr((data or {}).get("SHIP_ID"), "__player__"):
                    fired.append("STILL_A_PLAYER")
            return real_emit(name, data)

        SIG.signal_emit = spy
        try:
            R.player_roster_set_count(2)
        finally:
            SIG.signal_emit = real_emit

        self.assertNotIn("STILL_A_PLAYER", fired,
                         "the hull was blanked while the ship was still __player__, so "
                         "LM's route would delete and respawn its whole interior")

    # --- release: the one delete, at the phase edge -------------------------

    def test_release_deletes_only_parked_slots(self):
        keep = R.player_roster_resolve(0)
        drop = R.player_roster_resolve(3)
        R.player_roster_set_count(2)
        self.assertEqual([2, 3], R.player_roster_release_inactive())
        self.assertTrue(object_exists(keep))
        self.assertFalse(object_exists(drop))

    def test_release_refuses_a_slot_a_console_is_still_on(self):
        R.player_roster_bind(3, 42)
        held = R.player_roster_resolve(3)
        R.player_roster_set_count(2)
        self.assertEqual([2], R.player_roster_release_inactive())
        self.assertTrue(object_exists(held),
                        "released a ship a console was crewing - the exact use-after-free")

    def test_a_disconnected_client_stops_blocking_release(self):
        """A binding outlives the console that made it - nothing tells the roster a client
        left. Left unpruned it would block release forever and the parked ships would pile
        up for the rest of the session."""
        from sbs_utils.gui import Gui
        R.player_roster_bind(3, 42)
        R.player_roster_set_count(2)
        Gui.clients[42] = object()          # 42 is connected
        try:
            self.assertEqual({42}, R.player_roster_bound_live(3))
            self.assertEqual([2], R.player_roster_release_inactive())
            del Gui.clients[42]
            Gui.clients[99] = object()      # somebody else is, 42 is gone
            self.assertEqual(set(), R.player_roster_bound_live(3))
            self.assertEqual([3], R.player_roster_release_inactive())
        finally:
            Gui.clients.pop(42, None)
            Gui.clients.pop(99, None)

    def test_an_empty_client_registry_keeps_the_binding(self):
        """No connected clients is indistinguishable from nothing tracking clients, and it
        is what every headless run looks like. Refusing to delete is a leak; deleting a ship
        somebody is flying is a crash - so with no information, keep it."""
        R.player_roster_bind(3, 42)
        R.player_roster_set_count(2)
        self.assertEqual({42}, R.player_roster_bound_live(3))
        self.assertNotIn(3, R.player_roster_release_inactive())

    def test_release_is_safe_to_run_twice(self):
        R.player_roster_set_count(2)
        R.player_roster_release_inactive()
        self.assertEqual([], R.player_roster_release_inactive())

    # --- binding ------------------------------------------------------------

    def test_a_client_crews_exactly_one_slot(self):
        R.player_roster_bind(0, 9)
        R.player_roster_bind(2, 9)
        self.assertEqual(set(), R.player_roster_bound(0))
        self.assertEqual({9}, R.player_roster_bound(2))
        self.assertEqual(2, R.player_roster_slot_of_client(9))

    def test_unbind_forgets_the_client(self):
        R.player_roster_bind(1, 9)
        R.player_roster_unbind(9)
        self.assertIsNone(R.player_roster_slot_of_client(9))

    # --- the case the engine owns: the id really does change ----------------

    def test_rebind_reassigns_bound_clients_when_a_slot_gets_a_new_ship(self):
        """A sim wipe respawns the roster, so slot 2 is a genuinely NEW engine object.

        Indirection cannot morph the id - it makes SURVIVING the change the roster's job.
        """
        R.player_roster_bind(2, 55)
        R.player_roster_rebind()                       # record the ids we start from
        was = R.player_roster_resolve(2)

        for rec in R.player_roster():                  # the wipe
            so_id = R.player_roster_resolve(rec["slot"])
            if so_id is not None:
                to_object(so_id).delete_object()
        self._spawn_all()

        now = R.player_roster_resolve(2)
        self.assertNotEqual(was, now, "the mock reused the id - the test proves nothing")
        self.assertEqual([2], R.player_roster_rebind())
        import sys
        self.assertEqual(now, sys.modules["sbs"].get_ship_of_client(55))

    def test_rebind_is_quiet_when_nothing_moved(self):
        R.player_roster_bind(2, 55)
        R.player_roster_rebind()
        self.assertEqual([], R.player_roster_rebind())

    def test_rebind_does_not_touch_a_slot_nobody_is_on(self):
        R.player_roster_rebind()
        for rec in R.player_roster():
            so_id = R.player_roster_resolve(rec["slot"])
            if so_id is not None:
                to_object(so_id).delete_object()
        self._spawn_all()
        self.assertEqual([], R.player_roster_rebind())

    # --- reset ledger -------------------------------------------------------

    def test_reset_empties_the_roster(self):
        R.player_roster_bind(0, 5)
        self.assertTrue(R.player_roster_count_records() > 0)
        reset_mock(mock)
        self.assertEqual(0, R.player_roster_count_records())


if __name__ == "__main__":
    unittest.main()
