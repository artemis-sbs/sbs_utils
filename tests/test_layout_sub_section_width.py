"""A sub-section's col-width is ITS width, not a default for what is inside it.

`gui_sub_section("col-width:25;")` means "I take 25 of my parent row". It used to also
mean "every column inside me takes 25", because a Layout is both a COLUMN (in its parent)
and a SECTION (holding rows), and the width cascade read the same `default_width` for
both roles. Two controls in such a sub-section therefore took 25 each: the second spilled
straight out of the sub-section and was drawn over whatever came next.

That is what made the comms console's right column overlap, and no expression in the
layout could have fixed it - the sub-section was 25 wide and its contents were not.

The golden corpus (tests/layout_corpus.py) has no nested layout carrying a col-width, so
it could not catch this. These assert the invariant directly: whatever is inside a
sub-section stays inside it.

    python -m unittest tests.test_layout_sub_section_width
"""
import types
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.helpers import FrameContext
from sbs_utils.vec import Vec3
from sbs_utils.mast.parsers import StyleDefinition

import sbs_utils.procedural.gui  # noqa: F401  (import order: circular via blank)
from sbs_utils.pages.layout.layout import Layout
from sbs_utils.pages.layout.row import Row
from sbs_utils.pages.layout.column import Column


def _width(item, value):
    item.set_col_width(StyleDefinition.parse(f"col-width: {value};")["col-width"])
    return item


def _sub_section(columns, width=None):
    """A sub-section holding one row of `columns`, optionally `width` wide."""
    row = Row()
    for c in columns:
        row.add(c)
    section = Layout("inner", [row], 0, 0, 100, 100)
    if width is not None:
        _width(section, width)
    return section


def _calc(section, sibling=True):
    row = Row()
    row.add(section)
    if sibling:
        row.add(Column())
    outer = Layout("outer", [row], 0, 0, 100, 100)
    outer.calc(0)
    return outer


class SubSectionWidthTests(unittest.TestCase):
    def setUp(self):
        FrameContext.context = types.SimpleNamespace(
            sbs=None, sim=None, event=types.SimpleNamespace(client_id=0))
        FrameContext.aspect_ratios[0] = Vec3(1280, 720, 0)

    def tearDown(self):
        FrameContext.context = None

    def test_two_columns_SHARE_the_sub_sections_width(self):
        a, b = Column(), Column()
        section = _sub_section([a, b], width="25")
        _calc(section)
        self.assertAlmostEqual(section.bounds.right, 25.0, places=2)
        self.assertAlmostEqual(a.bounds.right, 12.5, places=2)
        self.assertAlmostEqual(b.bounds.left, 12.5, places=2)
        self.assertAlmostEqual(b.bounds.right, 25.0, places=2)

    def test_nothing_inside_spills_out_of_the_sub_section(self):
        # The invariant that matters. The old behavior put the last column at 25->50,
        # i.e. entirely outside its own sub-section and on top of the next one.
        cols = [Column() for _ in range(4)]
        section = _sub_section(cols, width="25")
        _calc(section)
        for i, c in enumerate(cols):
            self.assertGreaterEqual(c.bounds.left, section.bounds.left - 0.01, f"col{i}")
            self.assertLessEqual(c.bounds.right, section.bounds.right + 0.01, f"col{i}")

    def test_a_column_keeps_its_OWN_width_inside_a_sub_section(self):
        fixed, flex = _width(Column(), "10"), Column()
        section = _sub_section([fixed, flex], width="40")
        _calc(section)
        self.assertAlmostEqual(fixed.bounds.right - fixed.bounds.left, 10.0, places=2)
        self.assertAlmostEqual(flex.bounds.right, 40.0, places=2)

    def test_a_row_width_inside_a_sub_section_still_cascades(self):
        # Only the SECTION fallback was wrong. A row's col-width is a genuine default
        # for that row's columns and must keep working.
        a, b = Column(), Column()
        row = Row()
        row.add(a)
        row.add(b)
        row.set_col_width(StyleDefinition.parse("col-width: 5;")["col-width"])
        section = Layout("inner", [row], 0, 0, 100, 100)
        _width(section, "50")
        _calc(section)
        self.assertAlmostEqual(a.bounds.right - a.bounds.left, 5.0, places=2)
        self.assertAlmostEqual(b.bounds.right - b.bounds.left, 5.0, places=2)

    def test_a_sub_section_with_no_width_is_unchanged(self):
        a, b = Column(), Column()
        section = _sub_section([a, b])
        _calc(section)
        # Two flex columns split the sub-section, which itself split the outer row.
        self.assertAlmostEqual(section.bounds.right, 50.0, places=2)
        self.assertAlmostEqual(a.bounds.right, 25.0, places=2)
        self.assertAlmostEqual(b.bounds.right, 50.0, places=2)


if __name__ == "__main__":
    unittest.main()
