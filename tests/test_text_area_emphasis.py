"""`**strong**` and `*em*` in a writer's prose, drawn as emphasis (opt-in).

The xESS and the hail screens drew `**bold**` with its asterisks - the library's own
transcripts and readings emit `**name**`, and so does a writer. The engine draws a text
widget in one font and one color, so a strong word is drawn as its own PIECE, at the x
the words before it end at, struck twice a pixel apart (there is no bold face at body
size). `*em*` has no italic to use and loses only its marks.

It is OFF by default: the Quest Log and every other area draw the marks as typed, which
is what the AMD format page documents.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.helpers import FrameContext, Context
from sbs_utils.vec import Vec3

import sbs_utils.procedural.gui  # noqa: F401  (circular-import order)
from sbs_utils.pages.layout.text_area import (TextArea, TextLine, IconLine,
                                              emphasis_runs, emphasis_plain)
from sbs_utils.pages.layout.bounds import Bounds
from sbs_utils.pages.layout import measure
from sbs_utils.pages.layout.measure import measure_line_width

GOOD_FACE = "ter #e4cb8e 1 0;ter #fff 12 6;ter #e4cb8e 3 1"


class FakeEvent:
    client_id = 0


class Base(unittest.TestCase):
    def setUp(self):
        from cosmos_dev.mock import sbs as mock_sbs
        mock_sbs.create_new_sim()
        self.sbs = mock_sbs
        FrameContext.aspect_ratios[0] = Vec3(1024, 768, 0)
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent())
        measure.measure_cache_clear()
        self.sent = []
        self._orig = mock_sbs.send_gui_text

        def record(cid, region, tag, props, left, top, right, bottom):
            self.sent.append((tag, props, left, top))
            return self._orig(cid, region, tag, props, left, top, right, bottom)
        mock_sbs.send_gui_text = record

    def tearDown(self):
        self.sbs.send_gui_text = self._orig
        measure.measure_cache_clear()
        FrameContext.context = None

    def area(self, text, bounds=Bounds(0, 0, 90, 90), **kw):
        ta = TextArea("t", text, **kw)
        ta.tag = "t"
        ta.bounds = Bounds(bounds.left, bounds.top, bounds.right, bounds.bottom)
        ta.client_id = 0

        return ta

    def draw(self, ta):
        ta.calc_rich(0) if not ta.simple_text else None
        ta.recalc = False
        ta._present(FakeEvent())
        return self.sent

    @staticmethod
    def text_of(props):
        return props.split("$text:", 1)[1].split(";", 1)[0].strip("`")


class TestTheRuns(unittest.TestCase):
    def test_strong_and_em(self):
        self.assertEqual([("Find ", None), ("the", "strong"), (" hulk and ", None),
                          ("run", "em"), (".", None)],
                         emphasis_runs("Find **the** hulk and *run*."))
        self.assertEqual("Find the hulk and run.", emphasis_plain("Find **the** hulk and *run*."))

    def test_what_is_not_emphasis(self):
        for text in ("5 * 3 * 2", "a ** b", "** not **", "*", "x*y*z", "snake_case_word"):
            self.assertEqual([(text, None)], emphasis_runs(text), text)

    def test_braces_are_left_alone(self):
        self.assertEqual("Call me {Captain}, now.",
                         emphasis_plain("Call me {Captain}, **now**."))


class TestDrawn(Base):
    def test_a_one_line_area_is_not_a_plain_label_any_more(self):
        ta = self.area("Find **the** hulk.", emphasis=True)
        self.assertFalse(ta.simple_text)

    def test_no_asterisk_reaches_the_engine(self):
        sent = self.draw(self.area("Find **the** hulk and *run*.", emphasis=True))
        self.assertTrue(sent)
        for _tag, props, _l, _t in sent:
            self.assertNotIn("*", props)
        words = [self.text_of(p) for _t, p, _l, _y in sent]
        self.assertIn("the", words)
        self.assertIn("Find", words)

    def test_strong_is_struck_twice_and_sits_where_the_words_before_it_end(self):
        sent = self.draw(self.area("Find **the** hulk.", emphasis=True))
        strong = [(t, l) for t, p, l, _y in sent if self.text_of(p) == "the"]
        self.assertEqual(2, len(strong))                 # the word, and its second strike
        first = [l for t, p, l, _y in sent if self.text_of(p) == "Find"][0]
        advance = (measure_line_width("gui-2", "Find X") - measure_line_width("gui-2", "X"))
        self.assertAlmostEqual(first + advance / 1024 * 100, strong[0][1], places=4)
        self.assertGreater(strong[1][1], strong[0][1])   # a pixel to the right
        self.assertEqual(len(sent), len({t for t, _p, _l, _y in sent}))   # unique tags

    def test_a_paragraph_that_wraps_keeps_its_strong_words(self):
        word = "derelict "
        text = (word * 8) + "**hull breach** " + (word * 8)
        ta = self.area(text.strip(), bounds=Bounds(0, 0, 30, 90), emphasis=True)
        sent = self.draw(ta)
        lines = [ln for ln in ta.lines if isinstance(ln, TextLine)]
        self.assertGreater(len(lines), 1)
        self.assertNotIn("*", "".join(ln.text for ln in lines))
        drawn = " ".join(self.text_of(p) for _t, p, _l, _y in sent)
        self.assertIn("hull", drawn)
        self.assertNotIn("*", drawn)

    def test_beside_a_face(self):
        ta = self.area(f"![](face://{GOOD_FACE}) **Quill**: the hull is cold.", emphasis=True)
        sent = self.draw(ta)
        self.assertIsInstance(ta.lines[0], IconLine)
        texts = [self.text_of(p) for _t, p, _l, _y in sent]
        self.assertIn("Quill", texts)
        for t in texts:
            self.assertNotIn("*", t)

    def test_off_by_default_the_marks_are_drawn_as_typed(self):
        ta = self.area("Find **the** hulk.")
        self.assertTrue(ta.simple_text)
        ta = self.area("Line one.\nFind **the** hulk.")
        sent = self.draw(ta)
        self.assertIn("**the**", " ".join(p for _t, p, _l, _y in sent))

    def test_verbatim_text_keeps_its_marks(self):
        sent = self.draw(self.area("a = **kw\nb = *args*", markdown=False, emphasis=True))
        self.assertIn("*args*", " ".join(p for _t, p, _l, _y in sent))


class TestTheSurfacesAskForIt(unittest.TestCase):
    """The screens that draw a writer's prose turn emphasis on, and keep it literal."""

    def setUp(self):
        from sbs_utils.procedural.gui import text as TEXT
        self.TEXT = TEXT
        self.calls = []
        self._saved = TEXT.gui_text_area
        TEXT.gui_text_area = lambda s, *a, **k: self.calls.append((s, k))
        self._row = __import__("sbs_utils.procedural.gui.row", fromlist=["gui_row"])
        self._saved_row = self._row.gui_row
        self._row.gui_row = lambda *a, **k: None
        self._saved_text = TEXT.gui_text
        TEXT.gui_text = lambda *a, **k: None

    def tearDown(self):
        self.TEXT.gui_text_area = self._saved
        self.TEXT.gui_text = self._saved_text
        self._row.gui_row = self._saved_row

    def test_the_hail_band_and_screen(self):
        from sbs_utils.procedural.gui import hail_gui
        content = {"name": "Quill", "line": "Call me {Captain}, **now**.",
                   "choices": ["**Yes**", "No"]}
        hail_gui._hail_band_builder(0, content)
        hail_gui._hail_screen_builder(0, dict(content))
        lines = [(s, k) for s, k in self.calls if "now" in s]
        self.assertEqual(2, len(lines))
        for s, k in self.calls:
            self.assertTrue(k.get("emphasis"), s)
        # still literal: the widget's formatter gets the braces doubled
        self.assertIn("{{Captain}}", lines[0][0])

    def test_the_transcript_emits_bold_names_and_draws_them(self):
        from sbs_utils.procedural.gui.hail_gui import hail_transcript_text
        text = hail_transcript_text({"transcript": [
            {"name": "Quill", "text": "We need help."},
            {"kind": "choice", "text": "On our way"}]})
        self.assertIn("**Quill**", text)
        from cosmos_dev.mock import sbs as mock_sbs
        mock_sbs.create_new_sim()
        FrameContext.aspect_ratios[0] = Vec3(1024, 768, 0)
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent())
        sent = []
        orig = mock_sbs.send_gui_text
        mock_sbs.send_gui_text = lambda c, r, t, p, *b: sent.append(p)
        try:
            ta = TextArea("t", text, paragraphs=False, emphasis=True)
            ta.tag, ta.client_id = "t", 0
            ta.bounds = Bounds(0, 0, 90, 90)
            ta.calc_rich(0)
            ta.recalc = False
            ta._present(FakeEvent())
        finally:
            mock_sbs.send_gui_text = orig
            FrameContext.context = None
        self.assertTrue(sent)
        self.assertNotIn("**", " ".join(sent))

    def test_the_boarding_reader(self):
        from sbs_utils.procedural import boarding
        ta = TextArea("t", "")
        self.assertFalse(ta.emphasis)
        saved = boarding.boarding_reader_text
        boarding.boarding_reader_text = lambda cid, agent=None: "**Quill**: the hull is cold."
        boarding._READERS[77] = {"text": "", "seq": None, "agent": None, "area": None}
        try:
            boarding.boarding_reader(ta, 77)
        finally:
            boarding.boarding_reader_text = saved
            boarding._READERS.pop(77, None)
        self.assertTrue(ta.emphasis)
        self.assertFalse(ta.simple_text)

    def test_every_xess_prose_area(self):
        import inspect
        import re
        from sbs_utils.procedural.gui import xess, xess_ground
        for mod in (xess, xess_ground):
            for m in re.finditer(r"gui_text_area\((?P<args>[^\n]*)", inspect.getsource(mod)):
                args = m.group("args")
                if args.startswith('""') or args.startswith('"No reading'):
                    continue        # an empty area a reader fills, or a fixed sentence
                self.assertIn("emphasis=True", args, args)


if __name__ == "__main__":
    unittest.main()
