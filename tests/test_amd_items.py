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
from sbs_utils.gui import GuiClient
from sbs_utils.mast.maststory import MastStory
from sbs_utils.mast.mast_globals import MastGlobals
from sbs_utils.mast_sbs.maststoryscheduler import StoryScheduler

# Make procedural functions resolvable inside the compiled story's eval namespace (as a real
# mission does), so a hand-authored effect body (set_inventory_value) actually runs.
MastGlobals.import_python_module('sbs_utils.procedural.inventory')
from sbs_utils.procedural.items import item_get, item_keys, item_meta, items_of_category
from sbs_utils.procedural.spawn import npc_spawn
from sbs_utils.procedural.upgrades import upgrade_add
from sbs_utils.procedural.modifiers import modifiers_get_for_object
from sbs_utils.procedural.amd_items import (
    items_from_section, items_declare_amd, amd_item_data, amd_parse_modifiers,
    item_effect_label_name)


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


def _mod_section():
    # Two fully-declarative modifier items (no MAST body): one single modifier, one multiple.
    return {"children": [
        {"key": "carapaction_coil", "display_text": "Carapaction Coil",
         "description": "Reinforces shields for a time.",
         "data": {"type": "item/upgrade/defense", "art": "alien_2a", "mode": "consumable",
                  "duration": 300, "tier": 2, "price": 250,
                  "modifiers": "all_shield_upgrade_coeff 2.0"}},
        {"key": "infusion_pcoils", "display_text": "Infusion P-Coils",
         "description": "Boosts impulse and turn for a time.",
         "data": {"type": "item/upgrade/helm", "art": "danger_4a", "mode": "consumable",
                  "duration": 300, "tier": 2, "price": 250,
                  "modifiers": "impulse_upgrade_coeff 2.0, turn_upgrade_coeff 3.0"}},
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
        # A real server page + task so upgrade activation runs exactly as production
        # (Upgrade.activate -> task_schedule_server needs FrameContext.server_task, which resolves
        # to Agent.get(0).page.gui_task). The page carries `.story` so the item registry resolves.
        FrameContext.mast = self.story
        self.sched = StoryScheduler(self.story)
        self.page = types.SimpleNamespace(story=self.story, gui_task=None)
        self.page.gui_task = self.sched.run(0, self.page, "main", None, None, True)
        self.server = GuiClient(0)          # registers Agent id 0
        self.server.page_stack.append(self.page)
        # labels_get_type / item_get resolve the story via FrameContext.page.story.
        FrameContext.page = self.page

    def tearDown(self):
        # Full reset so nothing leaks into later test files. In particular FrameContext.task must
        # be cleared: a leftover task makes another file's task_schedule() resolve to THIS dead
        # scheduler's main (raising on labels it never compiled). Also drop the server GuiClient.
        FrameContext.task = None
        FrameContext.page = None
        FrameContext.mast = None
        SpaceObject.clear()
        clear_shared()

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

    # --- Declarative modifier effect (no MAST body) --------------------------------

    def test_modifiers_parse_to_structured_list(self):
        recs = items_from_section(_mod_section())
        self.assertEqual(recs[0].modifiers, [["all_shield_upgrade_coeff", 2.0]])
        self.assertEqual(recs[1].modifiers,
                         [["impulse_upgrade_coeff", 2.0], ["turn_upgrade_coeff", 3.0]])
        # amd_parse_modifiers helper handles blank/None and already-structured input.
        self.assertEqual(amd_parse_modifiers(None), [])
        self.assertEqual(amd_parse_modifiers(""), [])
        self.assertEqual(amd_parse_modifiers("scan_range 500"), [["scan_range", 500.0]])

    def test_modifiers_stamped_on_label_metadata(self):
        items_declare_amd(_mod_section())
        self.assertEqual(item_meta("carapaction_coil", "modifiers"),
                         [["all_shield_upgrade_coeff", 2.0]])

    def test_declared_modifier_applies_on_activation(self):
        items_declare_amd(_mod_section())
        ship = npc_spawn(0, 0, 0, "Artemis", "tsn", "tsn_light_cruiser", "behav_npcship")
        item = item_get("carapaction_coil")
        upgrade_add(ship.id, item, data={"key": "carapaction_coil"}, activate=True)
        mods = modifiers_get_for_object(ship.id, "all_shield_upgrade_coeff")
        self.assertEqual(len(mods), 1)
        self.assertEqual(mods[0].key, "all_shield_upgrade_coeff")
        self.assertEqual(mods[0].source, "carapaction_coil")
        self.assertEqual(mods[0].value[0], 2.0)

    def test_multiple_declared_modifiers_all_apply(self):
        items_declare_amd(_mod_section())
        ship = npc_spawn(0, 0, 0, "Intrepid", "tsn", "tsn_light_cruiser", "behav_npcship")
        item = item_get("infusion_pcoils")
        upgrade_add(ship.id, item, data={"key": "infusion_pcoils"}, activate=True)
        imp = modifiers_get_for_object(ship.id, "impulse_upgrade_coeff")
        trn = modifiers_get_for_object(ship.id, "turn_upgrade_coeff")
        self.assertEqual(len(imp), 1)
        self.assertEqual(imp[0].value[0], 2.0)
        self.assertEqual(len(trn), 1)
        self.assertEqual(trn[0].value[0], 3.0)

    def test_body_based_item_still_runs_no_regression(self):
        # secret_codecase has a hand-written body (set_inventory_value) and NO Modifiers field.
        # The body must still run, and no stray modifiers should be applied.
        items_declare_amd(_section())
        ship = npc_spawn(0, 0, 0, "Hera", "tsn", "tsn_light_cruiser", "behav_npcship")
        item = item_get("secret_codecase")
        self.assertIsNone(item_meta("secret_codecase", "modifiers"))
        upgrade_add(ship.id, item, data={"key": "secret_codecase"}, activate=True)
        from sbs_utils.procedural.inventory import get_inventory_value
        self.assertEqual(get_inventory_value(ship.id, "sc_armed", 0), 1)


if __name__ == "__main__":
    unittest.main()
