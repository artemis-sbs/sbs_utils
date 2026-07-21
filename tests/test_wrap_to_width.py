"""wrap_to_width: every line fits, and no text is lost.

Both invariants are here because I broke each of them once while writing it:

  * a version that summed word widths emitted lines a few px OVER the width.
    The engine then re-wrapped them into a box sized for the count we returned,
    and the extra line drew on top of its neighbour -- the exact overlap bug
    this work was meant to fix.
  * a version that "gave back" an over-long word by popping it silently DELETED
    that word from the document.

Neither showed up in the layout tests, so they get direct ones.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.helpers import FrameContext, Context
from sbs_utils.vec import Vec3

import sbs_utils.procedural.gui  # noqa: F401  (circular-import order)
from sbs_utils.pages.layout import measure
from sbs_utils.pages.layout.measure import wrap_to_width, measure_line_width


class FakeEvent:
    client_id = 0


PARA = (
    "If you've ever met a snob who literally believes his feces doesn't stink, "
    "he was probably an Arvonian. Also, he may have been a she. Adult Arvonians "
    "are the size and shape of pre-pubescent humans, so we outsiders struggle "
    'to tell Arvonian males and females apart. This has given the galaxy many '
    'hilarious "an Arvonian walks into a bar..." jokes.'
)


class TestWrapToWidth(unittest.TestCase):
    def setUp(self):
        from cosmos_dev.mock import sbs as mock_sbs
        mock_sbs.create_new_sim()
        FrameContext.aspect_ratios[0] = Vec3(1024, 768, 0)
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent())
        measure.measure_cache_clear()

    def tearDown(self):
        measure.measure_cache_clear()
        FrameContext.context = None

    def test_every_line_fits_the_width(self):
        for width in range(200, 900, 37):
            lines = wrap_to_width("gui-2", PARA, width)
            for line in lines:
                with self.subTest(width=width, line=line[:30]):
                    self.assertLessEqual(measure_line_width("gui-2", line), width)

    def test_no_word_is_lost(self):
        for width in range(200, 900, 37):
            lines = wrap_to_width("gui-2", PARA, width)
            with self.subTest(width=width):
                self.assertEqual(" ".join(lines).split(), PARA.split())

    def test_an_over_long_word_is_broken_not_overhung(self):
        # The engine breaks mid-word rather than letting a word overhang, and
        # so must we -- an overhanging word draws over the next column.
        word = "Supercalifragilisticexpialidocious" * 3
        lines = wrap_to_width("gui-2", word, 120)
        self.assertGreater(len(lines), 1)
        for line in lines:
            self.assertLessEqual(measure_line_width("gui-2", line), 120)
        self.assertEqual("".join(lines), word)

    def test_it_does_not_break_earlier_than_it_must(self):
        """The symptom that started this: breaking early wastes a line.

        Adding the first word of line N+1 to line N must genuinely not fit.
        """
        width = 635
        lines = wrap_to_width("gui-2", PARA, width)
        for a, b in zip(lines, lines[1:]):
            first_of_next = b.split()[0]
            with self.subTest(line=a[:30]):
                self.assertGreater(
                    measure_line_width("gui-2", a + " " + first_of_next), width,
                    "this line could have held one more word")

    def test_short_text_is_one_line(self):
        self.assertEqual(wrap_to_width("gui-2", "hello there", 5000),
                         ["hello there"])

    def test_empty_text(self):
        self.assertEqual(wrap_to_width("gui-2", "", 500), [])


if __name__ == "__main__":
    unittest.main()
