import types
import unittest

from sbs_utils.helpers import FrameContext
from sbs_utils.vec import Vec3

# procedural.gui must be imported before pages.layout.layout to avoid a
# circular import through pages.layout.blank
import sbs_utils.procedural.gui  # noqa: F401
from sbs_utils.mast.parsers import StyleDefinition
from sbs_utils.pages.layout.column import Column
from sbs_utils.pages.layout.layout import Layout
from sbs_utils.pages.layout.row import Row


class FakeSbs:
    """Records send_gui_image rects so the drawn border/background can be asserted."""

    def __init__(self):
        self.images = []

    def __getattr__(self, name):
        def record(*args, **kwargs):
            if name == "send_gui_image":
                # client_id, region_tag, tag, props, left, top, right, bottom
                self.images.append((args[2], args[4], args[5], args[6], args[7]))
        return record


class FakeEvent:
    client_id = 0


def style(text):
    return StyleDefinition.parse(text)


class TestLayoutBoxModel(unittest.TestCase):
    """The box model must be applied exactly once per element.

    A sub section is a Layout stored as a column, so it is visited by both the
    parent's column pass and its own calc(). Applying margin/border/padding in
    both inset its content twice.
    """

    def setUp(self):
        FrameContext.aspect_ratios[0] = Vec3(1024, 768, 0)
        self.sbs = FakeSbs()
        FrameContext.context = types.SimpleNamespace(
            sbs=self.sbs, sim=None, event=FakeEvent())

    def build(self, styled, prop, amount="10,10,10,10"):
        """A full-width section holding one column; returns (column, inner_leaf).

        ``styled`` is either Column (leaf) or Layout (sub section).
        """
        parsed = style(f"{prop}: {amount};")[prop]
        if styled is Layout:
            inner = Column()
            inner_row = Row()
            inner_row.add(inner)
            col = Layout(rows=[inner_row])
        else:
            col = inner = Column()
        setattr(col, f"{prop}_style", parsed)
        row = Row()
        row.add(col)
        section = Layout(rows=[row], left=0, top=0, right=100, bottom=100)
        section.calc(0)
        return col, inner

    def test_leaf_column_box_model_applied_once(self):
        for prop in ("margin", "border", "padding"):
            with self.subTest(prop=prop):
                col, _ = self.build(Column, prop)
                self.assertAlmostEqual(col.bounds.left, 10.0, places=3)
                self.assertAlmostEqual(col.bounds.right, 90.0, places=3)

    def test_sub_section_box_model_applied_once(self):
        for prop in ("margin", "border", "padding"):
            with self.subTest(prop=prop):
                sub, inner = self.build(Layout, prop)
                # bounds is the outer rect; only the content is inset, and once.
                self.assertAlmostEqual(sub.bounds.left, 0.0, places=3)
                self.assertAlmostEqual(sub.bounds.right, 100.0, places=3)
                self.assertAlmostEqual(inner.bounds.left, 10.0, places=3)
                self.assertAlmostEqual(inner.bounds.right, 90.0, places=3)

    def test_nested_sub_sections_do_not_compound(self):
        parsed = style("padding: 10,10,10,10;")["padding"]
        leaf = Column()
        r_in = Row()
        r_in.add(leaf)
        inner_sub = Layout(rows=[r_in])
        inner_sub.padding_style = parsed

        r_mid = Row()
        r_mid.add(inner_sub)
        outer_sub = Layout(rows=[r_mid])
        outer_sub.padding_style = parsed

        r_out = Row()
        r_out.add(outer_sub)
        section = Layout(rows=[r_out], left=0, top=0, right=100, bottom=100)
        section.calc(0)

        # Two levels of 10 == 20 total, not 40.
        self.assertAlmostEqual(leaf.bounds.left, 20.0, places=3)
        self.assertAlmostEqual(leaf.bounds.right, 80.0, places=3)

    def test_sub_section_border_and_background_rects(self):
        st = style("margin:10,10,10,10;border:5,5,5,5;")
        leaf = Column()
        inner_row = Row()
        inner_row.add(leaf)
        sub = Layout(rows=[inner_row])
        sub.tag = "sub1"
        sub.margin_style = st["margin"]
        sub.border_style = st["border"]
        sub.border_color = "#f00"
        sub.background_color = "#00f"

        row = Row()
        row.add(sub)
        section = Layout(rows=[row], left=0, top=0, right=100, bottom=100)
        section.calc(0)
        sub.present(FakeEvent())

        drawn = {("border" if tag.startswith("__bb") else "background"): (left, right)
                 for tag, left, top, right, bottom in self.sbs.images}

        # border sits inside the margin; background inside the border.
        self.assertAlmostEqual(drawn["border"][0], 10.0, places=3)
        self.assertAlmostEqual(drawn["border"][1], 90.0, places=3)
        self.assertAlmostEqual(drawn["background"][0], 15.0, places=3)
        self.assertAlmostEqual(drawn["background"][1], 85.0, places=3)
        # ...and the content inside that.
        self.assertAlmostEqual(leaf.bounds.left, 15.0, places=3)
        self.assertAlmostEqual(leaf.bounds.right, 85.0, places=3)


if __name__ == "__main__":
    unittest.main()
