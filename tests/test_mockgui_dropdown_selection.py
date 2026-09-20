"""The browser mock's dropdown has to honor `text:` as the CURRENT SELECTION.

A `<select>` that is never told which option is selected shows its FIRST one. That broke
two things at once in the mock, and the second is why it survived so long unnoticed:

  * after any repaint the box displayed option 0 while the script held something else;
  * and because it displayed option 0, PICKING option 0 was not a change - so the browser
    fired no `change` event at all and the script never heard the choice.

On the avatar editor that read as "selecting Arvonian gives you Terran properties, and
selecting Terran leaves the box saying Arvonian".

It hid for so long because every other dropdown in the tree happens to start on its first
option - `$text:{sides[0]}`, `crew_choice or 'auto'` against `list: auto,...` - so the
accidental display was correct and every pick was a real change. The avatar editor's race
picker is the only one whose initial `text:` (Terran) is not first in its list
(Arvonian, Kralien, Skaraan, Terran, ...).

**The engine honors `text:`**, so this was mock-only. A mock that behaves differently
from the engine makes a real bug and its absence indistinguishable, which is why the
divergence gets fixed rather than worked around in the mission.

This test is STATIC - it reads client.html, because the renderer is browser JavaScript and
there is no JS harness here. It checks the seam rather than the behavior, so it is worth
exactly as much as that: it catches the line being deleted, not a new way to break it.

    python -m unittest tests.test_mockgui_dropdown_selection
"""
import os
import re
import unittest

from sbs_utils.fs import test_set_exe_dir

test_set_exe_dir()

FACE_JS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "cosmos_dev", "mockgui", "face.js")

CLIENT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "cosmos_dev", "mockgui", "client.html")


def _dropdown_case():
    with open(CLIENT, encoding="utf-8") as f:
        src = f.read()
    start = src.index("case 'dropdown': {")
    end = src.index("case 'face': {", start)
    return src[start:end]


class TestDropdownHonorsItsSelection(unittest.TestCase):
    def setUp(self):
        self.case = _dropdown_case()

    def test_the_renderer_applies_the_text_property_to_the_select(self):
        self.assertIn("sel.value", self.case,
                      "the dropdown never sets sel.value, so it will show option 0 "
                      "whatever `text:` says")
        self.assertIn("s.text", self.case,
                      "the selection has to come from the `text:` property")

    def test_it_matches_against_the_option_values(self):
        """Assigning an unknown string to `sel.value` silently selects nothing and the
        box goes blank, so the wanted value is looked up in the options first."""
        self.assertRegex(self.case, r"sel\.options",
                         "the wanted value is not checked against the option list")

    def test_it_still_reports_changes(self):
        # The fix must not cost the change event - that is the half that made the bug
        # invisible rather than merely wrong.
        self.assertRegex(self.case, r"addEventListener\(\s*'change'")
        self.assertIn("value: sel.value", self.case)

    def test_the_text_is_unquoted_before_matching(self):
        """Cosmos stores widget text backtick-quoted (``$text:`Terran```). Matching the
        raw string against an option value would never hit."""
        self.assertIn("ctext(s.text)", self.case,
                      "the text must go through ctext() to lose its backticks")


class TestTheLibrarySendsTheSelection(unittest.TestCase):
    """The other half: whatever the browser does, the library has to put the current
    selection in `text:` for it to honor. This part is real, not static."""

    def test_setting_a_dropdown_value_writes_it_into_the_props(self):
        from sbs_utils.pages.layout.dropdown import Dropdown

        dd = Dropdown("t1", "text:Terran;list: Arvonian, Kralien, Terran")
        self.assertEqual(dd.value, "Terran")
        dd.value = "Kralien"
        self.assertEqual(dd.value, "Kralien")
        self.assertIn("Kralien", dd.values)
        # The list has to survive the selection write, or the box empties.
        for option in ("Arvonian", "Kralien", "Terran"):
            self.assertIn(option, dd.values)

    def test_a_selection_that_is_not_first_survives(self):
        """The exact shape that exposed the mock bug: a dropdown whose current value is
        not option 0."""
        from sbs_utils.helpers import props_display_text
        from sbs_utils.pages.layout.dropdown import Dropdown

        dd = Dropdown("t1", "text:Terran;list: Arvonian, Kralien, Skaraan, Terran")
        self.assertEqual(props_display_text(dd.values), "Terran")


class TestFaceTintIsAlphaCorrect(unittest.TestCase):
    """The browser compositor must tint PER PIXEL, not with a canvas blend mode.

    Canvas 2D stores color premultiplied, and its `multiply` blend computes
    Cs*Cd + Cs*(1-ad). Tinting with an opaque fillRect therefore leaves that second term
    wherever the sprite is partially transparent, and the pixel drifts toward the tint at
    full strength: exact at full coverage, +0.30 at half, +0.90 at a quarter (tint 0.30
    over color 0.55). Every antialiased edge got a tint-colored halo, worst on the eye
    and mouth cells - small features feathered into the face, so mostly soft pixels.

    getImageData/putImageData are defined on STRAIGHT alpha, so a plain channel multiply
    there is exactly what the engine does. PIL takes the same straight-alpha path in
    sbs_cli's face_bake, which is why only the browser ever showed this.
    """

    def setUp(self):
        with open(FACE_JS, encoding="utf-8") as f:
            src = f.read()
        start = src.index("function drawLayer")
        end = src.index("\n  function ", start + 10)
        self.fn = src[start:end]
        # CODE only. The comment above the fix names the old technique on purpose, and a
        # test that cannot tell an explanation from an instruction would forbid writing
        # down why the change was made.
        self.code = "\n".join(re.sub(r"//.*$", "", ln) for ln in self.fn.split("\n"))

    def test_it_multiplies_per_pixel(self):
        self.assertIn("getImageData", self.code)
        self.assertIn("putImageData", self.code)

    def test_it_does_not_use_the_canvas_multiply_blend(self):
        self.assertNotIn("'multiply'", self.code,
                         "the canvas multiply blend is not alpha-correct here")

    def test_it_leaves_alpha_untouched(self):
        # Only channels 0-2 are scaled; d[i+3] must not be written, or the sprite's own
        # coverage is destroyed and the halo comes back by another route.
        # An ASSIGNMENT to the alpha channel. `=` not followed by `=`, so the guard
        # `if (d[i + 3] === 0) continue;` - a comparison - does not trip it.
        self.assertNotRegex(self.code, r"d\[i \+ 3\]\s*=(?!=)")

    def test_the_untinted_path_stays_a_straight_blit(self):
        # A white tint must not pay for a per-pixel pass - most layers are untinted.
        self.assertIn("isWhite", self.code)


class TestVendoredFaceJsIsInSync(unittest.TestCase):
    """The VS Code extension carries a verbatim copy. Nothing but this notices a drift."""

    def test_the_two_copies_match(self):
        vendored = os.path.normpath(os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "sbs_cli", "editors", "vscode", "media", "face.js"))
        if not os.path.exists(vendored):
            self.skipTest("sbs_cli checkout not present")
        with open(FACE_JS, encoding="utf-8") as f:
            canonical = f.read()
        with open(vendored, encoding="utf-8") as f:
            copy = f.read()
        self.assertEqual(canonical, copy,
                         "cosmos_dev/mockgui/face.js and the vendored copy have drifted")


if __name__ == "__main__":
    unittest.main()
