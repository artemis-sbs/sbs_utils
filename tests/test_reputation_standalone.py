"""Reputation in a mission that is NOT Open Universe.

A side that values deeds (`Values:`), a character that speaks for a side (`Side:`),
`earns` in a quest's `Reward:` and in a hail answer, and `standing` in a line or a
choice - with nothing but what `sbs create -t amd` already puts in story.mast.

Every test here goes in through the door a mission uses: the real AMD readers
(`amd_document` under `amd_mission_data` and `amd_side_data`), `sides_declare_amd`,
`lifeforms_spawn`, `dialogue_register_scenes`, `quest_grant_amd`, the quest driver's
own completion, and the hail path (`hail_offer` / `hail_accept` / `hail_answer`). Two
real player ships, and console ids that carry the console bit.

    python -m unittest tests.test_reputation_standalone
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from cosmos_dev.mock import sbs as mock_sbs
from sbs_utils.agent import Agent, clear_shared
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.mast.mast_node import MastDataObject
from sbs_utils.procedural import amd_dialogue as D
from sbs_utils.procedural import boarding as B
from sbs_utils.procedural import hail as H
from sbs_utils.procedural import reputation as R
from sbs_utils.procedural.amd_doc import amd_document, amd_section
from sbs_utils.procedural.amd_lifeforms import (lifeforms_spawn, lifeforms_from_section,
                                                lifeform_speaker, lifeform_speaker_of)
from sbs_utils.procedural.amd_mission import amd_mission_data
from sbs_utils.procedural.amd_sides import (amd_side_data, sides_declare_amd,
                                            sides_from_section)
from sbs_utils.procedural.links import link
from sbs_utils.procedural.quest import QuestState, quest_get_state
from sbs_utils.procedural.quest_driver import (quest_grant_amd, quest_mark_complete,
                                               quest_grant_reward)
from sbs_utils.procedural.amd_quest import amd_reward
from sbs_utils.procedural.query import to_id
from sbs_utils.procedural.roles import add_role
from sbs_utils.procedural.spawn import player_spawn, npc_spawn

C_COMMS_A = 0x8000000000000001
C_COMMS_B = 0x8000000000000002
NL = "\n"

# What a writer types. One file, the sections the `amd` template loads.
MISSION = NL.join([
    "# [Sample Mission](sample_mission)",
    "",
    "## [Quests](quests)",
    "",
    "### [Tag the Hulk](tag_hulk)",
    "---",
    "Scope: shared",
    "Starts when: at once",
    "Reward: 150 credits, earns guild honest 30",
    "---",
    "Hang a beacon on the hulk.",
    "",
    "## [Sides](sides)",
    "",
    "### [TSN](tsn)",
    "---",
    "Color: #07F",
    "---",
    "The crew's own side.",
    "",
    "### [Harbor Guild](guild)",
    "---",
    "Color: #0C6",
    "Allies: tsn",
    "Values: honest 40, generous 30",
    "---",
    "The pilots and tug crews who work the lanes.",
    "",
    "### [The Breakers](breaker)",
    "---",
    "Color: #F80",
    "Enemies: tsn, guild",
    "---",
    "Scavengers.",
    "",
    "## [Characters](characters)",
    "",
    "### [Harbormaster Quill](quill)",
    "---",
    "Side: guild",
    "---",
    "Runs traffic control.",
    "",
    "### [Chief Ives](ives)",
    "---",
    "---",
    "Keeps the ledger. Speaks for nobody.",
    "",
    "## [Dialogue](dialogue)",
    "",
    "### [Quill Checks In](quill_hello)",
    "---",
    "Speaker: quill",
    "When: hail",
    "---",
    "%{standing < 30} Artemis, DS 1. State your business.",
    "%{standing >= 30} Artemis! Good to hear a friendly voice.",
    "",
    "- [Just passing through.]()",
    "- [We paid the tug crews out of our own pocket.]() ; earns guild generous 30",
    "- [Open the Guild yard to us.]() if standing >= 30",
    "",
    "### [The Guild Speaks](guild_hello)",
    "---",
    "Speaker: guild",
    "When: hail",
    "---",
    "%{standing < 30} This is the Harbor Guild. Keep to the lane.",
    "%{standing >= 30} The Guild knows your ship.",
    "",
    "- [Understood.]()",
    "- [Ask a favor.]() if honest >= 20",
    "",
])


class Base(unittest.TestCase):
    def setUp(self):
        from sbs_utils.handlerhooks import reset_mission_state
        reset_mission_state()
        mock_sbs.create_new_sim()
        mock_sbs.resume_sim()
        SpaceObject.clear()
        clear_shared()
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent(0, "test"))
        Agent.SHARED.set_inventory_value("sim", mock_sbs.sim)
        H.hail_reset()
        B.boarding_metric_uninstall()
        self._prev_resolver = D._METRIC_RESOLVER
        self._prev_outcomes = dict(D._OUTCOME_HANDLERS)
        D.dialogue_set_metric_resolver(None)
        # The library's own `earns`, whatever an earlier test file registered over it.
        earns = getattr(R, "reputation_earns_outcome", None)
        if earns is not None:
            D.dialogue_register_outcome("earns", earns)
        R.reputation_configure(None)

    def tearDown(self):
        B.boarding_metric_uninstall()
        D.dialogue_set_metric_resolver(self._prev_resolver)
        D._OUTCOME_HANDLERS.clear()
        D._OUTCOME_HANDLERS.update(self._prev_outcomes)
        H.hail_reset()
        D.dialogue_scenes_registry_clear()
        getattr(R, "reputation_sides_clear", lambda: None)()
        FrameContext.context = None

    # -- the template's own load order, minus MAST ------------------------------
    def load(self, text=MISSION, parser=amd_mission_data):
        self.doc = amd_document(text, data_parser=parser)
        sides_declare_amd(amd_section(self.doc, "sides"))
        self.cast = lifeforms_spawn(amd_section(self.doc, "characters"))
        D.dialogue_register_scenes(amd_section(self.doc, "dialogue"))
        quest_grant_amd(Agent.SHARED_ID, amd_section(self.doc, "quests"))
        return self.doc

    def ship(self, name, console, z=0):
        ship = to_id(player_spawn(0, 0, z, name, "tsn", "tsn_light_cruiser"))
        seat = Agent()
        seat.id = console
        seat.add()
        for r in ("console", "comms"):
            add_role(console, r)
        link(ship, "consoles", console)
        mock_sbs.assign_client_to_ship(console, ship)
        return ship

    def call(self, ship, scene):
        """Offer and open a hail; return (the line spoken, the answers offered)."""
        H.hail_offer(ship, scene=scene)
        H.hail_accept(ship)
        beat = H.hail_beat(ship)
        while H.hail_advance(ship):
            pass
        return (beat.get("text") if beat else None,
                [c.get("label") for c in (H.hail_active(ship) or {}).get("choices") or []])

    def answer(self, ship, console, words):
        labels = [c.get("label") for c in (H.hail_active(ship) or {}).get("choices") or []]
        index = next(i for i, l in enumerate(labels) if l.startswith(words))
        return H.hail_answer(ship, index, console)


# --- step 1: the registry --------------------------------------------------------
class TheSideRegistry(Base):
    def test_a_registered_side_is_found_by_key(self):
        R.reputation_side_register("Guild", {"By-the-Book": 40, "honest": 30})
        self.assertEqual(R.reputation_side("guild"),
                         {"key": "guild", "leans": {"by_the_book": 40, "honest": 30}})
        self.assertIsNone(R.reputation_side("breaker"))

    def test_it_is_on_the_reset_ledger_and_the_reset_empties_it(self):
        from sbs_utils.handlerhooks import (reset_mission_state, reset_mission_audit,
                                            _RESET_PROBES)
        self.assertIn("reputation sides", _RESET_PROBES)
        R.reputation_side_register("guild", {"honest": 40})
        self.assertEqual(reset_mission_audit().get("reputation sides"), 1)
        reset_mission_state()
        self.assertIsNone(R.reputation_side("guild"))
        self.assertNotIn("reputation sides", reset_mission_audit())


# --- step 2: Values: on a side ---------------------------------------------------
class ValuesBecomeLeans(Base):
    def test_under_the_mission_parser(self):
        doc = amd_document(MISSION, data_parser=amd_mission_data)
        recs = {r.get("key"): r for r in sides_from_section(amd_section(doc, "sides"))}
        self.assertEqual(recs["guild"].get("leans"), {"honest": 40, "generous": 30})
        self.assertEqual(recs["tsn"].get("leans"), {})

    def test_under_the_side_parser_on_a_flat_sides_file(self):
        flat = NL.join(["# [Harbor Guild](guild)", "---", "Color: #0C6",
                        "Values: by-the-book 40, Honest 30", "---", "The guild.", ""])
        recs = sides_from_section(amd_document(flat, data_parser=amd_side_data))
        self.assertEqual(recs[0].get("leans"), {"by_the_book": 40, "honest": 30})

    def test_declaring_the_sides_registers_what_each_values(self):
        for parser in (amd_mission_data, amd_side_data):
            R.reputation_sides_clear()
            sides_declare_amd(amd_section(amd_document(MISSION, data_parser=parser), "sides"))
            self.assertEqual(R.reputation_side("guild"),
                             {"key": "guild", "leans": {"honest": 40, "generous": 30}})
            # A side that values nothing in particular is still a side.
            self.assertEqual(R.reputation_side("breaker"), {"key": "breaker", "leans": {}})


# --- step 4: Side: on a character ------------------------------------------------
class ACharacterSpeaksForASide(Base):
    def test_side_is_a_declared_field_on_a_character(self):
        from sbs_utils.procedural.amd_schema import ARCHETYPES, ref
        self.assertEqual(ARCHETYPES["lifeform"].get("side"),
                         ref("node", hint="the side this person flies for"))

    def test_the_record_the_lifeform_and_both_cards_carry_it(self):
        self.load()
        recs = lifeforms_from_section(amd_section(self.doc, "characters"))
        self.assertEqual({r.get("key"): r.get("side") for r in recs},
                         {"quill": "guild", "ives": None})
        quill = self.cast["quill"]
        self.assertEqual(quill.get_inventory_value("lf_side", None), "guild")
        of = lifeform_speaker_of(to_id(quill))
        self.assertEqual((of.get("key"), of.get("side")), ("quill", "guild"))
        card = lifeform_speaker(recs, "quill")
        self.assertEqual((card.get("key"), card.get("side")), ("quill", "guild"))

    def test_the_hail_card_carries_key_and_side(self):
        self.load()
        ship = self.ship("Artemis", C_COMMS_A)
        card = H.hail_speaker("quill", ship)
        self.assertEqual((card.get("key"), card.get("side")), ("quill", "guild"))
        self.assertEqual(card.get("name"), "Harbormaster Quill")
        # A speaker that is a thing in the world speaks for the side it is on.
        npc_spawn(0, 0, 500, "DS 1", "tsn, station, home", "starbase_command",
                  "behav_station")
        self.assertEqual(H.hail_speaker("home", ship).get("side"), "tsn")
        # A key nothing answers to still renders, and still names itself.
        self.assertEqual(H.hail_speaker("guild", ship).get("key"), "guild")


# --- step 3: who a speaker speaks for, and the guard words -----------------------
class WhoseOpinion(Base):
    def test_a_record_with_its_own_leans_is_itself(self):
        cap = MastDataObject({"key": "vex", "leans": {"fearsome": 40}, "side": "ashfang"})
        self.assertIs(R.reputation_speaker_side(cap), cap)

    def test_a_character_is_read_through_its_side(self):
        self.load()
        guild = {"key": "guild", "leans": {"honest": 40, "generous": 30}}
        self.assertEqual(R.reputation_speaker_side(H.hail_speaker("quill")), guild)
        self.assertEqual(R.reputation_speaker_side(to_id(self.cast["quill"])), guild)
        self.assertEqual(R.reputation_speaker_side("quill"), guild)

    def test_a_speaker_key_that_is_a_side(self):
        self.load()
        self.assertEqual(R.reputation_speaker_side(H.hail_speaker("guild")).get("key"),
                         "guild")
        self.assertEqual(R.reputation_speaker_side("guild").get("key"), "guild")

    def test_a_side_nobody_declared_values_nothing(self):
        card = MastDataObject({"key": "sable", "side": "Corsair"})
        self.assertEqual(R.reputation_speaker_side(card), {"key": "corsair", "leans": {}})

    def test_someone_who_speaks_for_nobody(self):
        self.load()
        self.assertIsNone(R.reputation_speaker_side(H.hail_speaker("ives")))
        self.assertIsNone(R.reputation_speaker_side(None))


class TheGuardWords(Base):
    def test_standing_is_the_ships_weighted_standing_with_the_speakers_side(self):
        self.load()
        ship = self.ship("Artemis", C_COMMS_A)
        quill = H.hail_speaker("quill", ship)
        self.assertEqual(R.reputation_metric("standing", ship, quill), 0)
        R.reputation_adjust(ship, "guild", "honest", 30)
        # (40 * 30 + 30 * 0) / 70
        self.assertEqual(R.reputation_metric("standing", ship, quill), 17)
        self.assertEqual(R.reputation_metric("Reputation", ship, quill), 17)
        self.assertEqual(R.reputation_metric("honest", ship, quill), 30)
        self.assertEqual(R.reputation_metric("liar", ship, quill), -30)
        # Not a pole and not `standing`: nothing, as before.
        self.assertEqual(R.reputation_metric("medical", ship, quill), 0)
        # ...unless every name is to be read as a pole (Open Universe's habit).
        R.reputation_adjust(ship, "guild", "swagger", 7)
        self.assertEqual(R.reputation_metric("swagger", ship, quill), 0)
        self.assertEqual(R.reputation_metric("swagger", ship, quill, any_pole=True), 7)

    def test_a_guard_reads_it_with_no_resolver_installed_at_all(self):
        self.load()
        B.boarding_metric_uninstall()
        D.dialogue_set_metric_resolver(None)
        ship = self.ship("Artemis", C_COMMS_A)
        quill = H.hail_speaker("quill", ship)
        self.assertFalse(D.dialogue_guard_ok("standing >= 15", ship, quill))
        R.reputation_adjust(ship, "guild", "honest", 30)
        self.assertTrue(D.dialogue_guard_ok("standing >= 15", ship, quill))
        self.assertTrue(D.dialogue_guard_ok("honest", ship, quill))

    def test_it_is_the_base_under_the_boarding_resolver(self):
        # `dialogue_register_scenes` installs the away resolver (roles, `learned`,
        # `skill x`) in front; with nothing installed before it, reputation answers
        # what it does not.
        self.load()
        self.assertIs(D._METRIC_RESOLVER, B._boarding_metric)
        ship = self.ship("Artemis", C_COMMS_A)
        quill = H.hail_speaker("quill", ship)
        R.reputation_adjust(ship, "guild", "honest", 30)
        self.assertTrue(D.dialogue_guard_ok("standing >= 15", ship, quill))
        # ...and a role is still a role.
        add_role(ship, "medical")
        self.assertTrue(D.dialogue_guard_ok("medical", ship, quill))
        self.assertFalse(D.dialogue_guard_ok("security", ship, quill))

    def test_a_resolver_the_mission_set_itself_still_wins(self):
        seen = []

        def mine(name, agent_id, speaker):
            seen.append(name)
            return 99

        D.dialogue_set_metric_resolver(mine)
        self.load()                       # the away resolver goes in FRONT of `mine`
        ship = self.ship("Artemis", C_COMMS_A)
        quill = H.hail_speaker("quill", ship)
        self.assertTrue(D.dialogue_guard_ok("standing >= 99", ship, quill))
        self.assertEqual(seen, ["standing"])

    def test_a_console_and_the_ship_it_sits_on_are_one_reputation(self):
        self.load()
        ship = self.ship("Artemis", C_COMMS_A)
        quill = H.hail_speaker("quill", ship)
        R.reputation_adjust(ship, "guild", "honest", 30)
        self.assertEqual(R.reputation_metric("standing", C_COMMS_A, quill), 17)


class EarnsIsALibraryVerb(Base):
    def test_it_is_registered_by_importing_the_dialogue_module(self):
        self.assertIn("earns", D.dialogue_outcome_verbs())

    def test_dialogue_apply_moves_the_acting_ship(self):
        self.load()
        ship = self.ship("Artemis", C_COMMS_A)
        other = self.ship("Hera", C_COMMS_B, z=900)
        ok = D.dialogue_apply(ship, H.hail_speaker("quill", ship),
                              [("earns", "Guild", "by-the-book", "+12")])
        self.assertTrue(ok)
        self.assertEqual(R.reputation_get(ship, "guild", "by_the_book"), 12)
        self.assertEqual(R.reputation_get(other, "guild", "by_the_book"), 0)

    def test_a_console_earns_for_its_ship(self):
        self.load()
        ship = self.ship("Artemis", C_COMMS_A)
        D.dialogue_apply(C_COMMS_A, None, [("earns", "guild", "honest", "5")])
        self.assertEqual(R.reputation_get(ship, "guild", "honest"), 5)

    def test_a_clause_that_is_not_the_shape_changes_nothing(self):
        self.load()
        ship = self.ship("Artemis", C_COMMS_A)
        self.assertTrue(D.dialogue_apply(ship, None, [("earns", "guild", "honest")]))
        self.assertEqual(ship and Agent.get(ship).get_inventory_value("reputation", None),
                         None)


# --- step 5: a shared quest's earns reaches the ships -----------------------------
class ASharedQuestPaysEveryShip(Base):
    def test_completing_it_moves_both_ships_and_a_later_ship_starts_at_nothing(self):
        self.load()
        a = self.ship("Artemis", C_COMMS_A)
        b = self.ship("Hera", C_COMMS_B, z=900)
        self.assertEqual(quest_get_state(Agent.SHARED_ID, "tag_hulk"), QuestState.ACTIVE)
        quest_mark_complete(Agent.SHARED_ID, "tag_hulk")
        self.assertEqual(R.reputation_get(a, "guild", "honest"), 30)
        self.assertEqual(R.reputation_get(b, "guild", "honest"), 30)
        # The shared agent keeps its copy, as it always had.
        self.assertEqual(R.reputation_get(Agent.SHARED_ID, "guild", "honest"), 30)
        late = to_id(player_spawn(0, 0, 1800, "Aegis", "tsn", "tsn_light_cruiser"))
        self.assertEqual(R.reputation_get(late, "guild", "honest"), 0)
        self.assertEqual(R.reputation_metric("standing", late, H.hail_speaker("quill")), 0)

    def test_a_ship_held_quest_still_pays_only_its_ship(self):
        self.load()
        a = self.ship("Artemis", C_COMMS_A)
        b = self.ship("Hera", C_COMMS_B, z=900)
        quest_grant_reward(a, amd_reward("earns guild honest +10"))
        self.assertEqual(R.reputation_get(a, "guild", "honest"), 10)
        self.assertEqual(R.reputation_get(b, "guild", "honest"), 0)
        self.assertEqual(R.reputation_get(Agent.SHARED_ID, "guild", "honest"), 0)

    def test_a_world_held_quest_still_carries_none(self):
        self.load()
        a = self.ship("Artemis", C_COMMS_A)
        station = to_id(npc_spawn(0, 0, 500, "DS 1", "tsn, station", "starbase_command",
                                  "behav_station"))
        quest_grant_reward(station, amd_reward("earns guild honest +10"))
        self.assertEqual(R.reputation_get(a, "guild", "honest"), 0)
        self.assertEqual(R.reputation_get(station, "guild", "honest"), 0)


# --- the whole thing, the way a crew meets it -------------------------------------
class TheCrewHearsTheDifference(Base):
    COLD = "Artemis, DS 1. State your business."
    WARM = "Artemis! Good to hear a friendly voice."
    YARD = "Open the Guild yard to us."

    def test_zero_then_below_thirty_then_past_it(self):
        self.load()
        a = self.ship("Artemis", C_COMMS_A)
        b = self.ship("Hera", C_COMMS_B, z=900)

        # Standing 0: the cold line, and no yard.
        line, offered = self.call(a, "quill_hello")
        self.assertEqual(line, self.COLD)
        self.assertNotIn(self.YARD, offered)
        self.assertTrue(self.answer(a, C_COMMS_A, "Just passing"))

        # The story beat pays: honest 30 with a side that values honest 40 of 70.
        quest_mark_complete(Agent.SHARED_ID, "tag_hulk")
        quill = H.hail_speaker("quill", a)
        self.assertEqual(R.reputation_metric("standing", a, quill), 17)
        line, offered = self.call(a, "quill_hello")
        self.assertEqual(line, self.COLD)
        self.assertNotIn(self.YARD, offered)

        # The answer earns the rest - for the ship that gave it, and no other.
        self.assertTrue(self.answer(a, C_COMMS_A, "We paid"))
        self.assertEqual(R.reputation_metric("standing", a, quill), 30)
        self.assertEqual(R.reputation_metric("standing", b, quill), 17)

        line, offered = self.call(a, "quill_hello")
        self.assertEqual(line, self.WARM)
        self.assertIn(self.YARD, offered)

        # Hera never said it, and is still spoken to as a stranger.
        line, offered = self.call(b, "quill_hello")
        self.assertEqual(line, self.COLD)
        self.assertNotIn(self.YARD, offered)

    def test_a_scene_spoken_by_the_side_itself(self):
        self.load()
        a = self.ship("Artemis", C_COMMS_A)
        line, offered = self.call(a, "guild_hello")
        self.assertEqual(line, "This is the Harbor Guild. Keep to the lane.")
        self.assertEqual(offered, ["Understood."])
        self.answer(a, C_COMMS_A, "Understood")
        R.reputation_adjust(a, "guild", "honest", 60)
        line, offered = self.call(a, "guild_hello")
        self.assertEqual(line, "The Guild knows your ship.")
        self.assertIn("Ask a favor.", offered)


if __name__ == "__main__":
    unittest.main()
