"""Where a listbox's items actually land, and how big their click regions are.

An item's click region is emitted from its SECTION bounds (`Layout._post_present` ->
`send_gui_clickregion`), so section geometry is not cosmetic - it is what a player can
hit. This file pins that geometry, which nothing did before: the golden corpus
(tests/layout_corpus.py) covers `Layout.calc` only and contains no listbox at all, and
`test_listbox_packing.py` never exercises a non-zero gap.

The harness is `test_listbox_modes`'s: a FakePage and the real `_present`, so these are
measurements of the shipped path rather than of a helper.

Numbers are at 1024x768. A bare number in a style is percent-of-screen; `em` is the
font-relative unit. `1.2em` in a row resolves against the row's real font (24px here) =
3.75% of 768.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.vec import Vec3
from sbs_utils.mast.parsers import StyleDefinition

import sbs_utils.procedural.gui  # noqa: F401  (circular-import order)
from sbs_utils.pages.widgets.layout_listbox import LayoutListbox
from sbs_utils.pages.layout.bounds import Bounds


class FakeTask:
    class _Main:
        class _Page:
            client_id = 0
        page = _Page()
    main = _Main()

    def compile_and_format_string(self, value):
        return value

    def get_variable(self, name, default=None):
        return default

    def set_variable(self, name, value):
        pass


class FakePage:
    gui_task = FakeTask()


PANEL = Bounds(2.0, 10.0, 30.0, 90.0)
ROW_1_2EM = 3.75          # 1.2em x 24px / 768 - a row, against its own font
ROW_1_6EM = 5.0           # 1.6em x 24px / 768 - a listbox row-height, against ITS font


def fixed_row(item, **kwargs):
    """The common shape: the template declares its own row height."""
    from sbs_utils.procedural.gui import gui_row, gui_text
    gui_row("row-height: 1.2em;")
    gui_text(f"$text:`{item}`;")
    return None


def unstyled_row(item, **kwargs):
    """A template that does NOT declare a height - it expects to fill the item."""
    from sbs_utils.procedural.gui import gui_row, gui_text
    gui_row()
    gui_text(f"$text:`{item}`;")
    return None


def two_rows(item, **kwargs):
    """A multi-row item, which must be able to grow past any declared floor."""
    from sbs_utils.procedural.gui import gui_row, gui_text
    gui_row("row-height: 1.2em;")
    gui_text(f"$text:`{item}`;")
    gui_row("row-height: 1.0em;")
    gui_text(f"$text:`sub`;")
    return None


class ListboxGeometryBase(unittest.TestCase):
    def setUp(self):
        from cosmos_dev.mock import sbs as mock_sbs
        mock_sbs.create_new_sim()
        FrameContext.aspect_ratios[0] = Vec3(1024, 768, 0)
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent())
        FrameContext.page = FakePage()

    def tearDown(self):
        FrameContext.page = None
        FrameContext.context = None

    def sections(self, template=fixed_row, style=None, count=5, **kw):
        lb = LayoutListbox(PANEL.left, PANEL.top, "lb",
                           [f"i{i}" for i in range(count)],
                           item_template=template, select=True, **kw)
        lb.tag = "lb"
        lb.bounds = Bounds(PANEL)
        lb.client_id = 0
        if style:
            from sbs_utils.procedural.style import apply_control_styles
            apply_control_styles(".listbox", style, lb, FakeTask())
        lb._present(FakeEvent())
        return [s for s in lb.sections if getattr(s, "item_index", None) is not None]

    def pitch(self, secs):
        return secs[1].bounds.top - secs[0].bounds.top


class UndeclaredIsUnchanged(ListboxGeometryBase):
    """The 19 call sites that declare nothing must not move, ever.

    This is the guard on every future change to listbox sizing: with no `row-height` and
    no `item-gap`, an item is exactly as tall as its template's rows and items are
    flush.
    """

    def test_the_item_is_as_tall_as_its_template(self):
        secs = self.sections()
        self.assertAlmostEqual(secs[0].bounds.height, ROW_1_2EM, places=3)

    def test_items_are_flush_with_no_gap(self):
        secs = self.sections()
        self.assertAlmostEqual(self.pitch(secs), ROW_1_2EM, places=3)

    def test_a_multi_row_template_measures_both_rows(self):
        secs = self.sections(template=two_rows)
        self.assertGreater(secs[0].bounds.height, ROW_1_2EM)
        self.assertAlmostEqual(self.pitch(secs), secs[0].bounds.height, places=3)


class TheClickRegionIsTheRow(ListboxGeometryBase):
    """The reported bug: a row you can see but cannot reliably click.

    The click region IS the section, so an item whose section is shorter than the text
    drawn in it has a hit band smaller than it looks. The engine does not clip, so
    nothing about the drawn row reveals the mismatch.
    """

    def test_a_declared_row_height_is_the_sections_height(self):
        secs = self.sections(style="row-height: 1.6em;")
        # 5.0, not 4.167: the listbox used to resolve em against a hard-coded font
        # size of 20 rather than its own. The template's 1.2em row is shorter, so
        # the declared height is the floor that wins.
        self.assertAlmostEqual(secs[0].bounds.height, ROW_1_6EM, places=2)

    def test_a_taller_template_still_wins(self):
        # `row-height` is a FLOOR, not a cap - a two-row item must not be clipped into
        # a one-row click region.
        secs = self.sections(template=two_rows, style="row-height: 1.0em;")
        self.assertGreater(secs[0].bounds.height, ROW_1_2EM)

    def test_an_unstyled_template_fills_the_item_instead_of_collapsing(self):
        # With a zero-height section every row inside resolves to 0 (the flex pass
        # divides an available height of 0), so the item vanished: no click region, and
        # `pack_slots` thought one item filled the whole box.
        secs = self.sections(template=unstyled_row, style="row-height: 1.6em;")
        self.assertAlmostEqual(secs[0].bounds.height, ROW_1_6EM, places=2)
        self.assertGreater(len(secs), 1)


class GapIsSeparateFromHeight(ListboxGeometryBase):
    """`item-gap` is the spacing; `row-height` is the height. They are different axes."""

    def test_a_gap_adds_between_items_without_changing_them(self):
        secs = self.sections(style="item-gap: 1.0em;")
        self.assertAlmostEqual(secs[0].bounds.height, ROW_1_2EM, places=3)
        self.assertGreater(self.pitch(secs), ROW_1_2EM)

    def test_height_and_gap_compose(self):
        secs = self.sections(style="row-height: 1.6em;item-gap: 1.0em;")
        gap = self.pitch(secs) - secs[0].bounds.height
        self.assertAlmostEqual(secs[0].bounds.height, ROW_1_6EM, places=2)
        self.assertGreater(gap, 0)

    def test_a_declared_height_does_not_double_as_a_gap(self):
        # The defect this change removes: `row-height` used to be the gap, so a list
        # declaring the same value its template used rendered at twice the pitch.
        secs = self.sections(style="row-height: 1.2em;")
        self.assertAlmostEqual(self.pitch(secs), secs[0].bounds.height, places=3)


if __name__ == "__main__":
    unittest.main()
