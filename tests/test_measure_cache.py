import types
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.helpers import FrameContext
from sbs_utils.vec import Vec3

# procedural.gui must be imported before pages.layout to avoid a circular
# import through pages.layout.blank
import sbs_utils.procedural.gui  # noqa: F401
from sbs_utils.pages.layout import measure


class CountingSbs:
    """Counts engine text-metric calls so cache hits can be asserted."""

    def __init__(self):
        self.line_w_calls = 0
        self.line_h_calls = 0
        self.block_h_calls = 0

    def get_text_line_width(self, font, text):
        self.line_w_calls += 1
        return len(text) * 10

    def get_text_line_height(self, font, text):
        self.line_h_calls += 1
        return 20

    def get_text_block_height(self, font, text, px_width):
        self.block_h_calls += 1
        return 20 * (1 + (len(text) * 10) // max(1, px_width))


class FakeEvent:
    client_id = 0


class TestMeasureCache(unittest.TestCase):
    def setUp(self):
        FrameContext.aspect_ratios[0] = Vec3(1024, 768, 0)
        self.sbs = CountingSbs()
        FrameContext.context = types.SimpleNamespace(
            sbs=self.sbs, sim=None, event=FakeEvent())
        measure.measure_cache_clear()

    def tearDown(self):
        FrameContext.context = None
        measure.measure_cache_clear()

    def test_repeated_measure_hits_engine_once(self):
        for _ in range(20):
            self.assertEqual(measure.measure_line_width("gui-2", "Hello"), 50)
        self.assertEqual(self.sbs.line_w_calls, 1)

    def test_distinct_keys_each_hit_engine(self):
        measure.measure_line_width("gui-2", "Hello")
        measure.measure_line_width("gui-3", "Hello")   # different font
        measure.measure_line_width("gui-2", "World")   # different text
        self.assertEqual(self.sbs.line_w_calls, 3)

    def test_line_height_is_keyed_by_text_not_just_font(self):
        # The mock ignores the text argument, but the engine may not. Encoding
        # the mock's behaviour here would bake a mock assumption into the lib.
        measure.measure_line_height("gui-2", "short")
        measure.measure_line_height("gui-2", "a much longer string")
        self.assertEqual(self.sbs.line_h_calls, 2)
        measure.measure_line_height("gui-2", "short")
        self.assertEqual(self.sbs.line_h_calls, 2)

    def test_block_height_keyed_by_width(self):
        measure.measure_block_height("gui-2", "some words here", 100)
        measure.measure_block_height("gui-2", "some words here", 100)
        self.assertEqual(self.sbs.block_h_calls, 1)
        measure.measure_block_height("gui-2", "some words here", 200)
        self.assertEqual(self.sbs.block_h_calls, 2)

    def test_empty_text_never_calls_engine(self):
        self.assertEqual(measure.measure_line_width("gui-2", ""), 0)
        self.assertEqual(measure.measure_block_height("gui-2", "", 100), 0)
        self.assertEqual(self.sbs.line_w_calls, 0)
        self.assertEqual(self.sbs.block_h_calls, 0)

    def test_nonpositive_block_width_is_unmeasurable(self):
        self.assertIsNone(measure.measure_block_height("gui-2", "text", 0))
        self.assertEqual(self.sbs.block_h_calls, 0)

    def test_min_word_width_is_widest_token(self):
        # "min-content": the widest unbreakable token, not the whole string.
        self.assertEqual(measure.measure_min_word_width("gui-2", "a bb cccc d"), 40)

    def test_min_word_width_empty(self):
        self.assertEqual(measure.measure_min_word_width("gui-2", ""), 0)

    def test_no_context_is_unmeasurable_not_invented(self):
        # No frame context means we cannot ask the engine. Return None so the
        # caller falls back to flex -- never fabricate a number.
        FrameContext.context = None
        measure.measure_cache_clear()
        self.assertIsNone(measure.measure_line_width("gui-2", "Hello"))
        self.assertIsNone(measure.measure_line_height("gui-2", "Hello"))
        self.assertIsNone(measure.measure_block_height("gui-2", "Hello", 100))
        self.assertIsNone(measure.measure_min_word_width("gui-2", "Hello"))

    def test_cache_clear_resets(self):
        measure.measure_line_width("gui-2", "Hello")
        measure.measure_cache_clear()
        measure.measure_line_width("gui-2", "Hello")
        self.assertEqual(self.sbs.line_w_calls, 2)
        self.assertEqual(measure.measure_cache_stats()["engine_calls"], 1)

    def test_cache_cap_clears_on_overflow(self):
        for i in range(measure.CACHE_CAP + 10):
            measure.measure_line_width("gui-2", f"s{i}")
        self.assertLessEqual(len(measure._line_w), measure.CACHE_CAP)

    def test_stats_track_hits_and_engine_calls(self):
        measure.measure_line_width("gui-2", "Hello")
        measure.measure_line_width("gui-2", "Hello")
        stats = measure.measure_cache_stats()
        self.assertEqual(stats["line_w"], 1)
        self.assertEqual(stats["hits"], 1)
        self.assertEqual(stats["engine_calls"], 1)

    def test_px_percent_conversion_round_trips(self):
        ar = Vec3(1024, 768, 0)
        self.assertAlmostEqual(measure.px_to_pct_x(512, ar), 50.0)
        self.assertAlmostEqual(measure.px_to_pct_y(384, ar), 50.0)
        self.assertAlmostEqual(measure.pct_to_px_x(50.0, ar), 512.0)

    def test_conversion_guards_none_and_zero(self):
        self.assertIsNone(measure.px_to_pct_x(None, Vec3(1024, 768, 0)))
        self.assertIsNone(measure.px_to_pct_x(100, Vec3(0, 768, 0)))



class StrictSbs:
    """Mimics the ENGINE's Pybind signature: fontTag must be a str.

    The real get_text_line_width is typed (fontTag: str, textToMeasure: str)
    and raises TypeError on None. The normal mock accepts None via
    .get(fontTag, default), which is why a None font reached the engine and
    crashed LegendaryMissions without any headless test noticing.
    """

    def _check(self, font):
        if not isinstance(font, str):
            raise TypeError(
                "get_text_line_width(): incompatible function arguments. "
                f"Invoked with: {font!r}")

    def get_text_line_width(self, font, text):
        self._check(font)
        return len(text) * 10

    def get_text_line_height(self, font, text):
        self._check(font)
        return 20

    def get_text_block_height(self, font, text, px_width):
        self._check(font)
        return 20


class TestFontIsAlwaysAStringForTheEngine(unittest.TestCase):
    """Regression for the LM crash: no metric call may pass a non-str font."""

    def setUp(self):
        FrameContext.aspect_ratios[0] = Vec3(1024, 768, 0)
        FrameContext.context = types.SimpleNamespace(
            sbs=StrictSbs(), sim=None, event=FakeEvent())
        measure.measure_cache_clear()

    def tearDown(self):
        FrameContext.context = None
        measure.measure_cache_clear()

    def test_none_font_line_width(self):
        self.assertEqual(measure.measure_line_width(None, "Hello"), 50)

    def test_none_font_line_height(self):
        self.assertEqual(measure.measure_line_height(None, "Hello"), 20)

    def test_none_font_block_height(self):
        self.assertEqual(measure.measure_block_height(None, "Hello", 100), 20)

    def test_none_font_min_word(self):
        self.assertEqual(measure.measure_min_word_width(None, "a bbbb c"), 40)

    def test_empty_font_falls_back(self):
        self.assertEqual(measure.measure_line_width("", "Hello"), 50)

    def test_measure_props_with_no_font_anywhere(self):
        # The exact LM shape: a label with neither a font: prop nor a cascade.
        from sbs_utils.mast.parsers import CONTENT
        got = measure.measure_props("$text:`Select a mission. 8 types.`;",
                                    CONTENT, None, None, Vec3(1024, 768, 0))
        self.assertIsNotNone(got)

    def test_declared_font_is_still_honoured(self):
        measure.measure_line_width("gui-5", "Hello")
        self.assertIn(("gui-5", "Hello"), measure._line_w)


class EngineLikeSbs:
    """Behaves like the ENGINE, not like the mock.

    Two behaviours the normal mock does not have, both of which caused real
    invisible-text bugs in Cosmos:

      * fontTag must be a str (Pybind rejects None)
      * an UNRECOGNISED tag does not raise -- it returns -1

    The mock instead falls back to a gui-3 bucket for anything unknown and
    returns a positive number, so a malformed font tag looked fine headlessly
    and drew nothing in the game.
    """

    KNOWN = {"smallest", "gui-1", "gui-2", "gui-3", "gui-4", "gui-5", "gui-6"}

    def _w(self, font, text):
        if not isinstance(font, str):
            raise TypeError("incompatible function arguments")
        if font not in self.KNOWN:
            return -1
        return len(text) * 10

    def get_text_line_width(self, font, text):
        return self._w(font, text)

    def get_text_line_height(self, font, text):
        return -1 if font not in self.KNOWN else 20

    def get_text_block_height(self, font, text, px_width):
        return -1 if font not in self.KNOWN else 20


class TestEngineFontQuirks(unittest.TestCase):
    """Regression for the issue672 invisible text.

    `font: gui-3` in a style string stores " gui-3" with a leading space. The
    engine returned -1 for it, which became a NEGATIVE column width and an
    inverted rect, so the text vanished.
    """

    def setUp(self):
        FrameContext.aspect_ratios[0] = Vec3(1024, 768, 0)
        FrameContext.context = types.SimpleNamespace(
            sbs=EngineLikeSbs(), sim=None, event=FakeEvent())
        measure.measure_cache_clear()

    def tearDown(self):
        FrameContext.context = None
        measure.measure_cache_clear()

    def test_font_with_leading_space_is_normalised(self):
        # The exact issue672 shape.
        self.assertEqual(measure.measure_line_width(" gui-3", "Hello"), 50)

    def test_font_with_trailing_space(self):
        self.assertEqual(measure.measure_line_width("gui-3 ", "Hello"), 50)

    def test_unknown_font_is_unmeasurable_not_negative(self):
        # A genuinely unknown tag must yield None (-> flex), never a negative
        # width, which would invert the rect and hide the widget.
        self.assertIsNone(measure.measure_line_width("no-such-font", "Hello"))
        self.assertIsNone(measure.measure_line_height("no-such-font", "Hello"))
        self.assertIsNone(measure.measure_block_height("no-such-font", "Hi", 100))

    def test_negative_is_never_cached(self):
        measure.measure_line_width("no-such-font", "Hello")
        self.assertNotIn(("no-such-font", "Hello"), measure._line_w)

    def test_measure_props_survives_a_spaced_font(self):
        from sbs_utils.mast.parsers import CONTENT
        got = measure.measure_props("$text:`New Row1 is longer`;font: gui-3;",
                                    CONTENT, None, " gui-3", Vec3(1024, 768, 0))
        self.assertIsNotNone(got)
        self.assertGreater(got[0], 0.0, "content width came out non-positive")

    def test_measure_props_unknown_font_is_unmeasurable(self):
        from sbs_utils.mast.parsers import CONTENT
        got = measure.measure_props("$text:`Hi`;font:bogus;",
                                    CONTENT, None, "bogus", Vec3(1024, 768, 0))
        self.assertIsNone(got, "unknown font must be unmeasurable, not sized")


class TestDefaultFontPinned(unittest.TestCase):
    """The default font is a RENDER-CONFIRMED constant, not a guess.

    It was wrong for a while (gui-3), and nothing failed -- the error was in the
    forgiving direction, so every unfonted widget was merely measured wider than
    it drew. That is exactly the kind of mistake that survives a green suite, so
    the pinned value gets a test of its own.

    Re-confirm with missions/layout_probe -> "Pin Font" if this ever needs to
    change; do not adjust it to make some other test pass.
    """

    def test_default_is_gui_2(self):
        self.assertEqual(measure.DEFAULT_FONT, "gui-2")

    def test_default_is_a_tag_the_engine_knows(self):
        # An unknown tag measures -1 in the engine, which becomes a negative
        # width and an inverted rect -- text vanishes. The default must never
        # be a tag that can do that.
        self.assertIn(measure.DEFAULT_FONT,
                      {"smallest", "gui-1", "gui-2", "gui-3", "gui-4",
                       "gui-5", "gui-6"})

    def test_unset_font_measures_as_the_default(self):
        for unset in (None, "", "   ", 0):
            with self.subTest(unset=unset):
                self.assertEqual(measure._font(unset), measure.DEFAULT_FONT)


if __name__ == "__main__":
    unittest.main()
