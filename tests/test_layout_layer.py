"""The `layer:` style key and the draw_layer plumbing (GUI_LAYER_CLIP_PLAN.md Phase B).

The engine has no clip, so text that overruns its rect is drawn over its neighbours.
Paint order plus an opaque fill is the only way to hide a spill that has already
happened -- ENGINE-VERIFIED (VisualTestRange `--map visual_draw_layer`): a fill at a
higher draw_layer hides the overflow, one at a lower layer does not, and on a tie the
text wins even though the image was emitted later.

Before this, a scripter could not reach that: row/column/section backgrounds were
pinned to a hardcoded `draw_layer:1000` (UNDER content, so a backdrop could never cover
a neighbour's spill), and `gui_image` DROPPED draw_layer entirely because
`ImageAtlas.get_props` rebuilt the props string from file/color/sub_rect.

These are emitted-stream tests: they assert the props string that reaches send_gui_*,
which is the exact string the engine receives.
"""
import types
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.helpers import FrameContext
from sbs_utils.vec import Vec3
from sbs_utils.pages.layout.measure import BACKDROP_LAYER, backdrop_props
from sbs_utils.pages.layout.column import Column
from sbs_utils.pages.layout.row import Row
from sbs_utils.mast.parsers import StyleDefinition


class TestBackdropProps(unittest.TestCase):
    def test_default_is_the_historic_1000(self):
        # The whole back-compat promise: a layout that never says `layer:` emits
        # exactly the string it always did.
        self.assertEqual(backdrop_props("smallWhite", "#123"),
                         "image:smallWhite; color:#123;draw_layer:1000;")
        self.assertEqual(BACKDROP_LAYER, 1000)

    def test_explicit_layer_replaces_it(self):
        self.assertIn("draw_layer:2000;", backdrop_props("smallWhite", "#123", 2000))
        self.assertNotIn("draw_layer:1000", backdrop_props("smallWhite", "#123", 2000))

    def test_zero_is_a_layer_not_a_missing_one(self):
        # 0 is falsy: a `layer: 0` must not silently become the 1000 default.
        self.assertIn("draw_layer:0;", backdrop_props("smallWhite", "#123", 0))


class TestCascadeProps(unittest.TestCase):
    def setUp(self):
        self.col = Column()

    def test_silent_when_no_layer_set(self):
        self.assertEqual(self.col.get_cascade_props(layer=True), "")

    def test_emits_when_set(self):
        self.col.layer = 1500
        self.assertEqual(self.col.get_cascade_props(layer=True), "draw_layer:1500;")

    def test_not_emitted_unless_asked(self):
        # Callers that fold the cascade into something other than an engine props
        # string (the text area's per-line `$$` style) must not receive it.
        self.col.layer = 1500
        self.assertNotIn("draw_layer", self.col.get_cascade_props(True, True, True))

    def test_author_draw_layer_in_the_message_wins(self):
        # Two draw_layer keys in one props string is undefined; the nearer
        # declaration is the one they meant. Same rule button.py already used.
        self.col.layer = 1500
        props = self.col.get_cascade_props(layer=True, message="$text:`x`;draw_layer:9;")
        self.assertNotIn("draw_layer", props)

    def test_own_layer_beats_the_inherited_default(self):
        self.col.default_layer = 1200
        self.assertEqual(self.col.get_layer(), 1200)
        self.col.layer = 1500
        self.assertEqual(self.col.get_layer(), 1500)


class TestRowAliasesLikeColorDoes(unittest.TestCase):
    def test_layer_property_writes_the_default(self):
        # Row/Layout expose cascading props as `x` aliasing `default_x`; layer
        # has to follow that or a style set on a row would not cascade.
        row = Row()
        self.assertIsNone(row.get_layer())
        row.layer = 2500
        self.assertEqual(row.default_layer, 2500)
        self.assertEqual(row.get_layer(), 2500)


class _FakeTask:
    """apply_control_styles needs `format_string` (a plain str passes through it
    unchanged in the real scheduler too) and `main.page.client_id`, which it uses to
    look up the aspect ratio for the em/px units in the same style string."""
    def __init__(self):
        self.main = types.SimpleNamespace(page=types.SimpleNamespace(client_id=0))

    def format_string(self, message):
        return message


class TestStyleStringToEmittedProps(unittest.TestCase):
    """The whole chain: authored style string -> the props the engine receives.

    Each link has its own test above; this is the one that fails if they stop being
    connected -- which is how `layer:` could have looked implemented while silently
    doing nothing.
    """
    def setUp(self):
        FrameContext.aspect_ratios[0] = Vec3(1000, 1000, 0)

    def _row(self, style):
        from sbs_utils.procedural.style import apply_control_styles
        row = Row()
        apply_control_styles(".row", style, row, _FakeTask())
        return row

    def test_row_background_carries_an_authored_layer(self):
        row = self._row("row-height: 6em; background: #123456; layer: 1500;")
        self.assertEqual(row.get_layer(), 1500)
        props = backdrop_props(row.background_image, row.background_color, row.get_layer())
        self.assertIn("draw_layer:1500;", props)
        # The colour keeps the leading space the style string gave it -- long-standing
        # behaviour that the engine's props parser tolerates, asserted so a future
        # strip() here is a deliberate change rather than an accident.
        self.assertIn("color: #123456", props)

    def test_row_without_a_layer_is_untouched(self):
        # Back-compat: every existing background must still emit the historic 1000.
        row = self._row("row-height: 6em; background: #123456;")
        self.assertIsNone(row.get_layer())
        props = backdrop_props(row.background_image, row.background_color, row.get_layer())
        self.assertIn("draw_layer:1000;", props)

    def test_junk_layer_is_ignored_not_fatal(self):
        row = self._row("background: #123456; layer: bananas;")
        self.assertIsNone(row.get_layer())


class TestImageAtlasProps(unittest.TestCase):
    """ImageAtlas used to DROP draw_layer -- get_props rebuilt the string from
    file/color/sub_rect -- so the one widget that can paint an opaque rectangle was
    the one that could not be raised."""

    def _atlas(self):
        from sbs_utils.procedural.gui.image import ImageAtlas
        atlas = ImageAtlas.__new__(ImageAtlas)     # bypass file resolution
        atlas.file = "smallWhite"
        atlas.left = atlas.top = atlas.right = atlas.bottom = None
        atlas.color = "#123"
        atlas.draw_layer = None
        return atlas

    def test_no_layer_is_byte_identical_to_the_historic_string(self):
        # The back-compat claim at the level of the emitted string, not just of
        # what it renders -- this branch never carried a trailing semicolon.
        self.assertEqual(self._atlas().get_props(), "image:smallWhite;color:#123")

    def test_registered_layer_is_emitted(self):
        atlas = self._atlas()
        atlas.draw_layer = "1500"
        self.assertEqual(atlas.get_props(), "image:smallWhite;color:#123;draw_layer:1500;")

    def test_per_use_layer_beats_the_registration(self):
        # Same rule `color` already follows: one registered cell serves every use.
        atlas = self._atlas()
        atlas.draw_layer = "1500"
        self.assertIn("draw_layer:2500;", atlas.get_props(layer=2500))


class TestStyleParsing(unittest.TestCase):
    def test_layer_survives_the_style_parser(self):
        parsed = StyleDefinition.parse("layer: 2000;")
        self.assertEqual(str(parsed.get("layer")).strip(), "2000")

    def test_unknown_keys_are_still_dropped(self):
        # Guards the case list itself: `layer` is recognised because it was
        # added, not because the parser passes everything through.
        self.assertIsNone(StyleDefinition.parse("not-a-real-key: 2000;").get("not-a-real-key"))


if __name__ == "__main__":
    unittest.main()
