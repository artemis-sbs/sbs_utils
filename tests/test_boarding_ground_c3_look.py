"""Look, Pack and Act on the ground say what is TRUE NOW - three engine-seen slips.

From filming author course 3 (lectures 9 and 10) in the real engine:

  * Look kept the last prop's line after the crew member walked into another area: the
    trail sign's words under the gully's own list, a stale `Pump panel` in the cistern.
  * A pickup was logged under the PROP's name (`Dr Ines Hale picked up Toolbox.`) while
    Pack showed the item (`fuse x2`) - two names for one thing. Then the fix said every
    pickup as `<item> from the <prop>`, which read badly when the prop WAS the thing
    (`pump key from the Pump house key`). The words now follow the prop: gone, its name
    (with the pack's count when the name has none); still standing, `<item> from the`.
  * A `Once: yes` notice was still offered as `Use Brittle notice` after its one use.

Driven through the production entry points (`boarding_interact`, the Look app's own list,
`boarding_points_of_interest`) on a two-area ground.

    python -m unittest tests.test_boarding_ground_c3_look
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

import sbs_utils.mast_sbs.story_nodes  # noqa: F401  (import first: circular import)
import cosmos_dev.mock.sbs as sbs
from sbs_utils.agent import clear_shared
from sbs_utils.gui import GuiClient
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.procedural import boarding as A
from sbs_utils.procedural import tilemap as T
from sbs_utils.procedural import boarding_tiles as BT
from sbs_utils.procedural import boarding_props as P
from sbs_utils.procedural import boarding_checks as C
from sbs_utils.procedural import boarding_combat as K
from sbs_utils.procedural.boarding_hints import boarding_points_of_interest
from sbs_utils.procedural.gui import boarding_gui as G
from sbs_utils.procedural.gui import xess_ground as XG
from sbs_utils.procedural.inventory import set_inventory_value
from sbs_utils.procedural.lifeform import lifeform_spawn

LOOK_CID = 0x8000000000000061

LOOK_YARD = """area: yard
title: The Yard
tileset: g
entry: pad
exits:
  to_shed: shed @door_mat
legend:
  .: dirt
  #: rock
  P: dirt @pad
  E: dirt @to_shed
---
##########
#.P......#
#........#
#.......E#
##########
"""

LOOK_SHED = """area: shed
title: The Shed
tileset: g
entry: door_mat
legend:
  .: dirt
  #: rock
  M: dirt @door_mat
---
######
#.M..#
######
"""

LOOK_KINDS = {"dirt": {"cell": "g:dirt"}, "rock": {"cell": "g:rock", "walk": False}}

LOOK_PROPS = {"children": [
    {"key": "toolbox", "display_text": "Toolbox", "description": "Two fuses.",
     "data": {"area": "yard", "at": "4, 1", "sprite": "g:dirt", "item": "fuse", "qty": "2"}},
    {"key": "coil", "display_text": "Coil", "description": "",
     "data": {"area": "yard", "at": "5, 2", "sprite": "g:dirt", "item": "coil"}},
    {"key": "notice", "display_text": "Brittle notice", "description": "It falls apart.",
     "data": {"area": "yard", "at": "2, 3", "sprite": "g:dirt", "scene": "any",
              "once": "yes"}},
    {"key": "sign", "display_text": "Trail sign", "description": "PUMP HOUSE, east.",
     "data": {"area": "yard", "at": "7, 1", "sprite": "g:dirt"}},
    {"key": "panel", "display_text": "Pump panel", "description": "",
     "data": {"area": "yard", "at": "6, 3", "sprite": "g:dirt", "scene": "any"}},
]}

LOOK_TALK = {"any": {"key": "any", "display_text": "a", "data": {},
                     "description": "% Hm.\n- [Go]()\n"}}


class LookSaysWhatIsTrueNow(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        self.addCleanup(setattr, FrameContext, "context", None)
        SpaceObject.clear()
        clear_shared()
        for clear in (A.boarding_clear, T.tilemap_clear, BT.boarding_tile_clear,
                      P.boarding_props_clear, C.boarding_checks_clear,
                      K.boarding_combat_clear):
            clear()
            self.addCleanup(clear)
        T.tilemap_tileset("g", LOOK_KINDS)
        T.tilemap_load(LOOK_YARD)
        T.tilemap_load(LOOK_SHED)
        T._WATCH["task"] = object()
        K._WATCH["task"] = object()
        T.tilemap_set_clock(0.0)
        ship = lifeform_spawn("Ship", "", "x")
        A.boarding_invite(ship, [], title="Yard", area="yard")
        GuiClient(LOOK_CID)
        body = lifeform_spawn("Hale", "", "boarding,medical")
        set_inventory_value(body.id, A.JOBS_KEY, ["medical"])
        A.boarding_assign(LOOK_CID, body.id)
        self.body = body.id
        P.boarding_props_declare(LOOK_PROPS)
        P.boarding_props_place()
        P.boarding_props_scenes(LOOK_TALK)
        G.boarding_go_down(LOOK_CID)

    def stand(self, area, x, y):
        T.tilemap_place(self.body, area, x, y)

    # --- 4. Look's note belongs to the area it was said in ---------------------------

    def test_the_note_is_shown_where_it_was_said(self):
        self.stand("yard", 7, 2)
        P.boarding_interact(LOOK_CID, "sign")
        self.assertIn("PUMP HOUSE", P.boarding_last_note(LOOK_CID))

    def test_the_note_is_gone_once_you_are_in_another_area(self):
        self.stand("yard", 7, 2)
        P.boarding_interact(LOOK_CID, "sign")
        self.stand("shed", 2, 1)
        self.assertEqual("", P.boarding_last_note(LOOK_CID),
                         "the yard's trail sign was still on Look in the shed")
        self.stand("yard", 7, 2)
        self.assertIn("PUMP HOUSE", P.boarding_last_note(LOOK_CID),
                      "back where it was said, the last word stands")

    # --- 5. A pickup is logged as what went into the pack ----------------------------

    # The words follow the PROP: gone after the pickup, it was the thing lying there
    # and is said by its name; still standing, it was a container the item came out of.

    def test_a_prop_that_goes_is_said_by_its_name_with_the_count_the_pack_shows(self):
        self.stand("yard", 4, 2)
        result, text = P.boarding_interact(LOOK_CID, "toolbox")
        self.assertEqual("picked", result)
        self.assertEqual({"fuse": 2}, P.boarding_pack(self.body))
        self.assertIsNone(P.boarding_prop("toolbox")["id"], "fixture: the toolbox stays")
        self.assertEqual("Picked up Toolbox (fuse x2).", text)
        self.assertIn("Hale picked up Toolbox (fuse x2).", A.boarding_reader_text(LOOK_CID))

    def test_a_prop_that_is_its_item_keeps_its_own_name(self):
        self.stand("yard", 5, 1)
        result, text = P.boarding_interact(LOOK_CID, "coil")
        self.assertEqual(("picked", "Picked up Coil."), (result, text))

    def test_the_c3_pickups_read_as_what_was_picked_up(self):
        """Each one is gone after the pickup, as every `Item:` prop is."""
        cases = [
            # (display name, item, qty, said)
            ("Relay keycard", "relay_key", 1, "Relay keycard"),          # c3-07
            ("Pump house key", "pump_key", 1, "Pump house key"),        # c3-10, not
            #                          `pump key from the Pump house key`
            ("Toolbox", "fuse", 2, "Toolbox (fuse x2)"),                 # c3-10
            ("Two fuses", "fuse", 2, "Two fuses"),                       # c3-13, not
            #                          `fuse x2 from the Two fuses`
            ("coupling", "coupling", 1, "coupling"),                     # c3-16, a drop
        ]
        for name, item, qty, said in cases:
            rec = {"name": name, "item": item, "qty": qty}
            self.assertEqual(said, P.boarding_pickup_text(rec, gone=True), name)

    def test_a_container_that_stays_names_the_item_and_where_it_came_from(self):
        rec = {"name": "Captain's strongbox", "item": "fuse", "qty": 2}
        self.assertEqual("fuse x2 from the Captain's strongbox",
                         P.boarding_pickup_text(rec, gone=False))
        rec = {"name": "The toolbox", "item": "fuse", "qty": 1}
        self.assertEqual("fuse from The toolbox", P.boarding_pickup_text(rec, gone=False))

    def test_interact_reads_the_prop_as_it_is_after_the_pickup(self):
        """`gone` is not assumed: a prop whose removal leaves it standing reads as a
        container."""
        orig = P.boarding_prop_remove
        P.boarding_prop_remove = lambda key: False          # it stays on the map
        self.addCleanup(setattr, P, "boarding_prop_remove", orig)
        self.stand("yard", 4, 2)
        _, text = P.boarding_interact(LOOK_CID, "toolbox")
        self.assertEqual("Picked up fuse x2 from the Toolbox.", text)

    # --- 6. A spent Once prop is not offered -----------------------------------------

    def look_buttons(self):
        return [name for kind, _, name in XG._near(LOOK_CID) if kind == "prop"]

    def test_a_once_prop_is_offered_until_it_is_used_and_then_never(self):
        self.stand("yard", 6, 3)
        far = [t[2] for t in boarding_points_of_interest(LOOK_CID)]
        self.assertIn("Brittle notice", far, "fixture: it should be listed from here")
        self.stand("yard", 2, 2)
        self.assertIn("Brittle notice", self.look_buttons())
        result, _ = P.boarding_interact(LOOK_CID, "notice")
        self.assertEqual("scene", result)
        self.assertNotIn("Brittle notice", self.look_buttons(),
                         "Look still offered `Use Brittle notice` after its one use")
        # Further off does not list it either, and a click still only reads it.
        self.stand("yard", 6, 3)
        far = [t[2] for t in boarding_points_of_interest(LOOK_CID)]
        self.assertNotIn("Brittle notice", far)
        self.stand("yard", 2, 2)
        self.assertEqual(("looked", "It falls apart."),
                         P.boarding_interact(LOOK_CID, "notice"))


    # --- 7. A scene prop with no description leaves no bare name on Look ------------

    def test_a_scene_prop_with_no_description_says_nothing_on_look(self):
        """`Pump panel` (c3-10) and `Captain's strongbox` (c3-15): Look ended in the
        prop's NAME where its description belongs. The scene is in Act; Look says
        nothing - and not the previous prop's line either."""
        self.stand("yard", 7, 2)
        P.boarding_interact(LOOK_CID, "sign")
        self.assertIn("PUMP HOUSE", P.boarding_last_note(LOOK_CID), "fixture")
        self.stand("yard", 6, 2)
        result, _ = P.boarding_interact(LOOK_CID, "panel")
        self.assertEqual("scene", result, "fixture: the panel should open its scene")
        self.assertNotEqual("Pump panel", P.boarding_last_note(LOOK_CID),
                            "Look shows the bare prop name")
        self.assertEqual("", P.boarding_last_note(LOOK_CID),
                         "the trail sign's line is still on Look under the panel")

    def test_a_scene_prop_with_a_description_says_it(self):
        self.stand("yard", 2, 2)
        result, _ = P.boarding_interact(LOOK_CID, "notice")
        self.assertEqual("scene", result)
        self.assertEqual("It falls apart.", P.boarding_last_note(LOOK_CID))


if __name__ == "__main__":
    unittest.main()
