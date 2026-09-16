"""Rooms that notice the party - the join between walking and the story.

Until this existed the two halves of a boarding mission never met: `boarding_site.py`
knew where everybody was standing and `boarding.py` knew what a scene was, and a party
could walk into the lab without the lab noticing.

THE RULE IS ONCE PER ROOM, NOT ONCE PER PERSON, and it is the only interesting thing
here. The probe paid for it in the engine: three characters walked into one airlock, a
per-person trigger fired three times, and the scene restarted twice - re-rolling its
random line in front of everybody. Regrouping is a normal thing for a party to do and it
has to be silent. `test_a_second_arrival_is_silent` is that lesson, pinned.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir

test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.agent import Agent
from sbs_utils.gui import GuiClient
from sbs_utils.procedural import boarding_site as B
from sbs_utils.procedural.grid import grid_objects, grid_pos_data
from sbs_utils.procedural.lifeform import lifeform_spawn
from sbs_utils.procedural.query import to_id, to_object
from sbs_utils.procedural.roles import any_role, role
from sbs_utils.procedural.spawn import npc_spawn

CONSOLES = [0x8000000000000001, 0x8000000000000002, 0x8000000000000003]


class _RoomBase(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        SpaceObject.clear()
        B.boarding_site_clear()
        self.fired = []
        from sbs_utils.procedural import signal as S
        self._real_emit = S.signal_emit

        def spy(name, data=None, **kw):
            if name in ("boarding_entered", "boarding_left"):
                self.fired.append((name, dict(data or {})))
            return self._real_emit(name, data, **kw)

        S.signal_emit = spy
        self.addCleanup(setattr, S, "signal_emit", self._real_emit)
        # boarding_site imports signal_emit inside the function, so patching the module
        # attribute is what the tick actually reaches.

        for cid in CONSOLES:
            GuiClient(cid)
        # `tsn_destroyer`, NOT `starbase_civil`: the station has no stock interior at all
        # (`grid_data.json` holds none), so building it yields zero rooms and every test
        # here would be asserting against an empty ship.
        self.site = to_object(npc_spawn(3000, 0, 3000, "Kepler", "tsn",
                                        "tsn_destroyer", "behav_station"))
        B.boarding_site_build(self.site)
        # BY NAME. A room is drawn one grid node per CELL, so a lab is several objects all
        # called the same thing - which is exactly why the trigger keys on the name.
        nodes = grid_objects(self.site.id) & any_role(B.ROOM_ROLES)
        self.by_name = {}
        for n in nodes:
            so = to_object(n)
            if so is not None:
                # `boarding_room_name`, not `.name`: the builder names each node
                # "<room>:<x>,<y>", so the raw name is per-CELL.
                self.by_name.setdefault(B.boarding_room_name(so.name), []).append(n)
        self.room_names = sorted(self.by_name)
        self.assertGreaterEqual(len(self.room_names), 2, "fixture needs two named rooms")
        self.rooms = [self.by_name[n][0] for n in self.room_names]
        self.people = [lifeform_spawn("Boarder %d" % i, "terran_male", "boarding,science")
                       for i in range(len(CONSOLES))]

    def tearDown(self):
        B.boarding_site_clear()

    def cell_of(self, room):
        at = grid_pos_data(to_id(room))
        return int(at[0]), int(at[1])

    def put(self, i, room):
        """Stand console i's figure on this room node, and give the console that figure."""
        x, y = self.cell_of(room)
        fig = B.boarding_figure_of(self.people[i])
        if fig is None:
            fig = B.boarding_figure_spawn(self.site, self.people[i], x, y)
            B.boarding_take(CONSOLES[i], fig, self.site)
        else:
            blob = to_object(fig).data_set
            blob.set("curx", x, 0)
            blob.set("cury", y, 0)
        return fig

    def names(self):
        return [n for n, _ in self.fired]


class ARoomWakesWhenThePartyArrives(_RoomBase):
    def test_arriving_fires_once(self):
        self.put(0, self.rooms[0])
        B.boarding_rooms_tick()
        self.assertEqual(["boarding_entered"], self.names())

    def test_it_says_which_room_and_who(self):
        self.put(0, self.rooms[0])
        B.boarding_rooms_tick()
        _, data = self.fired[0]
        self.assertEqual(self.room_names[0], data["BOARDING_ROOM_NAME"])
        self.assertEqual(CONSOLES[0], data["BOARDING_CLIENT"])
        self.assertEqual(to_id(self.people[0]), data["BOARDING_WHO"])
        self.assertEqual(self.site.id, data["BOARDING_SITE"])
        self.assertTrue(data["BOARDING_ROOM_NAME"])

    def test_standing_still_does_not_fire_again(self):
        self.put(0, self.rooms[0])
        B.boarding_rooms_tick()
        B.boarding_rooms_tick()
        B.boarding_rooms_tick()
        self.assertEqual(["boarding_entered"], self.names())

    def test_a_second_arrival_is_silent(self):
        """THE LESSON THE PROBE PAID FOR. Three people into one airlock fired three
        times and restarted the scene twice, re-rolling its line in front of everybody."""
        self.put(0, self.rooms[0])
        B.boarding_rooms_tick()
        self.put(1, self.rooms[0])
        self.put(2, self.rooms[0])
        B.boarding_rooms_tick()
        self.assertEqual(["boarding_entered"], self.names())

    def test_two_different_rooms_are_two_events(self):
        self.put(0, self.rooms[0])
        self.put(1, self.rooms[1])
        B.boarding_rooms_tick()
        self.assertEqual(["boarding_entered", "boarding_entered"], self.names())
        got = {d["BOARDING_ROOM_NAME"] for _, d in self.fired}
        self.assertEqual({self.room_names[0], self.room_names[1]}, got)




class ARoomIsDrawnPerCell(unittest.TestCase):
    """The reason the trigger keys on a NAME instead of a grid object.

    An authored floor plan (`grid_ascii`) makes one grid node per lettered CELL, all
    carrying the room's name - so a lab three cells across is three objects called
    "site-lab". Keyed on the node, walking from one side of that lab to the other would
    fire three arrivals and three departures for a room nobody ever left.

    Stock `grid_data.json` names each node uniquely ("Cabin 1", "Cabin 2"), which is why
    this needs its own fixture: the stock hulls cannot show the bug.
    """

    PLAN = """ship: tsn_destroyer
layout: boarding_rooms_test
size: 11x8
legend:
  l: site-lab / room,science
  a: site-airlock / room,access
---
...........
...aaa.....
...lll.....
...........
...........
...........
...........
...........
"""
    # Rows 1 and 2 only, columns 3-5. The hull mask for `tsn_destroyer` is a real
    # silhouette (`..#######..` / `.#########.` / ...), and a room cell placed OFF the
    # hull is silently refused - the first version of this plan put the lab on row 4,
    # where the mask reads `..#..#..#..`, and built nothing.

    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        SpaceObject.clear()
        B.boarding_site_clear()
        from sbs_utils.procedural.grid import grid_merge_ascii
        grid_merge_ascii(self.PLAN, "test_boarding_rooms", "tsn_destroyer")
        self.fired = []
        from sbs_utils.procedural import signal as S
        real = S.signal_emit

        def spy(name, data=None, **kw):
            if name in ("boarding_entered", "boarding_left"):
                self.fired.append((name, dict(data or {})))
            return real(name, data, **kw)

        S.signal_emit = spy
        self.addCleanup(setattr, S, "signal_emit", real)
        GuiClient(CONSOLES[0])
        self.site = to_object(npc_spawn(0, 0, 0, "Kepler", "tsn", "tsn_destroyer",
                                        "behav_station"))
        B.boarding_site_build(self.site, layout="boarding_rooms_test")
        self.who = lifeform_spawn("Boarder", "terran_male", "boarding,science")
        self.lab = [n for n in grid_objects(self.site.id)
                    if (to_object(n) is not None
                        and B.boarding_room_name(to_object(n).name) == "site-lab")]
        self.assertGreater(len(self.lab), 1, "the lab must span several cells")

    def tearDown(self):
        B.boarding_site_clear()

    def stand_on(self, node):
        at = grid_pos_data(to_id(node))
        fig = B.boarding_figure_of(self.who)
        if fig is None:
            fig = B.boarding_figure_spawn(self.site, self.who, int(at[0]), int(at[1]))
            B.boarding_take(CONSOLES[0], fig, self.site)
        else:
            blob = to_object(fig).data_set
            blob.set("curx", int(at[0]), 0)
            blob.set("cury", int(at[1]), 0)
        return fig

    def test_crossing_one_room_is_ONE_arrival(self):
        for node in self.lab:
            self.stand_on(node)
            B.boarding_rooms_tick()
        self.assertEqual(["boarding_entered"],
                         [n for n, _ in self.fired],
                         "walking across one lab reported arriving in it repeatedly")

    def test_and_leaving_it_is_ONE_departure(self):
        for node in self.lab:
            self.stand_on(node)
            B.boarding_rooms_tick()
        self.fired.clear()
        airlock = next(n for n in grid_objects(self.site.id)
                       if to_object(n) is not None
                       and B.boarding_room_name(to_object(n).name) == "site-airlock")
        self.stand_on(airlock)
        B.boarding_rooms_tick()
        self.assertEqual(["boarding_left", "boarding_entered"],
                         sorted([n for n, _ in self.fired], reverse=True))


class AndSleepsWhenTheyLeave(_RoomBase):
    def test_the_last_one_out_fires_left(self):
        self.put(0, self.rooms[0])
        B.boarding_rooms_tick()
        self.fired.clear()
        self.put(0, self.rooms[1])
        B.boarding_rooms_tick()
        self.assertIn("boarding_left", self.names())

    def test_leaving_somebody_behind_does_NOT(self):
        self.put(0, self.rooms[0])
        self.put(1, self.rooms[0])
        B.boarding_rooms_tick()
        self.fired.clear()
        self.put(0, self.rooms[1])          # one walks out, one stays
        B.boarding_rooms_tick()
        self.assertNotIn("boarding_left", self.names())

    def test_a_room_can_wake_a_second_time(self):
        """Revisiting is normal. A once-per-mission latch would make the second half of
        a mission silent."""
        self.put(0, self.rooms[0])
        B.boarding_rooms_tick()
        self.put(0, self.rooms[1])
        B.boarding_rooms_tick()
        self.fired.clear()
        self.put(0, self.rooms[0])
        B.boarding_rooms_tick()
        self.assertIn("boarding_entered", self.names())


class WhatCountsAsBeingSomewhere(_RoomBase):
    def test_a_corridor_is_travel_not_arrival(self):
        """A floor plan is mostly hallway. If those fired, crossing a ship would be a
        dozen arrivals and the signal would be worth nothing."""
        from sbs_utils.procedural.grid import grid_objects_at
        empty = None
        for x in range(40):
            for y in range(40):
                here = grid_objects_at(self.site.id, x, y)
                if not (here & any_role(B.ROOM_ROLES)):
                    empty = (x, y)
                    break
            if empty:
                break
        self.assertIsNotNone(empty, "fixture has no cell outside a room")
        fig = B.boarding_figure_spawn(self.site, self.people[0], empty[0], empty[1])
        B.boarding_take(CONSOLES[0], fig, self.site)
        B.boarding_rooms_tick()
        self.assertEqual([], self.names())

    def test_a_figure_is_not_a_room(self):
        """Two figures on one cell must not read as one standing in the other."""
        self.put(0, self.rooms[0])
        self.put(1, self.rooms[0])
        B.boarding_rooms_tick()
        for _, d in self.fired:
            self.assertNotIn(d["BOARDING_ROOM"], [to_id(f) for f in role(B.FIGURE_ROLE)])


class ResetAndBookkeeping(_RoomBase):
    def test_clearing_forgets_every_room(self):
        self.put(0, self.rooms[0])
        B.boarding_rooms_tick()
        self.assertEqual(1, B.boarding_room_count())
        B.boarding_site_clear()
        self.assertEqual(0, B.boarding_room_count())

    def test_watching_twice_watches_once(self):
        a = B.boarding_rooms_watch()
        b = B.boarding_rooms_watch()
        self.assertIs(a, b)
        B.boarding_rooms_unwatch()

    def test_the_console_can_be_found_from_the_figure(self):
        fig = self.put(0, self.rooms[0])
        self.assertEqual(CONSOLES[0], B.boarding_client_of_figure(fig))

    def test_an_undriven_figure_has_no_console(self):
        fig = B.boarding_figure_spawn(self.site, self.people[2], 5, 5)
        self.assertIsNone(B.boarding_client_of_figure(fig))


if __name__ == "__main__":
    unittest.main()
