"""The crew resolution chain: who is at a console, and why.

    python -m unittest tests.test_crew_resolve
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.procedural.amd_doc import amd_document
from sbs_utils.procedural.amd_crew import amd_crew_data, crew_from_document
from sbs_utils.procedural.execution import set_shared_variable
from sbs_utils.procedural.inventory import set_inventory_value
from sbs_utils.procedural.spawn import npc_spawn
from sbs_utils.gui import GuiClient
import sbs_utils.procedural.crew as crew


CAST = """# [Rosters](rosters)

## [Enterprise-D](tng_d)
---
crew
Hull: tsn_battle_cruiser
Ship: Enterprise
Race: terran
Portraits: media/crew/tng
---

### [William Riker](riker)
---
Rank: Commander
Console: helm
---

### [Data](data)
---
Console: science
Portrait: data
---

### [Ensign Ro](ro)
---
Rank: Ensign
---

## [Deep Space Nine](ds9)
---
crew
Ship: Defiant
---

### [Kira Nerys](kira)
---
Console: helm
---

## [Thursday Night Crew](thursday)
---
crew
By: person
---

### [Doug](doug)
---
Rank: Captain
---

### [Marty](marty)
---
"""


KLINGON = """# [R](r)

## [Klingon Watch](klg)
---
crew
Race: klingon
---

### [K'tal](ktal)
---
Console: helm
---
"""


class CrewCase(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        SpaceObject.clear()
        self._clients = {}
        crew.crew_clear()
        crew.crew_names_clear()
        set_shared_variable("CREW_SELECT", "")
        crew.crew_declare(crew_from_document(
            amd_document(CAST, data_parser=amd_crew_data)))

    def tearDown(self):
        crew.crew_clear()
        crew.crew_names_clear()
        self.autoname(True)

    def ship(self, name, hull="tsn_battle_cruiser"):
        return npc_spawn(0, 0, 0, name, "tsn", hull, "behav_npcship")

    def autoname(self, on):
        """CREW_AUTONAME is a library built-in, so override it the way an operator would."""
        from sbs_utils.procedural.settings import settings_get_defaults
        settings_get_defaults()["CREW_AUTONAME"] = bool(on)

    def seat(self, client_id, console):
        """Make a client genuinely LOOK seated, which is what occupancy is believed from.

        A bare integer is not enough: inventory lives on an AGENT, and a client id with no
        agent behind it silently drops every write - which reads as "the seat never took".
        """
        if client_id not in self._clients:
            self._clients[client_id] = GuiClient(client_id)
        set_inventory_value(client_id, "CONSOLE_TYPE", console)


class TestTiers(CrewCase):
    def test_a_ship_bound_by_name_wins(self):
        s = self.ship("Enterprise")
        post = crew.crew_resolve(1, s.id, "helm")
        self.assertEqual(post.name, "William Riker")
        self.assertEqual(post.source, "ship")

    def test_the_hull_default_staffs_a_ship_nobody_named(self):
        s = self.ship("Random Freighter")
        post = crew.crew_resolve(1, s.id, "science")
        self.assertEqual(post.name, "Data")
        self.assertEqual(post.source, "hull")

    def test_crew_select_beats_the_hull_default(self):
        s = self.ship("Random Freighter")
        set_shared_variable("CREW_SELECT", "ds9")
        post = crew.crew_resolve(1, s.id, "helm")
        self.assertEqual(post.name, "Kira Nerys")
        self.assertEqual(post.source, "map")

    def test_a_ship_binding_beats_crew_select(self):
        s = self.ship("Enterprise")
        set_shared_variable("CREW_SELECT", "ds9")
        post = crew.crew_resolve(1, s.id, "helm")
        self.assertEqual(post.name, "William Riker")
        self.assertEqual(post.source, "ship")

    def test_what_the_player_typed_beats_every_roster(self):
        s = self.ship("Enterprise")
        post = crew.crew_resolve(1, s.id, "helm", own_name="Doug")
        self.assertEqual(post.name, "Doug")
        self.assertEqual(post.source, "own")

    def test_an_unbound_hull_still_gets_a_name(self):
        # No roster reaches this ship at all, and the console is named anyway. This is the
        # whole point of the feature: the crew name existed for years and almost nobody
        # typed one, so every seat on air read "unmanned".
        s = self.ship("Nobody", hull="tsn_light_cruiser")
        post = crew.crew_resolve(1, s.id, "helm")
        self.assertTrue(post.name)
        self.assertEqual(post.source, "library")

    def test_it_is_unmanned_only_when_autoname_is_off(self):
        self.autoname(False)
        s = self.ship("Nobody", hull="tsn_light_cruiser")
        post = crew.crew_resolve(1, s.id, "helm")
        self.assertEqual(post.name, "")
        self.assertEqual(post.source, crew.SOURCE_UNMANNED)

    def test_a_floating_officer_fills_a_console_nobody_named(self):
        s = self.ship("Enterprise")
        post = crew.crew_resolve(1, s.id, "engineering")
        self.assertEqual(post.name, "Ensign Ro")

    def test_a_member_face_is_stable_across_calls(self):
        # `face_resolve` rolls a fresh face every call, so a member with no Face: of their
        # own used to look like a different person on every repaint.
        s = self.ship("Enterprise")
        first = crew.crew_resolve(1, s.id, "helm").face
        second = crew.crew_resolve(2, s.id, "helm").face
        self.assertTrue(first)
        self.assertEqual(first, second)

    def test_a_portrait_is_resolved_against_the_roster_folder(self):
        s = self.ship("Enterprise")
        self.assertEqual(crew.crew_resolve(1, s.id, "science").portrait,
                         "media/crew/tng/data")


class TestLibraryTier(CrewCase):
    def test_a_seat_the_roster_missed_is_named_from_the_stock_pool(self):
        # The DS9 roster only crews helm; weapons is filled automatically.
        s = self.ship("Defiant")
        post = crew.crew_resolve(1, s.id, "weapons")
        self.assertTrue(post.name)
        self.assertEqual(post.source, "library")

    def test_a_registered_pool_fills_a_seat_the_roster_left_empty(self):
        crew.crew_register_names("weapons", ["Ensign Vega"])
        s = self.ship("Defiant")
        post = crew.crew_resolve(1, s.id, "weapons")
        self.assertEqual(post.name, "Ensign Vega")
        self.assertEqual(post.source, "library")

    def test_a_registered_pool_is_consulted_before_the_stock_one(self):
        # A base game or a total conversion replaces the stock names by registering its own.
        crew.crew_register_names("helm", ["Ensign Vega"])
        s = self.ship("Nobody", hull="tsn_light_cruiser")
        self.assertEqual(crew.crew_resolve(1, s.id, "helm").name, "Ensign Vega")

    def test_every_console_in_a_run_gets_a_DIFFERENT_person(self):
        # Uniqueness is what makes a Director bridge wall readable - all of them are on
        # screen at once.
        s = self.ship("Nobody", hull="tsn_light_cruiser")
        names = [crew.crew_resolve(i, s.id, "helm").name for i in range(40)]
        self.assertEqual(len(names), len(set(names)))
        self.assertTrue(all(names))

    def test_a_registered_pool_running_out_falls_through_to_the_stock_one(self):
        crew.crew_register_names("helm", ["Ensign Vega"])
        s = self.ship("Nobody", hull="tsn_light_cruiser")
        first = crew.crew_resolve(1, s.id, "helm").name
        second = crew.crew_resolve(2, s.id, "helm").name
        self.assertEqual(first, "Ensign Vega")
        self.assertTrue(second)
        self.assertNotEqual(second, first)

    def test_an_automatic_name_follows_the_player_between_stations(self):
        # crew_assign runs on every console selection. Re-rolling each time would rename a
        # player the moment they moved seat, and the old name would stay claimed so they
        # could never get it back.
        s = self.ship("Nobody", hull="tsn_light_cruiser")
        self.seat(10, "helm")
        first = crew.crew_assign(10, s.id, "helm")
        self.seat(10, "weapons")
        second = crew.crew_assign(10, s.id, "weapons")
        self.assertTrue(first.name)
        self.assertEqual(second.name, first.name)
        self.assertEqual(second.face, first.face)

    def test_re_selecting_the_same_console_keeps_the_name(self):
        s = self.ship("Nobody", hull="tsn_light_cruiser")
        self.seat(10, "helm")
        first = crew.crew_assign(10, s.id, "helm").name
        self.assertEqual(crew.crew_assign(10, s.id, "helm").name, first)

    def test_a_typed_name_still_replaces_an_automatic_one(self):
        # Tier 1 is checked before the held name, so a player can always name themselves.
        s = self.ship("Nobody", hull="tsn_light_cruiser")
        self.seat(10, "helm")
        auto = crew.crew_assign(10, s.id, "helm").name
        typed = crew.crew_assign(10, s.id, "helm", own_name="Doug")
        self.assertEqual(typed.name, "Doug")
        self.assertEqual(typed.source, "own")
        self.assertNotEqual(auto, "Doug")

    def test_two_clients_still_get_different_automatic_names(self):
        s = self.ship("Nobody", hull="tsn_light_cruiser")
        self.seat(10, "helm")
        self.seat(11, "helm")
        self.assertNotEqual(crew.crew_assign(10, s.id, "helm").name,
                            crew.crew_assign(11, s.id, "helm").name)

    def test_the_face_is_a_real_face_string_not_the_hull_side(self):
        # A hull's shipData `side` is "TSN" - a SIDE, not a face race. `face_resolve` passes
        # an unrecognized spec through as a LITERAL face string, so this used to hand "TSN"
        # to send_gui_face. A face string is `alias #color col row;` and nothing else.
        s = self.ship("Nobody", hull="tsn_light_cruiser")
        face = crew.crew_resolve(1, s.id, "helm").face
        self.assertTrue(face)
        self.assertIn(" ", face)
        self.assertIn(";", face)
        self.assertNotIn(face.strip().lower(), ("tsn", "terran", "klingon"))

    def test_a_roster_race_a_mod_registered_resolves_to_that_races_face(self):
        # `Race: klingon` must not become the literal face string "klingon" - the mod case
        # this whole feature exists for.
        from sbs_utils.faces import face_register_race
        face_register_race("klingon", ["tng2 #fff 0 0;"])
        crew.crew_declare(crew_from_document(amd_document(KLINGON, data_parser=amd_crew_data)))
        crew.crew_bind_ship("Bird of Prey", "klg")
        s = self.ship("Bird of Prey")
        self.assertEqual(crew.crew_resolve(1, s.id, "helm").face, "tng2 #fff 0 0;")


    def test_names_are_released_by_the_run_reset(self):
        # "Unique per RUN" is exactly the lifetime of the used-name set.
        s = self.ship("Nobody", hull="tsn_light_cruiser")
        crew.crew_resolve(1, s.id, "helm")
        self.assertTrue(crew._USED_NAMES)
        crew.crew_names_clear()
        self.assertFalse(crew._USED_NAMES)


class TestByPerson(CrewCase):
    def setUp(self):
        super().setUp()
        set_shared_variable("CREW_SELECT", "thursday")

    def test_it_never_auto_assigns_one_of_ITS_people(self):
        # The seat still gets a name - but never Doug's. Handing a real person's face to
        # whoever opened helm first is exactly what a group roster exists to avoid.
        s = self.ship("Anything")
        post = crew.crew_resolve(1, s.id, "helm")
        self.assertNotIn(post.name, ("Doug", "Marty"))
        self.assertEqual(post.source, "library")

    def test_a_picked_person_follows_you_between_seats(self):
        s = self.ship("Anything")
        pick = crew.crew_pick_value("thursday", "doug")
        self.assertEqual(crew.crew_resolve(1, s.id, "helm", own_pick=pick).name, "Doug")
        self.assertEqual(crew.crew_resolve(1, s.id, "weapons", own_pick=pick).name, "Doug")

    def test_an_unloadable_pick_is_ignored_not_an_error(self):
        # The pick persists on the player's machine; the roster that gave it meaning belongs
        # to one mod. Joining a game without that mod must simply fall through.
        s = self.ship("Anything")
        post = crew.crew_resolve(1, s.id, "helm", own_pick="nosuchmod:someone")
        self.assertNotIn(post.name, ("Doug", "Marty"))

    def test_a_typed_name_still_overrides_a_picked_person(self):
        s = self.ship("Anything")
        pick = crew.crew_pick_value("thursday", "doug")
        post = crew.crew_resolve(1, s.id, "helm", own_pick=pick, own_name="Douglas")
        self.assertEqual(post.name, "Douglas")

    def test_it_offers_everyone_free_regardless_of_console(self):
        s = self.ship("Anything")
        self.assertEqual([m.name for m in crew.crew_choices_for(s.id, "weapons")],
                         ["Doug", "Marty"])


class TestSelection(CrewCase):
    def test_a_roster_resolves_from_key_name_index_or_substring(self):
        for spec in ("tng_d", "Enterprise-D", 0, "enterprise-d"):
            self.assertEqual(crew.crew_find(spec).key, "tng_d", spec)

    def test_an_ambiguous_spec_returns_none_rather_than_guessing(self):
        self.assertIsNone(crew.crew_find("e"))

    def test_empty_selects_nothing(self):
        self.assertIsNone(crew.crew_select(""))
        self.assertIsNone(crew.crew_select(None))
        self.assertIsNone(crew.crew_select("none"))

    def test_random_picks_one(self):
        self.assertIn(crew.crew_select("random").key, ("tng_d", "ds9", "thursday"))

    def test_a_miss_warns_by_name_and_selects_nothing(self):
        # crew_select imports `log` inside the function, so patching the module is enough.
        said = []
        from sbs_utils.procedural import execution
        original = execution.log
        execution.log = lambda msg, name=None, level=None: said.append(msg)
        try:
            self.assertIsNone(crew.crew_select("Enterprize"))
        finally:
            execution.log = original
        self.assertTrue(said, "a miss must not be silent")
        self.assertIn("Enterprize", said[0])
        self.assertIn("tng_d", said[0])       # it lists what IS available


class TestSeats(CrewCase):
    def test_two_clients_at_one_console_get_different_people(self):
        s = self.ship("Enterprise")
        self.seat(10, "science")
        first = crew.crew_assign(10, s.id, "science")
        self.seat(11, "science")
        second = crew.crew_assign(11, s.id, "science")
        self.assertEqual(first.name, "Data")
        self.assertEqual(second.name, "Ensign Ro")
        self.assertEqual(crew.crew_seat_count(), 2)

    def test_the_same_client_re_resolving_keeps_its_person(self):
        s = self.ship("Enterprise")
        self.seat(10, "science")
        self.assertEqual(crew.crew_assign(10, s.id, "science").name, "Data")
        self.assertEqual(crew.crew_assign(10, s.id, "science").name, "Data")

    def test_one_roster_on_two_ships_fills_each_from_the_top(self):
        a, b = self.ship("Enterprise"), self.ship("Enterprise-D")
        self.seat(10, "helm")
        self.seat(11, "helm")
        self.assertEqual(crew.crew_assign(10, a.id, "helm").name, "William Riker")
        self.assertEqual(crew.crew_assign(11, b.id, "helm").name, "William Riker")

    def test_a_seat_frees_itself_when_the_client_moves_on(self):
        # SELF-HEALING. No disconnect hook: a seat is believed only while the client's own
        # CONSOLE_TYPE still agrees with it.
        s = self.ship("Enterprise")
        self.seat(10, "science")
        self.assertEqual(crew.crew_assign(10, s.id, "science").name, "Data")
        self.seat(10, "comms")                      # they walked to another station
        self.seat(11, "science")
        self.assertEqual(crew.crew_assign(11, s.id, "science").name, "Data")

    def test_crew_release_frees_the_seat_at_once(self):
        s = self.ship("Enterprise")
        self.seat(10, "science")
        crew.crew_assign(10, s.id, "science")
        self.assertEqual(crew.crew_seat_count(), 1)
        crew.crew_release(10)
        self.assertEqual(crew.crew_seat_count(), 0)

    def test_assign_publishes_crew_name_unchanged(self):
        # The whole reason this drops into the existing seam: the Director's <<crew_name>>
        # token and the Gamemaster's message list read this key and need no edit.
        from sbs_utils.procedural.inventory import get_inventory_value
        s = self.ship("Enterprise")
        self.seat(10, "helm")
        crew.crew_assign(10, s.id, "helm")
        self.assertEqual(get_inventory_value(10, "CREW_NAME", None), "William Riker")
        self.assertEqual(get_inventory_value(10, "CREW_RANK", None), "Commander")
        self.assertEqual(get_inventory_value(10, "CREW_SOURCE", None), "ship")

    def test_a_name_with_braces_cannot_reach_a_format_string(self):
        s = self.ship("Enterprise")
        post = crew.crew_resolve(1, s.id, "helm", own_name="Foo{bar}")
        self.assertNotIn("{", post.name)


class TestReset(CrewCase):
    def test_clear_drops_rosters_bindings_and_seats(self):
        s = self.ship("Enterprise")
        self.seat(10, "helm")
        crew.crew_assign(10, s.id, "helm")
        self.assertTrue(crew.crew_count())
        self.assertTrue(crew.crew_seat_count())
        crew.crew_clear()
        self.assertEqual(crew.crew_count(), 0)
        self.assertEqual(crew.crew_seat_count(), 0)

    def test_declaring_the_same_roster_twice_does_not_duplicate(self):
        # An in-process recompile re-registers every file.
        before = crew.crew_count()
        crew.crew_declare(crew_from_document(
            amd_document(CAST, data_parser=amd_crew_data)))
        self.assertEqual(crew.crew_count(), before)
        self.assertEqual(len(crew.crew_rosters()), 3)


if __name__ == "__main__":
    unittest.main()
