"""A suit's scan files the item's DESCRIPTION, read under the key an item carries.

`amd_items` puts an item's body under `desc` (and LM's `item_defs.mast` metadata writes
`desc:` too); `eva_scan_target` read `description`, which nothing writes, so the reading
it filed to the survey log was empty for every item.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir

test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # noqa: F401  (import first: circular import order)
from cosmos_dev.mock import sbs
from sbs_utils.agent import clear_shared
from sbs_utils.gui import GuiClient
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.mast.maststory import MastStory
from sbs_utils.procedural import eva_tools as T
from sbs_utils.procedural import survey_log as L
from sbs_utils.procedural.amd_items import item_declare
from sbs_utils.procedural.inventory import set_inventory_value
from sbs_utils.procedural.spawn import terrain_spawn
from sbs_utils.procedural.query import to_id
from sbs_utils.spaceobject import SpaceObject

CID = 0x8080000000000071


class TestEvaScanFilesTheDescription(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        sbs.resume_sim()
        SpaceObject.clear()
        clear_shared()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        self.story = MastStory()
        FrameContext.mast = self.story
        # The item registry walks the CURRENT PAGE's story; no page, no items.
        FrameContext.page = type("_Page", (), {"story": self.story, "gui_task": None})()
        GuiClient(CID)
        L.xess_log_clear()

    def tearDown(self):
        L.xess_log_clear()
        FrameContext.mast = None
        FrameContext.page = None
        FrameContext.context = None

    def _scan(self, record):
        key = item_declare(record)
        self.assertEqual(record["key"], key)
        obj = terrain_spawn(0, 0, 0, "Bench", "#,pickup", "container_1a", "behav_asteroid")
        set_inventory_value(to_id(obj), "item_key", key)
        self.assertTrue(T.eva_scan_target(CID, obj))
        return L.xess_log_last()

    def test_an_amd_items_body_is_the_reading(self):
        entry = self._scan({"key": "cold_gel", "name": "Cold Gel", "type": "item/resource",
                            "desc": "The gel is cold and smells of ozone."})
        self.assertIsNotNone(entry)
        self.assertEqual("The gel is cold and smells of ozone.", entry["text"])

    def test_a_label_that_spells_it_description_still_reads(self):
        key = "old_slate"
        item_declare({"key": key, "name": "Old Slate", "type": "item/misc"})
        self.story.labels["prefab_item_" + key].apply_metadata({"description": "Scratched."})
        obj = terrain_spawn(0, 0, 0, "Slate", "#,pickup", "container_1a", "behav_asteroid")
        set_inventory_value(to_id(obj), "item_key", key)
        self.assertTrue(T.eva_scan_target(CID, obj))
        self.assertEqual("Scratched.", L.xess_log_last()["text"])


if __name__ == "__main__":
    unittest.main()
