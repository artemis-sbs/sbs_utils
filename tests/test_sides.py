from cosmos_dev.mock import sbs as sbs
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.agent import Agent, get_story_id
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.objects import PlayerShip, Npc
from sbs_utils.fs import test_set_exe_dir
from sbs_utils.procedural.sides import (
    to_side_id, side_keys_set,
    side_members_set, side_ally_members_set, side_enemy_members_set,
    side_are_allies, side_are_enemies, side_are_neutral, side_are_same_side,
    side_set_relations, side_get_relations,
    side_hostile_members, is_hostile_combatant,
    players_hostile_members, is_hostile_to_players,
    side_allied_members, players_allied_members,
    side_are_friendly, is_allied_to_players,
    side_ensure, side_set_hostile_to_players,
    side_surrender, side_unsurrender, side_capture,
    side_hostile_ships, players_hostile_ships, players_ceasefire,
)
import unittest

test_set_exe_dir()


def make_side(key, name):
    """Create a side Agent the same way MAST/prefab code would."""
    side = Agent()
    side.id = get_story_id()
    side.add()
    side.add_role("__side__")
    side.set_inventory_value("side_key", key)
    side.set_inventory_value("side_name", name)
    return side


class TestSides(unittest.TestCase):

    def setUp(self):
        SpaceObject.clear()
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())

    # ------------------------------------------------------------------
    # to_side_id
    # ------------------------------------------------------------------

    def test_to_side_id_by_key(self):
        tsn = make_side("tsn", "TSN")
        self.assertEqual(to_side_id("tsn"), tsn.id)

    def test_to_side_id_by_key_case_insensitive(self):
        tsn = make_side("tsn", "TSN")
        self.assertEqual(to_side_id("TSN"), tsn.id)

    def test_to_side_id_by_display_name(self):
        pirates = make_side("pirate", "Pirates")
        self.assertEqual(to_side_id("Pirates"), pirates.id)

    def test_to_side_id_by_agent_id(self):
        tsn = make_side("tsn", "TSN")
        self.assertEqual(to_side_id(tsn.id), tsn.id)

    def test_to_side_id_unknown_returns_none(self):
        self.assertIsNone(to_side_id("no_such_side_xyz"))

    def _spy_emitted(self):
        """Capture the keys actually EMITTED as 'Side not found' — spying at the
        single warning gate's log sink (the real message source), so a lookup
        that merely *routes* to the gate but is suppressed counts as silent.
        Clears the process-wide dedup set so each test starts fresh."""
        from sbs_utils.procedural import sides as sides_mod
        from sbs_utils.procedural import execution as exec_mod
        sides_mod._missing_side_warned.clear()
        emitted = []
        orig = exec_mod.log
        exec_mod.log = lambda msg, *a, **k: emitted.append(msg)
        self.addCleanup(setattr, exec_mod, "log", orig)
        return emitted

    def test_to_side_id_hidden_or_empty_is_silent_none(self):
        # A "#"-only / empty side means NO side (asteroids, cambots, hidden
        # objects) — resolve to None WITHOUT emitting a 'Side not found' message.
        emitted = self._spy_emitted()
        for hidden in ("", "   ", "#", "##", "  #  "):
            self.assertIsNone(to_side_id(hidden), hidden)
        self.assertEqual(emitted, [], "a hidden/empty side must not warn")

    def test_to_side_id_hash_prefixed_resolves_to_bare_side(self):
        # "#raider" is the "raider" side with its display hidden — it must resolve.
        raider = make_side("raider", "Raider")
        self.assertEqual(to_side_id("#raider"), raider.id)

    def test_to_side_id_literally_registered_hash_side_matches(self):
        # A side genuinely registered as "#secret" still matches as-is.
        secret = make_side("#secret", "Secret")
        self.assertEqual(to_side_id("#secret"), secret.id)

    def test_to_side_id_unknown_named_side_emits_once(self):
        # A genuinely-named miss is a real problem (typo'd side): it emits, but
        # only ONCE per distinct key even across a per-tick sweep.
        emitted = self._spy_emitted()
        for _ in range(3):
            self.assertIsNone(to_side_id("wibble"))
        self.assertEqual(len(emitted), 1, "should emit once per distinct key")
        self.assertIn("wibble", emitted[0])

    def test_warn_missing_side_stays_silent_for_monster(self):
        # Feral monsters intentionally ride an unregistered 'monster' side.
        emitted = self._spy_emitted()
        self.assertIsNone(to_side_id("monster"))
        self.assertEqual(emitted, [])

    def test_to_side_id_warn_false_stays_silent(self):
        # Existence probes (create-if-missing) pass warn=False: no message even
        # for a genuinely-unknown side.
        emitted = self._spy_emitted()
        self.assertIsNone(to_side_id("nope_xyz", warn=False))
        self.assertEqual(emitted, [])

    # ------------------------------------------------------------------
    # side_keys_set
    # ------------------------------------------------------------------

    def test_side_keys_set(self):
        make_side("tsn", "TSN")
        make_side("pirate", "Pirates")
        keys = side_keys_set()
        self.assertIn("tsn", keys)
        self.assertIn("pirate", keys)
        self.assertEqual(len(keys), 2)

    # ------------------------------------------------------------------
    # Relationship setting and querying
    # ------------------------------------------------------------------

    def test_allied_relations(self):
        make_side("tsn", "TSN")
        make_side("uspf", "USPF")
        side_set_relations("tsn", "uspf", sbs.DIPLOMACY.ALLIED)
        self.assertTrue(side_are_allies("tsn", "uspf"))
        self.assertTrue(side_are_allies("uspf", "tsn"))  # bidirectional
        self.assertFalse(side_are_enemies("tsn", "uspf"))
        self.assertFalse(side_are_neutral("tsn", "uspf"))

    def test_hostile_relations(self):
        make_side("tsn", "TSN")
        make_side("pirate", "Pirates")
        side_set_relations("tsn", "pirate", sbs.DIPLOMACY.HOSTILE)
        self.assertTrue(side_are_enemies("tsn", "pirate"))
        self.assertTrue(side_are_enemies("pirate", "tsn"))  # bidirectional
        self.assertFalse(side_are_allies("tsn", "pirate"))
        self.assertFalse(side_are_neutral("tsn", "pirate"))

    def test_neutral_relations(self):
        make_side("tsn", "TSN")
        make_side("alien", "Aliens")
        side_set_relations("tsn", "alien", sbs.DIPLOMACY.NEUTRAL)
        self.assertTrue(side_are_neutral("tsn", "alien"))
        self.assertTrue(side_are_neutral("alien", "tsn"))  # bidirectional
        self.assertFalse(side_are_allies("tsn", "alien"))
        self.assertFalse(side_are_enemies("tsn", "alien"))

    def test_change_relations_clears_old(self):
        make_side("tsn", "TSN")
        make_side("pirate", "Pirates")
        side_set_relations("tsn", "pirate", sbs.DIPLOMACY.HOSTILE)
        self.assertTrue(side_are_enemies("tsn", "pirate"))
        side_set_relations("tsn", "pirate", sbs.DIPLOMACY.ALLIED)
        self.assertTrue(side_are_allies("tsn", "pirate"))
        self.assertFalse(side_are_enemies("tsn", "pirate"))  # old link gone

    def test_get_relations_allied(self):
        make_side("tsn", "TSN")
        make_side("uspf", "USPF")
        side_set_relations("tsn", "uspf", sbs.DIPLOMACY.ALLIED)
        self.assertEqual(side_get_relations("tsn", "uspf"), sbs.DIPLOMACY.ALLIED)

    def test_get_relations_hostile(self):
        make_side("tsn", "TSN")
        make_side("pirate", "Pirates")
        side_set_relations("tsn", "pirate", sbs.DIPLOMACY.HOSTILE)
        self.assertEqual(side_get_relations("tsn", "pirate"), sbs.DIPLOMACY.HOSTILE)

    def test_get_relations_unknown_when_unset(self):
        make_side("tsn", "TSN")
        make_side("alien", "Aliens")
        # No relation set — should return UNKNOWN
        self.assertEqual(side_get_relations("tsn", "alien"), sbs.DIPLOMACY.UNKNOWN)

    def test_same_side(self):
        tsn = make_side("tsn", "TSN")
        self.assertTrue(side_are_same_side("tsn", "tsn"))
        self.assertTrue(side_are_same_side(tsn.id, "tsn"))

    def test_different_sides_not_same(self):
        make_side("tsn", "TSN")
        make_side("pirate", "Pirates")
        self.assertFalse(side_are_same_side("tsn", "pirate"))

    # ------------------------------------------------------------------
    # side_members_set
    # ------------------------------------------------------------------

    def test_side_members_set(self):
        make_side("tsn", "TSN")
        ship1 = PlayerShip().spawn(0, 0, 0, "Artemis", "tsn", "tsn_battle_cruiser").py_object
        ship2 = PlayerShip().spawn(0, 0, 0, "Hera", "tsn", "tsn_battle_cruiser").py_object
        members = side_members_set("tsn")
        self.assertIn(ship1.id, members)
        self.assertIn(ship2.id, members)

    def test_side_members_excludes_other_sides(self):
        make_side("tsn", "TSN")
        make_side("pirate", "Pirates")
        tsn_ship = PlayerShip().spawn(0, 0, 0, "Artemis", "tsn", "tsn_battle_cruiser").py_object
        pirate_ship = Npc().spawn(0, 0, 0, "Raider", "pirate", "Light Cruiser", "behav_npcship").py_object
        tsn_members = side_members_set("tsn")
        self.assertIn(tsn_ship.id, tsn_members)
        self.assertNotIn(pirate_ship.id, tsn_members)

    # ------------------------------------------------------------------
    # side_ally_members_set / side_enemy_members_set
    # ------------------------------------------------------------------

    def test_ally_members_set(self):
        make_side("tsn", "TSN")
        make_side("uspf", "USPF")
        make_side("pirate", "Pirates")
        tsn_ship = PlayerShip().spawn(0, 0, 0, "Artemis", "tsn", "tsn_battle_cruiser").py_object
        uspf_ship = Npc().spawn(0, 0, 0, "DS1", "uspf", "starbase_command", "behav_spaceport").py_object
        pirate_ship = Npc().spawn(0, 0, 0, "Raider", "pirate", "Light Cruiser", "behav_npcship").py_object
        side_set_relations("tsn", "uspf", sbs.DIPLOMACY.ALLIED)
        side_set_relations("tsn", "pirate", sbs.DIPLOMACY.HOSTILE)
        allies = side_ally_members_set("tsn")
        self.assertIn(uspf_ship.id, allies)
        self.assertNotIn(tsn_ship.id, allies)   # own side not in ally set
        self.assertNotIn(pirate_ship.id, allies)

    def test_enemy_members_set(self):
        make_side("tsn", "TSN")
        make_side("pirate", "Pirates")
        tsn_ship = PlayerShip().spawn(0, 0, 0, "Artemis", "tsn", "tsn_battle_cruiser").py_object
        pirate_ship = Npc().spawn(0, 0, 0, "Raider", "pirate", "Light Cruiser", "behav_npcship").py_object
        side_set_relations("tsn", "pirate", sbs.DIPLOMACY.HOSTILE)
        enemies = side_enemy_members_set("tsn")
        self.assertIn(pirate_ship.id, enemies)
        self.assertNotIn(tsn_ship.id, enemies)

    # ------------------------------------------------------------------
    # side_hostile_members / is_hostile_combatant  (raider-migration source of truth)
    # ------------------------------------------------------------------

    def _hostile_setup(self):
        """tsn (player), pirate (hostile, raider-tagged), civ (neutral, raider-tagged).
        Returns (tsn_ship, pirate_ship, civ_ship)."""
        make_side("tsn", "TSN")
        make_side("pirate", "Pirates")
        make_side("civ", "Civ")
        tsn_ship = PlayerShip().spawn(0, 0, 0, "Artemis", "tsn", "tsn_battle_cruiser").py_object
        pirate_ship = Npc().spawn(0, 0, 0, "Raider", "pirate", "Light Cruiser", "behav_npcship").py_object
        civ_ship = Npc().spawn(0, 0, 0, "Trader", "civ", "Light Cruiser", "behav_npcship").py_object
        # Both foe and neutral carry the combat "raider" tag (the overloaded marker).
        pirate_ship.add_role("raider")
        civ_ship.add_role("raider")
        side_set_relations("tsn", "pirate", sbs.DIPLOMACY.HOSTILE)
        side_set_relations("tsn", "civ", sbs.DIPLOMACY.NEUTRAL)
        return tsn_ship, pirate_ship, civ_ship

    def test_side_hostile_members_scoped_excludes_neutral(self):
        tsn_ship, pirate_ship, civ_ship = self._hostile_setup()
        foes = side_hostile_members("tsn", "raider")
        self.assertIn(pirate_ship.id, foes)       # hostile + raider-tagged
        self.assertNotIn(civ_ship.id, foes)       # neutral (ceasefire analogue) drops out
        self.assertNotIn(tsn_ship.id, foes)       # own side

    def test_side_hostile_members_scope_respects_role_removal(self):
        # A surrendered/defected ship drops the raider role -> leaves the scoped set
        # even though its side is still diplomatically hostile.
        tsn_ship, pirate_ship, civ_ship = self._hostile_setup()
        pirate_ship.remove_role("raider")
        self.assertNotIn(pirate_ship.id, side_hostile_members("tsn", "raider"))
        # ...but without the scope it is still a hostile-side member.
        self.assertIn(pirate_ship.id, side_hostile_members("tsn"))

    def test_is_hostile_combatant(self):
        tsn_ship, pirate_ship, civ_ship = self._hostile_setup()
        self.assertTrue(is_hostile_combatant("tsn", pirate_ship))    # hostile by diplomacy
        self.assertFalse(is_hostile_combatant("tsn", civ_ship))      # neutral
        # DIPLOMACY decides by default: dropping a combat tag changes nothing, because
        # the ship is still on a hostile side. (This is the whole point of the default -
        # a stale or missing tag can no longer make a real enemy read as harmless.)
        pirate_ship.remove_role("raider")
        self.assertTrue(is_hostile_combatant("tsn", pirate_ship))
        # A mission that still keeps its own combat tag can opt back in explicitly.
        self.assertFalse(is_hostile_combatant("tsn", pirate_ship, scope_role="raider"))
        # The diplomacy way out of the fight: surrender moves it to the neutral
        # "surrendered" side, so it stops being a combatant with no tag involved.
        side_surrender(pirate_ship)
        self.assertFalse(is_hostile_combatant("tsn", pirate_ship))

    def test_players_hostile_members(self):
        # tsn_ship is the only player; pirate hostile, civ neutral.
        tsn_ship, pirate_ship, civ_ship = self._hostile_setup()
        foes = players_hostile_members("raider")
        self.assertIn(pirate_ship.id, foes)
        self.assertNotIn(civ_ship.id, foes)     # neutral to the player
        self.assertNotIn(tsn_ship.id, foes)
        # No players with a side -> empty (victory can't false-fire off an empty set
        # only because there is genuinely nothing hostile).
        tsn_ship.remove_role("__player__")
        self.assertEqual(players_hostile_members("raider"), set())

    def test_is_hostile_to_players(self):
        tsn_ship, pirate_ship, civ_ship = self._hostile_setup()
        self.assertTrue(is_hostile_to_players(pirate_ship))
        self.assertFalse(is_hostile_to_players(civ_ship))       # neutral
        # Diplomacy-driven by default: only a SIDE change takes it out of the fight.
        pirate_ship.remove_role("raider")
        self.assertTrue(is_hostile_to_players(pirate_ship))
        side_surrender(pirate_ship)                              # -> "surrendered" side
        self.assertFalse(is_hostile_to_players(pirate_ship))

    def test_hostile_ships_is_diplomacy_only(self):
        """side_hostile_ships / players_hostile_ships: the tag-free "who may I fight"
        sets that replaced scoping by role("raider")."""
        tsn_ship, pirate_ship, civ_ship = self._hostile_setup()
        foes = side_hostile_ships("tsn")
        self.assertIn(pirate_ship.id, foes)
        self.assertNotIn(civ_ship.id, foes)          # neutral by diplomacy
        # An enemy carrying NO combat tag still counts - the case a tag-scoped set missed.
        pirate_ship.remove_role("raider")
        self.assertIn(pirate_ship.id, side_hostile_ships("tsn"))
        self.assertIn(pirate_ship.id, players_hostile_ships())
        # Surrendered ships drop out (they move to the neutral "surrendered" side).
        side_surrender(pirate_ship)
        self.assertNotIn(pirate_ship.id, side_hostile_ships("tsn"))
        self.assertNotIn(pirate_ship.id, players_hostile_ships())

    def test_players_ceasefire_ends_hostility(self):
        """"End the attack" as a RELATION change - the replacement for stripping a
        shared combat tag, which left the ships diplomatically hostile."""
        tsn_ship, pirate_ship, civ_ship = self._hostile_setup()
        self.assertTrue(side_are_enemies("tsn", "pirate"))
        n = players_ceasefire()
        self.assertGreater(n, 0)
        self.assertFalse(side_are_enemies("tsn", "pirate"))
        self.assertEqual(players_hostile_ships(), set())

    def _friendly_setup(self):
        """tsn (player) + uspf (ALLIED to tsn) + pirate (hostile). Returns
        (tsn_station, uspf_station, pirate_station)."""
        make_side("tsn", "TSN"); make_side("uspf", "USPF"); make_side("pirate", "Pirates")
        tsn_p = PlayerShip().spawn(0, 0, 0, "Artemis", "tsn", "tsn_battle_cruiser").py_object
        tsn_st = Npc().spawn(0, 0, 0, "Home", "tsn", "starbase_command", "behav_spaceport").py_object
        uspf_st = Npc().spawn(0, 0, 0, "Ally", "uspf", "starbase_command", "behav_spaceport").py_object
        pir_st = Npc().spawn(0, 0, 0, "Foe", "pirate", "starbase_command", "behav_spaceport").py_object
        for s in (tsn_st, uspf_st, pir_st):
            s.add_role("station")
        side_set_relations("tsn", "uspf", sbs.DIPLOMACY.ALLIED)
        side_set_relations("tsn", "pirate", sbs.DIPLOMACY.HOSTILE)
        return tsn_st, uspf_st, pir_st

    def test_players_allied_members_stations(self):
        tsn_st, uspf_st, pir_st = self._friendly_setup()
        friendly = players_allied_members("station")
        self.assertIn(tsn_st.id, friendly)      # own player side
        self.assertIn(uspf_st.id, friendly)     # allied side
        self.assertNotIn(pir_st.id, friendly)   # hostile

    def test_side_allied_members(self):
        tsn_st, uspf_st, pir_st = self._friendly_setup()
        friends = side_allied_members("tsn", "station")
        self.assertIn(tsn_st.id, friends)       # own side
        self.assertIn(uspf_st.id, friends)      # ally
        self.assertNotIn(pir_st.id, friends)    # enemy

    def test_side_are_friendly_includes_same_side(self):
        tsn_st, uspf_st, pir_st = self._friendly_setup()
        self.assertTrue(side_are_friendly("tsn", "tsn"))     # same side is friendly
        self.assertTrue(side_are_friendly("tsn", "uspf"))    # allied
        self.assertFalse(side_are_friendly("tsn", "pirate")) # enemy

    def test_is_allied_to_players(self):
        tsn_st, uspf_st, pir_st = self._friendly_setup()
        self.assertTrue(is_allied_to_players(tsn_st))    # same side as the player
        self.assertTrue(is_allied_to_players(uspf_st))   # allied
        self.assertFalse(is_allied_to_players(pir_st))   # hostile

    # ------------------------------------------------------------------
    # side_ensure / side_set_hostile_to_players  (spawn-side decouple primitives)
    # ------------------------------------------------------------------

    def test_side_ensure_creates_and_is_idempotent(self):
        self.assertIsNone(to_side_id("kralien"))
        sid = side_ensure("kralien")
        self.assertEqual(to_side_id("kralien"), sid)   # now resolvable
        self.assertEqual(side_ensure("kralien"), sid)  # idempotent

    def test_surrender_changes_side_and_is_reversible(self):
        make_side("tsn", "TSN"); make_side("raider", "Raider")
        side_set_relations("tsn", "raider", sbs.DIPLOMACY.HOSTILE)
        PlayerShip().spawn(0, 0, 0, "Artemis", "tsn", "tsn_battle_cruiser")
        foe = Npc().spawn(2000, 0, 2000, "Foe", "raider", "kralien_cruiser", "behav_npcship").py_object
        foe.add_role("raider"); foe.add_role("kralien")
        # BEFORE: a hostile raider-side ship.
        self.assertTrue(side_are_enemies("tsn", foe))
        self.assertIn(foe.id, players_hostile_members("raider"))

        side_surrender(foe)
        # Side flipped to the neutral "surrendered" side; non-hostile everywhere.
        self.assertEqual(foe.side, "surrendered")
        self.assertFalse(side_are_enemies("tsn", foe))          # neutral by SIDE now
        self.assertFalse(is_hostile_to_players(foe))
        self.assertNotIn(foe.id, side_enemy_members_set("tsn"))
        self.assertNotIn(foe.id, players_hostile_members("raider"))
        self.assertTrue(foe.has_role("surrendered"))
        self.assertFalse(foe.has_role("raider"))
        self.assertTrue(foe.has_role("kralien"))                # faction identity kept
        self.assertEqual(foe.data_set.get("surrender_flag", 0), 1)

        side_unsurrender(foe)
        # Restored: origin side back, hostile again, re-armed.
        self.assertEqual(foe.side, "raider")
        self.assertTrue(side_are_enemies("tsn", foe))
        self.assertIn(foe.id, players_hostile_members("raider"))
        self.assertTrue(foe.has_role("raider"))
        self.assertFalse(foe.has_role("surrendered"))
        self.assertEqual(foe.data_set.get("surrender_flag", 0), 0)

    def test_capture_makes_a_prize_join_the_captor(self):
        make_side("tsn", "TSN"); make_side("raider", "Raider")
        side_set_relations("tsn", "raider", sbs.DIPLOMACY.HOSTILE)
        player = PlayerShip().spawn(0, 0, 0, "Artemis", "tsn", "tsn_battle_cruiser").py_object
        foe = Npc().spawn(2000, 0, 2000, "Foe", "raider", "kralien_cruiser", "behav_npcship").py_object
        foe.add_role("raider"); foe.add_role("kralien")
        side_surrender(foe)
        self.assertEqual(foe.side, "surrendered")
        side_capture(foe, player)                       # take it as a prize
        self.assertEqual(foe.side, "tsn")               # joined the captor's side
        self.assertTrue(is_allied_to_players(foe))      # now friendly
        self.assertFalse(is_hostile_to_players(foe))
        self.assertTrue(foe.has_role("captured"))
        self.assertFalse(foe.has_role("surrendered"))   # no longer flees home
        self.assertTrue(foe.has_role("kralien"))        # identity kept

    def test_side_set_hostile_to_players_registers_faction(self):
        # A player on tsn; register a per-faction enemy side and a ship on it.
        make_side("tsn", "TSN")
        PlayerShip().spawn(0, 0, 0, "Artemis", "tsn", "tsn_battle_cruiser")
        side_set_hostile_to_players("kralien")          # creates the side + relations
        foe = Npc().spawn(0, 0, 0, "K", "kralien", "Light Cruiser", "behav_npcship").py_object
        foe.add_role("raider")
        self.assertTrue(side_are_enemies("tsn", "kralien"))
        self.assertTrue(is_hostile_to_players(foe))     # hostile via diplomacy, own faction side
        self.assertIn(foe.id, players_hostile_members("raider"))


if __name__ == '__main__':
    unittest.main()
