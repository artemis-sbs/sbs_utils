"""amd_items - author game items (upgrades/resources/traps) as an AMD section and register them
into the item registry (labels tagged ``type: item/...``), so ``item_get`` / ``item_keys`` /
``item_meta`` resolve them the same as a hand-written ``prefab_item_<key>`` metadata label.

Run: python -m unittest tests.test_amd_items
"""
import types
import unittest
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.agent import clear_shared
from sbs_utils.mast.maststory import MastStory
from sbs_utils.procedural.items import item_get, item_keys, item_meta, items_of_category
from sbs_utils.procedural.amd_items import (
    items_from_section, items_declare_amd, amd_item_data, item_effect_label_name)


def _section():
    # mimic document_get_amd_file's parsed shape: children with key/display_text/description/data.
    # secret_codecase gets a MAST effect body (prefab_item_secret_codecase); powercell is data-only.
    return {"children": [
        {"key": "secret_codecase", "display_text": "Secret Codecase",
         "description": "Arms a one-shot enemy auto-surrender.",
         "data": {"type": "item/upgrade/comms", "art": "container_1a", "mode": "consumable",
                  "targets": "ship, cockpit", "consoles": "comms", "duration": 300,
                  "tier": 3, "price": 400}},
        {"key": "hidens_powercell", "display_text": "HiDens Power Cell",
         "description": "Instantly restores 500 ship energy when used.",
         "data": {"type": "item/resource/energy", "art": "container_2a", "mode": "resource",
                  "targets": "ship, cockpit", "price": 150}},
    ]}


class AmdItemsTests(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        SpaceObject.clear()
        clear_shared()
        # A story whose `labels` dict is the item registry. Author the effect body for one item
        # (the mission-written path); the other is registered data-only (synthetic label).
        self.story = MastStory()
        self.story.compile(
            "\n->END\n\n=== prefab_item_secret_codecase\n"
            "    set_inventory_value(UPGRADE_AGENT_ID, \"sc_armed\", 1)\n    ->END\n",
            "test", self.story)
        # labels_get_type / item_get resolve the story via FrameContext.page.story.
        FrameContext.page = types.SimpleNamespace(story=self.story)

    def tearDown(self):
        FrameContext.page = None

    def test_records_read(self):
        recs = items_from_section(_section())
        self.assertEqual(len(recs), 2)
        self.assertEqual(recs[0].key, "secret_codecase")
        self.assertEqual(recs[0].name, "Secret Codecase")
        self.assertEqual(recs[0].type, "item/upgrade/comms")
        self.assertEqual(recs[0].art, "container_1a")
        self.assertEqual(recs[0].consoles, "comms")
        self.assertEqual(recs[0].duration, 300)     # numeric coercion preserved
        self.assertEqual(recs[0].tier, 3)
        self.assertEqual(recs[0].price, 400)
        self.assertEqual(recs[1].mode, "resource")

    def test_declare_registers_items(self):
        keys = items_declare_amd(_section())
        self.assertEqual(set(keys), {"secret_codecase", "hidens_powercell"})
        # Registered + queryable via the items.py registry API.
        self.assertEqual(set(item_keys()), {"secret_codecase", "hidens_powercell"})
        self.assertIsNotNone(item_get("secret_codecase"))
        self.assertEqual(item_meta("secret_codecase", "art"), "container_1a")
        self.assertEqual(item_meta("secret_codecase", "display_text"), "Secret Codecase")
        self.assertEqual(item_meta("secret_codecase", "duration"), 300)
        self.assertEqual(item_meta("secret_codecase", "desc"),
                         "Arms a one-shot enemy auto-surrender.")
        # Category query works off the stamped `type`.
        self.assertEqual([l.get_inventory_value("key") for l in items_of_category("resource")],
                         ["hidens_powercell"])
        self.assertEqual([l.get_inventory_value("key") for l in items_of_category("upgrade")],
                         ["secret_codecase"])

    def test_declare_reuses_mission_effect_label(self):
        # The item's metadata is stamped onto the SAME label that carries the effect body, so
        # item_get(key) returns the effect label (upgrade_add runs its body).
        items_declare_amd(_section())
        lbl = item_get("secret_codecase")
        self.assertIs(lbl, self.story.labels[item_effect_label_name("secret_codecase")])
        self.assertTrue(len(lbl.cmds) > 0)   # the authored effect body is present

    def test_data_parser_default_coercion(self):
        d = amd_item_data("Type: item/upgrade/comms\nTier: 3\nPrice: 400\nDuration: 300")
        self.assertEqual(d.get("type"), "item/upgrade/comms")
        self.assertEqual(d.get("tier"), 3)       # amd_num -> int
        self.assertEqual(d.get("price"), 400)
        self.assertEqual(d.get("duration"), 300)

    def test_none_section_safe(self):
        self.assertEqual(items_from_section(None), [])
        self.assertEqual(items_declare_amd(None), [])


if __name__ == "__main__":
    unittest.main()
