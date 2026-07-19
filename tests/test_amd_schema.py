"""Unit tests for the declarative AMD field schema (procedural.amd_schema).

Stdlib-only module, so these run offline with no sbs mock. The load-bearing case
is the `Mode` collision (item vs map): it proves the schema MUST be archetype-keyed
and that a flat label->type map would be wrong.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.procedural import amd_schema as S


class TestArchetypeResolution(unittest.TestCase):
    def test_section_key_maps_to_archetype(self):
        self.assertEqual(S.archetype_for_section("Items"), "item")
        self.assertEqual(S.archetype_for_section("items"), "item")
        self.assertEqual(S.archetype_for_section("Item"), "item")   # trailing-s tolerant
        self.assertEqual(S.archetype_for_section("Sides"), "side")
        self.assertEqual(S.archetype_for_section("Science"), "scan")
        self.assertIsNone(S.archetype_for_section("SomeRandomSection"))
        self.assertIsNone(S.archetype_for_section(""))

    def test_infer_from_discriminating_field(self):
        self.assertEqual(S.infer_archetype(["Scan of", "Tab"]), "scan")
        self.assertEqual(S.infer_archetype(["Enemies", "Color"]), "side")
        self.assertEqual(S.infer_archetype(["Face", "Roles"]), "lifeform")
        self.assertEqual(S.infer_archetype(["At", "Kind"]), "landmark")
        self.assertEqual(S.infer_archetype(["Center", "Radius"]), "region")
        self.assertEqual(S.infer_archetype(["State", "When", "Then"]), "quest")
        self.assertEqual(S.infer_archetype(["Modifiers", "Type"]), "item")

    def test_section_key_beats_field_inference(self):
        # A record under `## Items` is an item even if it carries a field that would
        # otherwise infer differently.
        self.assertEqual(S.infer_archetype(["Color"], section_key="Items"), "item")

    def test_unknown_record_is_none(self):
        self.assertIsNone(S.infer_archetype(["Desc", "Notes"]))


class TestModeCollision(unittest.TestCase):
    """The single field-label collision that justifies archetype-keying."""
    def test_mode_is_item_enum_under_item(self):
        self.assertEqual(S.enum_values("Mode", "item"),
                         ["consumable", "install", "resource"])

    def test_mode_is_map_enum_under_map(self):
        self.assertEqual(S.enum_values("Mode", "map"),
                         ["story", "sandbox", "skirmish", "war", "campaign"])

    def test_mode_without_archetype_is_plain_text(self):
        # No archetype context -> no false enum, degrade to text (never mis-validate).
        self.assertEqual(S.field_schema("Mode")["type"], "text")
        self.assertIsNone(S.enum_values("Mode"))


class TestFieldSchema(unittest.TestCase):
    def test_typed_widgets(self):
        self.assertEqual(S.field_schema("Color", "side")["type"], "color")
        self.assertEqual(S.field_schema("Face", "lifeform")["type"], "face")
        self.assertEqual(S.field_schema("At", "landmark")["type"], "coord2")
        self.assertEqual(S.field_schema("Duration", "item")["type"], "int")

    def test_reference_fields_carry_ref_kind(self):
        self.assertEqual(S.field_schema("Parent", "quest"),
                         {"type": "ref", "ref": "node"})
        d = S.field_schema("Enemies", "side")
        self.assertEqual(d["type"], "ref")
        self.assertEqual(d["ref"], "side")
        self.assertTrue(d["csv"])

    def test_compound_when_then(self):
        when = S.field_schema("When", "quest")
        self.assertEqual(when["type"], "compound")
        self.assertIn("reach", when["verbs"])
        self.assertEqual(when["verbs"]["reach"]["type"], "coord2")
        self.assertEqual(when["verbs"]["signal"]["type"], "signal")

    def test_global_fallback_when_archetype_lacks_field(self):
        # 'Color' isn't in QUEST, but it's a type-stable GLOBAL -> still a colour.
        self.assertEqual(S.field_schema("Color", "quest")["type"], "color")

    def test_unknown_field_defaults_to_text(self):
        self.assertEqual(S.field_schema("Nonsense", "quest")["type"], "text")

    def test_descriptors_are_json_serializable(self):
        import json
        for arch, table in S.ARCHETYPES.items():
            for label, desc in table.items():
                json.dumps(desc)   # raises if any descriptor isn't JSON-able


class TestRecordAndTemplate(unittest.TestCase):
    def test_record_schema_shape(self):
        rec = S.record_schema(["Scan of", "Tab"])
        self.assertEqual(rec["archetype"], "scan")
        self.assertEqual(rec["fields"]["Tab"]["type"], "enum")
        self.assertEqual(rec["fields"]["Scan of"]["ref"], "role")

    def test_template_fields_preserve_order(self):
        fields = S.template_fields("item")
        self.assertEqual(fields[0], "type")   # authoring order from ITEM table
        self.assertIn("modifiers", fields)
        self.assertEqual(S.template_fields("nope"), [])

    def test_enum_values_only_for_closed_enums(self):
        self.assertEqual(S.enum_values("State", "quest"),
                         ["active", "secret", "idle", "complete", "failed"])
        # 'consoles' is an open enum -> suggestions, not a closed set to validate.
        self.assertIsNone(S.enum_values("Consoles", "item"))
        # a ref field is not an enum.
        self.assertIsNone(S.enum_values("Parent", "quest"))


if __name__ == "__main__":
    unittest.main()
