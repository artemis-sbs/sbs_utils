"""The `layer:` style key and the draw_layer plumbing (DESIGN_RECORD.md s6).

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


class _Rec:
    """Records the props string every send_gui_* receives."""
    def __init__(self):
        self.calls = []

    def _grab(self, kind):
        def f(client_id, region_tag, tag, props, *rect):
            self.calls.append((kind, props))
        return f

    def __getattr__(self, name):
        if name.startswith("send_gui_"):
            return self._grab(name)
        raise AttributeError(name)

    def props(self, kind=None):
        return [p for k, p in self.calls if kind is None or k == kind]


class TestMarkdownSegmentsCarryTheLayer(unittest.TestCase):
    """The RICH text_area path builds its own props per segment, so unlike
    `_present_simple` it does not get the cascade for free. Without this a markdown text
    area inside a RAISED container -- an overlay panel with an opaque backdrop above it --
    rendered underneath that backdrop and vanished.

    The cascade still must not reach the `$$` per-line mini-language: that is a style
    string the text area parses itself, not one the engine reads.
    """

    def _ar(self):
        return types.SimpleNamespace(x=1920.0, y=1080.0)

    def test_layer_prop_is_silent_when_unraised(self):
        from sbs_utils.pages.layout.text_area import _layer_prop
        self.assertEqual(_layer_prop(None), "")

    def test_layer_prop_emits_when_raised(self):
        from sbs_utils.pages.layout.text_area import _layer_prop
        self.assertEqual(_layer_prop(30000), "draw_layer:30000;")

    def test_layer_prop_zero_is_a_layer_not_a_missing_one(self):
        from sbs_utils.pages.layout.text_area import _layer_prop
        self.assertEqual(_layer_prop(0), "draw_layer:0;")

    def test_ship_segment_carries_it(self):
        from sbs_utils.pages.layout.text_area import ShipLine
        seg = ShipLine.__new__(ShipLine)
        seg.text, seg.align, seg.width = "tsn_scout", "left", 10.0
        rec = _Rec()
        seg.send_gui(rec, 1, "r", "t", 0.0, 0.0, 100.0, 100.0, 22000)
        self.assertIn("draw_layer:22000;", rec.props("send_gui_3dship")[0])

    def test_ship_segment_unraised_is_untouched(self):
        from sbs_utils.pages.layout.text_area import ShipLine
        seg = ShipLine.__new__(ShipLine)
        seg.text, seg.align, seg.width = "tsn_scout", "left", 10.0
        rec = _Rec()
        seg.send_gui(rec, 1, "r", "t", 0.0, 0.0, 100.0, 100.0)
        self.assertEqual(rec.props("send_gui_3dship")[0], "hull_tag:tsn_scout;")

    def test_hr_rides_the_container_layer(self):
        from sbs_utils.pages.layout.text_area import HrLine
        seg = HrLine(self._ar())
        rec = _Rec()
        seg.send_gui(rec, 1, "r", "t", 0.0, 0.0, 100.0, 100.0, 30000)
        self.assertIn("draw_layer:30000;", rec.props("send_gui_image")[0])

    def test_hr_unraised_keeps_the_historic_1000(self):
        from sbs_utils.pages.layout.text_area import HrLine
        seg = HrLine(self._ar())
        rec = _Rec()
        seg.send_gui(rec, 1, "r", "t", 0.0, 0.0, 100.0, 100.0)
        self.assertIn("draw_layer:1000;", rec.props("send_gui_image")[0])

    def test_link_raises_its_hit_area_with_its_text(self):
        # If only the text rose, the clickregion would sit behind the backdrop and the
        # link would look live while being unclickable.
        from sbs_utils.pages.layout.text_area import LinkLine
        seg = LinkLine.__new__(LinkLine)
        seg.display, seg.click_tag, seg.font = "Go", "k", "gui-2"
        rec = _Rec()
        seg.send_gui(rec, 1, "r", "t", 0.0, 0.0, 100.0, 100.0, 26000)
        self.assertIn("draw_layer:26000;", rec.props("send_gui_text")[0])
        self.assertIn("draw_layer:26000;", rec.props("send_gui_clickregion")[0])

    def test_a_face_accepts_a_layer_and_cannot_use_it(self):
        # NOT an oversight: `send_gui_face` takes the face string where every other
        # widget takes a style, so there is nowhere to put a draw_layer. It is the only
        # drawable send_gui_* without a style parameter. Asserted so the day the engine
        # grows one, this test fails and tells someone to wire it up.
        import inspect
        from sbs_utils.pages.layout.text_area import FaceLine
        seg = FaceLine.__new__(FaceLine)
        seg.text, seg.align, seg.width = "tng1 #fff 1 1;", "left", 10.0

        recorded = []
        sbs = types.SimpleNamespace(
            send_gui_face=lambda *a: recorded.append(a))
        seg.send_gui(sbs, 1, "r", "t", 0.0, 0.0, 100.0, 100.0, 30000)
        self.assertEqual(len(recorded), 1)
        self.assertNotIn("draw_layer", str(recorded[0]))
        # and the signature still accepts one, so the call site stays uniform
        self.assertIn("layer", inspect.signature(FaceLine.send_gui).parameters)


class TestUntaggedBackdropDoesNotCrash(unittest.TestCase):
    """A layout item that never took a tag - `gui_blank` as a spacer, a bare section -
    has `tag is None`, and the backdrop path concatenated it: `"__bg:" + None`.

    It could only fire the first time someone gave such an item a BACKGROUND, which
    nobody had until an opaque gutter was needed beside a face (a face cannot be layered,
    so the fill has to go around it). It took the whole page down from Gui.present:

        File ".../pages/layout/column.py", line 327, in _pre_present
            "__bg:"+self.tag, props,
        TypeError: can only concatenate str (not "NoneType") to str
    """

    def test_tagged_item_is_unchanged(self):
        from sbs_utils.pages.layout.measure import backdrop_tag
        item = types.SimpleNamespace(tag="mine")
        self.assertEqual(backdrop_tag(item), "mine")

    def test_untagged_item_gets_one(self):
        from sbs_utils.pages.layout.measure import backdrop_tag
        item = types.SimpleNamespace(tag=None)
        got = backdrop_tag(item)
        self.assertTrue(got.startswith("__anon"))
        self.assertIsInstance("__bg:" + got, str)   # the concatenation that used to raise

    def test_the_minted_tag_is_stable_across_presents(self):
        # The engine addresses widgets by tag: a value that changed per frame would emit
        # a NEW widget every present instead of updating the one already there.
        from sbs_utils.pages.layout.measure import backdrop_tag
        item = types.SimpleNamespace(tag=None)
        self.assertEqual(backdrop_tag(item), backdrop_tag(item))

    def test_two_untagged_items_do_not_collide(self):
        from sbs_utils.pages.layout.measure import backdrop_tag
        a = types.SimpleNamespace(tag=None)
        b = types.SimpleNamespace(tag=None)
        self.assertNotEqual(backdrop_tag(a), backdrop_tag(b))

    def test_a_blank_with_a_background_presents(self):
        # The actual reported crash, end to end through Column._pre_present.
        from sbs_utils.pages.layout.blank import Blank
        from sbs_utils.pages.layout.bounds import Bounds
        col = Blank()
        col.tag = None
        col.background_color = "#000"
        col.bounds = Bounds(0.0, 0.0, 10.0, 10.0)
        sent = []
        ctx = FrameContext.context
        FrameContext.context = types.SimpleNamespace(
            sbs=types.SimpleNamespace(
                send_gui_image=lambda *a: sent.append(a[2])))
        try:
            col._pre_present(types.SimpleNamespace(client_id=1))
        finally:
            FrameContext.context = ctx
        self.assertEqual(len(sent), 1)
        self.assertTrue(sent[0].startswith("__bg:__anon"))
