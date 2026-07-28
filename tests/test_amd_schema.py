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
        # `Parent:` is authored `Part of:` now; both resolve to the same descriptor,
        # and the STORED key stays `parent` so every reader is untouched.
        for label in ("Part of", "Parent"):
            d = S.field_schema(label, "quest")
            self.assertEqual(d["type"], "ref")
            self.assertEqual(d["ref"], "node")
            self.assertEqual(d["key"], "parent")
        d = S.field_schema("Enemies", "side")
        self.assertEqual(d["type"], "ref")
        self.assertEqual(d["ref"], "side")
        self.assertTrue(d["csv"])

    def test_internal_fields_parse_but_are_not_offered(self):
        import sbs_utils.procedural.amd_schema as SS
        offered = SS.template_fields("quest")
        for gone in ("fail after", "fail on signal", "fail on all dead",
                     "complete after", "on kill", "on collect", "win text", "reveal"):
            self.assertNotIn(gone, offered, gone)
            self.assertTrue(SS.amd_is_declared(gone, "quest"), gone + " must still parse")
            self.assertTrue(SS.amd_is_internal(gone, "quest"), gone)
        for kept in ("starts when", "done when", "fails when", "reward", "penalty",
                     "at start"):   # survives: see the note on the field
            self.assertIn(kept, offered, kept)

    def test_the_life_cycle_is_one_grammar(self):
        """Three questions, one trigger type - the point of the collapse. `Starts when:`
        used to be a `compound` of its own while `Done when:` was a `trigger`, which is
        exactly the kind of split an author has to memorise."""
        for label in ("Starts when", "Done when", "Fails when", "When"):
            self.assertEqual(S.field_schema(label, "quest")["type"], "trigger", label)
        self.assertEqual(S.field_schema("Then", "quest")["type"], "compound")

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
        # `At start:` (was `State:`) in words an author would use - `hidden` for a
        # record not revealed yet, `offered` for a job waiting to be accepted.
        self.assertEqual(S.enum_values("At start", "quest"),
                         ["running", "offered", "hidden", "posting",
                          "done", "failed"])
        self.assertEqual(S.enum_values("State", "quest"),
                         S.enum_values("At start", "quest"))
        # 'consoles' is an open enum -> suggestions, not a closed set to validate.
        self.assertIsNone(S.enum_values("Consoles", "item"))
        # a ref field is not an enum.
        self.assertIsNone(S.enum_values("Parent", "quest"))


class TestCoercion(unittest.TestCase):
    """The declared TYPE parses the value - replacing the per-label elif chains."""

    def test_boolean_false_is_really_false(self):
        # the bug this fixes: `Required: false` used to coerce to the STRING
        # "false", which is truthy, so a false flag read as true.
        self.assertIs(S.amd_coerce(S.boolean(), "false"), False)
        self.assertIs(S.amd_coerce(S.boolean(), "no"), False)
        self.assertIs(S.amd_coerce(S.boolean(), "true"), True)
        self.assertIs(S.amd_coerce(S.boolean(), ""), True)     # bare flag = on

    def test_author_shaped_types(self):
        self.assertEqual(S.amd_coerce(S.weighted(), "by-the-book 40, fearsome 30"),
                         {"by_the_book": 40, "fearsome": 30})
        self.assertEqual(S.amd_coerce(S.makeup(), "60% Kralien, 40% Arvonian"),
                         {"Kralien": 60, "Arvonian": 40})
        self.assertEqual(S.amd_coerce(S.counted(), "bio_sample x1, salvage x5"),
                         {"bio_sample": 1, "salvage": 5})
        self.assertEqual(S.amd_coerce(S.kv(), "kind=bio, range=medium"),
                         {"kind": "bio", "range": "medium"})
        self.assertEqual(S.amd_coerce(S.duration(), "6 minutes"), 360)
        self.assertEqual(S.amd_coerce(S.duration(), "90 seconds"), 90)
        self.assertEqual(S.amd_coerce(S.pct(), "40%"), 0.4)
        self.assertEqual(S.amd_coerce(S.coord2(), "6, 4"), [6, 4])

    def test_colour_keeps_its_hash(self):
        # 27 authored values start with '#'; raw YAML would eat them as a comment.
        self.assertEqual(S.amd_coerce(S.color(), "#07F"), "#07F")

    def test_csv_ref_is_a_list_plain_ref_is_not(self):
        self.assertEqual(S.amd_coerce(S.ref("side", csv=True), "tsn, civ"), ["tsn", "civ"])
        self.assertEqual(S.amd_coerce(S.ref("node"), "job_sweep"), "job_sweep")

    def test_enum_matches_case_insensitively_but_stores_declared_spelling(self):
        d = S.enum("active", "secret")
        self.assertEqual(S.amd_coerce(d, "Active"), "active")
        # an unknown value passes through untouched, for the linter to flag
        self.assertEqual(S.amd_coerce(d, "activ"), "activ")

    def test_unknown_type_keeps_the_historical_default(self):
        self.assertEqual(S.amd_coerce(S.text(), "  hello  "), "hello")
        self.assertEqual(S.amd_coerce({}, "30"), 30)


class TestAliasesAndRuntimeKeys(unittest.TestCase):
    """`aka` is what makes every naming decision reversible after release."""

    def test_alias_resolves_to_canonical(self):
        S.amd_register_fields("aliastest", {"done when": S.field(S.trigger(),
                                                                 key="on_signal",
                                                                 aka=("goal",))})
        # canonical labels come back NORMALISED (underscored), matching runtime keys
        self.assertEqual(S.amd_canonical_label("Goal", "aliastest"), "done_when")
        self.assertEqual(S.amd_field_key("Goal", "aliastest"), "on_signal")
        self.assertEqual(S.amd_field_key("Done when", "aliastest"), "on_signal")

    def test_label_normalisation_is_space_hyphen_underscore_tolerant(self):
        self.assertEqual(S.amd_canonical_label("Fail on signal", "quest"), "fail_on_signal")
        self.assertEqual(S.amd_canonical_label("fail_on_signal", "quest"), "fail_on_signal")
        self.assertEqual(S.amd_canonical_label("fail-on-signal", "quest"), "fail_on_signal")

    def test_read_field_returns_runtime_key_and_parsed_value(self):
        key, value = S.amd_read_field("Required", "false", "quest")
        self.assertEqual(key, "required")
        self.assertIs(value, False)


class TestRenamesStayCompatible(unittest.TestCase):
    """Every naming decision has to be reversible after release. These are the
    two mechanisms that make that true."""

    def test_a_renamed_VALUE_still_parses(self):
        # Three generations of the same value all land on the word authors write now.
        for old in ("idle", "available", "offered"):
            self.assertEqual(S.amd_coerce(S.field_schema("At start", "quest"), old),
                             "offered")
        self.assertEqual(S.amd_coerce(S.field_schema("State", "quest"), "secret"),
                         "hidden")
        self.assertEqual(S.amd_coerce(S.field_schema("State", "quest"), "active"),
                         "running")

    def test_a_retired_value_is_accepted_but_not_offered(self):
        self.assertNotIn("idle", S.enum_values("State", "quest"))   # not offered
        self.assertIn("idle", S.enum_accepts("State", "quest"))     # not flagged

    def test_a_renamed_LABEL_still_resolves(self):
        # Goal -> Done when, When -> Starts when
        self.assertEqual(S.amd_canonical_label("Goal", "quest"), "done_when")
        self.assertEqual(S.amd_canonical_label("When", "quest"), "starts_when")
        self.assertEqual(S.field_schema("Goal", "quest")["type"], "trigger")

    def test_renaming_the_authored_name_does_not_move_the_stored_key(self):
        # the rule that keeps every existing reader working through a rename
        self.assertEqual(S.amd_field_key("Goal", "quest"), "goal")
        self.assertEqual(S.amd_field_key("Done when", "quest"), "goal")
        self.assertEqual(S.amd_field_key("When", "quest"), "when")
        self.assertEqual(S.amd_field_key("Starts when", "quest"), "when")


class TestVocabularyCoverage(unittest.TestCase):
    """The busiest part of the language used to have no schema at all."""

    def test_quest_fields_are_declared(self):
        for label in ("Pays", "Goal", "Done when", "Objective", "Complete after",
                      "Fail on all dead", "On accept", "On complete", "Scope",
                      "Tier", "Citation", "Win text"):
            self.assertTrue(S.amd_is_declared(label, "quest"), f"{label} undeclared")

    def test_sections_authors_actually_write_resolve(self):
        for name, arch in (("Jobs", "quest"), ("Goals", "quest"),
                           ("Narrative", "quest"), ("Contracts", "quest"),
                           ("Dialogue", "dialogue"), ("Scenario", "map")):
            self.assertEqual(S.archetype_for_section(name), arch, name)

    def test_a_flat_record_is_classified_by_its_fields(self):
        # the 1444 a2x records that sit directly under the document root have no
        # section to be named by
        self.assertEqual(S.infer_archetype(["Goal", "Pays"]), "quest")
        self.assertEqual(S.infer_archetype(["Complete after"]), "quest")


class TestExtensionRegistry(unittest.TestCase):
    """A mission adds vocabulary and gets typing + lint + widgets for it."""

    def test_register_then_resolve(self):
        S.amd_register_fields("clan", {"Values": S.weighted(), "Flies": S.makeup()},
                              domain="universe")
        self.assertEqual(S.field_schema("Values", "clan")["type"], "weighted")
        self.assertIn("values", S.template_fields("clan"))

    def test_identical_reregistration_is_a_noop(self):
        S.amd_register_fields("clan2", {"Values": S.weighted()})
        S.amd_register_fields("clan2", {"Values": S.weighted()})   # must not raise

    def test_collision_with_a_global_field_raises_loudly(self):
        with self.assertRaises(ValueError) as ctx:
            S.amd_register_fields("clan3", {"Color": S.text()}, domain="rogue")
        self.assertIn("already declared", str(ctx.exception))

    def test_section_name_table_is_extensible(self):
        S.amd_register_section_names(("contracts", "bounties"), "quest", domain="universe")
        self.assertEqual(S.archetype_for_section("Contracts"), "quest")
        self.assertEqual(S.archetype_for_section("Bounties"), "quest")

    def test_conflicting_section_name_raises(self):
        with self.assertRaises(ValueError):
            S.amd_register_section_names(("items",), "quest")


if __name__ == "__main__":
    unittest.main()
