"""A pickup can be worth several units (item_spawn(..., qty=n)).

Without this a bulk resource needs one object per unit. LegendaryMissions' Sensor Net job
wants 24 salvage, which would have meant 24 separate collectibles scattered across the map
- object churn, and a tedious flight rather than a pickup.

The credit half lives in the mission layer (items/item_collect.mast reads `item_qty`,
defaulting to 1); this covers the library half - that the pickup CARRIES the quantity, and
that a pickup which does not ask for one is left exactly as it was.

    python -m unittest tests.test_item_qty
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.procedural.items import item_spawn
from sbs_utils.procedural.inventory import get_inventory_value


class ItemQtyTests(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        SpaceObject.clear()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())

    def tearDown(self):
        FrameContext.context = None

    def test_a_pickup_carries_its_quantity(self):
        obj = item_spawn("salvage", 0, 0, 0, qty=5)
        self.assertEqual(5, get_inventory_value(obj.id, "item_qty", 1))

    def test_no_qty_leaves_the_pickup_untouched(self):
        """Absent means 1 - the collection route's default - so every pickup that
        predates this behaves exactly as before rather than gaining a stray key."""
        obj = item_spawn("salvage", 0, 0, 0)
        self.assertIsNone(get_inventory_value(obj.id, "item_qty", None))

    def test_qty_of_one_is_not_stamped_either(self):
        obj = item_spawn("salvage", 0, 0, 0, qty=1)
        self.assertIsNone(get_inventory_value(obj.id, "item_qty", None))

    def test_the_key_still_rides_along(self):
        """qty must not displace item_key - that is what the collection route credits."""
        obj = item_spawn("salvage", 0, 0, 0, qty=3)
        self.assertEqual("salvage", get_inventory_value(obj.id, "item_key", ""))


if __name__ == "__main__":
    unittest.main()
