"""`follow_route_point_grid` - the only way to reach a `//point/grid` route off a bridge.

WHY THIS FILE EXISTS. The mock never emits `grid_point_selection` - grep `cosmos_dev/`
for it and there is nothing. So the interaction a boarding party is entirely built on -
click a cell of an interior, walk your own figure there - had no unit test, no
`--exercise` coverage and no headless proof of any kind. It could only ever be checked by
a person on a real console, which is why the grid board sat in a scratch mission for
weeks.

The two facts these tests pin are the two that are easy to get wrong and impossible to
notice:

* **`EVENT.client_id` is the clicker; the MAST global `client_id` is not.** The route body
  is started on `FrameContext.server_task` and ticked in place, so `client_id` inside a
  `//point/grid` route is the SERVER - 0 - no matter who clicked. A design that gives each
  console its own figure lives or dies on this one field.
* **`GRID_PARENT_ID` is the ship whose interior was clicked**, which for a boarding party
  is NOT the clicker's own ship.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir

test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.griddispatcher import GridDispatcher
from sbs_utils.procedural.routes import follow_route_point_grid
from sbs_utils.procedural.spawn import player_spawn
from sbs_utils.procedural.query import to_object


class PointGridRouteTests(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        SpaceObject.clear()
        GridDispatcher.clear()
        self.seen = []
        GridDispatcher.add_any_point(self.seen.append)
        self.ship = to_object(player_spawn(0, 0, 0, "Kestrel", "tsn", "tsn_light_cruiser"))

    def tearDown(self):
        GridDispatcher.clear()

    def test_it_reaches_a_point_handler_at_all(self):
        """The mock emits no grid_point_selection, so without this nothing ever fires."""
        follow_route_point_grid(41, self.ship, 4, 18)
        self.assertEqual(1, len(self.seen))

    def test_the_event_carries_the_clicking_console(self):
        follow_route_point_grid(41, self.ship, 4, 18)
        self.assertEqual(41, self.seen[0].client_id)

    def test_two_consoles_are_told_apart(self):
        """The whole per-console design rests on this one field."""
        follow_route_point_grid(41, self.ship, 3, 3)
        follow_route_point_grid(42, self.ship, 17, 17)
        self.assertEqual([41, 42], [e.client_id for e in self.seen])
        self.assertEqual([(3, 3), (17, 17)],
                         [(e.source_point.x, e.source_point.y) for e in self.seen])

    def test_the_cell_is_carried(self):
        """The one thing a GUI click can never give you - a send_gui_* click has a tag."""
        follow_route_point_grid(41, self.ship, 4, 18)
        self.assertEqual(4, self.seen[0].source_point.x)
        self.assertEqual(18, self.seen[0].source_point.y)

    def test_the_parent_is_the_interior_that_was_clicked(self):
        """Not the clicker's own ship: a boarding console is looking at somebody else's."""
        other = to_object(player_spawn(1000, 0, 0, "Derelict", "tsn", "starbase_civil"))
        follow_route_point_grid(41, other, 9, 9)
        self.assertEqual(other.id, self.seen[0].parent_id)
        self.assertNotEqual(self.ship.id, self.seen[0].parent_id)

    def test_the_event_is_frozen_like_the_engines(self):
        """The engine's event is Pybind11 and read-only. A route that re-stamps it works
        only in the mock, so the fake must refuse the assignment here too."""
        follow_route_point_grid(41, self.ship, 4, 18)
        with self.assertRaises(AttributeError):
            self.seen[0].client_id = 99

    def test_the_tag_is_the_one_the_dispatcher_switches_on(self):
        """griddispatcher routes on `event.tag`; the wrong tag reaches nothing and says
        nothing about it."""
        follow_route_point_grid(41, self.ship, 4, 18)
        self.assertEqual("grid_point_selection", self.seen[0].tag)


if __name__ == "__main__":
    unittest.main()
