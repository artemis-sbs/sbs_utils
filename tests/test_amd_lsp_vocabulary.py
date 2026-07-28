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


if __name__ == "__main__":
    unittest.main()
