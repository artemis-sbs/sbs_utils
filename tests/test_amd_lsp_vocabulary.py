"""The editor learns a mission's OWN vocabulary by READING its Python, never running
it (sbs_utils.procedural.amd_lsp._learn_mission_vocabulary).

    python -m unittest tests.test_amd_lsp_vocabulary
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.procedural import amd_lsp as L
from sbs_utils.procedural import amd_schema as S

SRC = chr(10).join([
    "from sbs_utils.procedural.amd_schema import (amd_register_fields,",
    "    amd_register_section_names, text, enum, coord2, pct, field)",
    "",
    "def declare():",
    "    amd_register_fields('patron', {",
    "        'call sign': text(hint='what the room calls them'),",
    "        'face kind': enum('torgoth male', 'terran male', open=True),",
    "        'reliability': pct(),",
    "        'seat': coord2(),",
    "    }, domain='casino')",
    "    amd_register_section_names(('patrons', 'bar'), 'patron', domain='casino')",
    "",
])


class LearnsWithoutRunning(unittest.TestCase):
    """A mission extends the schema at runtime, but the editor never imports mission
    code - so OU's clan/captain/worldlet labels and LM's recipes were untyped in the
    Inspector, unlinted, and showed no type at all in the kind picker."""

    def setUp(self):
        L._learn_mission_vocabulary([SRC])

    def test_the_section_name_now_resolves(self):
        self.assertEqual(S.archetype_for_section("patrons"), "patron")
        self.assertEqual(S.archetype_for_section("bar"), "patron")

    def test_fields_keep_their_declared_TYPE(self):
        self.assertEqual(S.field_schema("reliability", "patron")["type"], "pct")
        self.assertEqual(S.field_schema("seat", "patron")["type"], "coord2")
        self.assertEqual(S.field_schema("call sign", "patron")["type"], "text")

    def test_an_enum_keeps_its_values(self):
        d = S.field_schema("face kind", "patron")
        self.assertEqual(d["type"], "enum")
        self.assertIn("terran male", d["values"])
        self.assertTrue(d.get("open"))

    def test_the_new_archetype_is_offered_a_starter_set(self):
        self.assertTrue(S.starter_fields("patron"))

    def test_nothing_is_EXECUTED(self):
        """The declaration is read out of the syntax tree, so a module that would blow
        up on import (no engine here) still teaches the editor its vocabulary."""
        src = chr(10).join([
            "import sbs                      # would fail outside Cosmos",
            "raise SystemExit('never runs')",
            "from sbs_utils.procedural.amd_schema import amd_register_section_names",
            "amd_register_section_names(('rumors',), 'dialogue')",
        ])
        L._learn_mission_vocabulary([src])
        self.assertEqual(S.archetype_for_section("rumors"), "dialogue")

    def test_a_dynamic_declaration_is_skipped_not_guessed(self):
        src = chr(10).join([
            "from sbs_utils.procedural.amd_schema import amd_register_section_names",
            "amd_register_section_names(NAMES, whatever())",
        ])
        L._learn_mission_vocabulary([src])          # must not raise
        self.assertIsNone(S.archetype_for_section("whatever"))

    def test_bad_syntax_is_survivable(self):
        L._learn_mission_vocabulary(["amd_register_fields('x', {"])   # must not raise


class EveryFieldTypeIsReadable(unittest.TestCase):
    """The editor reads a declaration only when it knows the constructor's name.

    `named_hulls` was added to the schema and not to that list, so the ONE table using it -
    LegendaryMissions' boss fields - was dropped whole, and VS Code underlined `Trigger:`,
    `Low:`, `Flies:`, `Fleets:`, `Difficulty:` and `Named:` in every shipped boss file."""

    def test_no_constructor_is_missing_from_the_list(self):
        import inspect
        made = set()
        for name, fn in vars(S).items():
            if name.startswith("_") or not inspect.isfunction(fn):
                continue
            if fn.__module__ != S.__name__:
                continue
            try:
                source = inspect.getsource(fn)
            except OSError:
                continue
            if "return _d(" in source:
                made.add(name)
        self.assertTrue(made, "found no field constructors - has amd_schema moved?")
        self.assertEqual(sorted(made - set(L._DESCRIPTOR_FNS)), [])

    def test_a_table_with_named_hulls_is_learned(self):
        src = chr(10).join([
            "amd_register_fields('ship_list', {",
            "    'named': named_hulls(hint='Ragnarok tsn_juggernaut'),",
            "    'fleets': integer(),",
            "})",
        ])
        L._learn_mission_vocabulary([src])
        self.assertEqual(S.field_schema("fleets", "ship_list")["type"], "int")
        self.assertTrue(S.amd_is_declared("named", "ship_list"))

    def test_one_unreadable_field_does_not_cost_the_table(self):
        src = chr(10).join([
            "amd_register_fields('ship_note', {",
            "    'odd': a_type_from_the_future(),",
            "    'plain': text(),",
            "})",
        ])
        L._learn_mission_vocabulary([src])
        self.assertTrue(S.amd_is_declared("plain", "ship_note"))
        self.assertFalse(S.amd_is_declared("odd", "ship_note"))


if __name__ == "__main__":
    unittest.main()
