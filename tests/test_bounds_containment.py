"""Containment tests for the layout clipping helper.

``is_out_of_bounds`` decides whether a child layout item is far enough outside
its parent that the parent should mark it ``_is_shown = False``. It is the
gate every row and column passes through on the way to the screen, so its
edge behavior is load bearing.

Also pins the integrity of ``Bounds.hidden``. That is a single class-level
instance shared by every layout item in the process; anything that writes
through it un-hides every hidden element at once.
"""

import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.pages.layout.bounds import Bounds, is_out_of_bounds


class FakeItem:
    """The duck type is_out_of_bounds accepts: a .bounds, or the four sides."""

    def __init__(self, bounds=None, left=0, top=0, right=0, bottom=0):
        self.bounds = bounds
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom


def item(left, top, right, bottom):
    return FakeItem(Bounds(left, top, right, bottom))


PARENT = item(0, 0, 100, 100)


class TestIsOutOfBounds(unittest.TestCase):
    """A child is out of bounds only when it is entirely past one edge.

    Partial overlap is NOT out of bounds -- the engine clips the overflow, and
    treating a half-visible row as hidden would blank rows that should show
    their visible part.
    """

    def test_a_child_inside_the_parent_is_in_bounds(self):
        self.assertFalse(is_out_of_bounds(item(10, 10, 20, 20), PARENT))

    def test_a_child_exactly_filling_the_parent_is_in_bounds(self):
        self.assertFalse(is_out_of_bounds(item(0, 0, 100, 100), PARENT))

    def test_a_partially_overlapping_child_is_in_bounds(self):
        """Hanging off the right edge still has a visible left portion."""
        self.assertFalse(is_out_of_bounds(item(90, 10, 150, 20), PARENT))

    def test_a_child_touching_the_edge_is_in_bounds(self):
        """left == parent.right is a zero-width sliver, not "past" the edge.

        The comparison is strict (>), so the boundary case stays visible.
        """
        self.assertFalse(is_out_of_bounds(item(100, 0, 110, 100), PARENT))

    def test_entirely_right_of_the_parent_is_out(self):
        self.assertTrue(is_out_of_bounds(item(110, 0, 120, 100), PARENT))

    def test_entirely_left_of_the_parent_is_out(self):
        self.assertTrue(is_out_of_bounds(item(-100, 0, -10, 100), PARENT))

    def test_entirely_above_the_parent_is_out(self):
        self.assertTrue(is_out_of_bounds(item(0, -100, 100, -1), PARENT))

    def test_entirely_below_the_parent_is_out(self):
        """The axis the shipped smoke check duplicated its way past."""
        self.assertTrue(is_out_of_bounds(item(0, 110, 100, 120), PARENT))


class TestTolerance(unittest.TestCase):
    def test_tolerance_widens_the_accept_band(self):
        child = item(105, 0, 120, 100)          # 5 past the right edge
        self.assertTrue(is_out_of_bounds(child, PARENT, 0.0))
        self.assertFalse(is_out_of_bounds(child, PARENT, 10.0))

    def test_tolerance_is_not_unbounded(self):
        """A tolerance smaller than the gap still reports out of bounds."""
        child = item(105, 0, 120, 100)
        self.assertTrue(is_out_of_bounds(child, PARENT, 2.0))

    def test_tolerance_applies_on_every_edge(self):
        for name, child in (
            ("right", item(105, 0, 120, 100)),
            ("left", item(-20, 0, -5, 100)),
            ("top", item(0, -20, 100, -5)),
            ("bottom", item(0, 105, 100, 120)),
        ):
            with self.subTest(edge=name):
                self.assertTrue(is_out_of_bounds(child, PARENT, 0.0))
                self.assertFalse(is_out_of_bounds(child, PARENT, 10.0))


class TestSidesFallback(unittest.TestCase):
    """When .bounds is None the four side attributes are used instead.

    Layout items are expected to carry a Bounds, but the helper accepts the
    looser shape and rows in particular grow their side attributes during
    calc(). If that fallback ever stops working, clipping silently changes.
    """

    def test_a_child_with_no_bounds_uses_its_sides(self):
        child = FakeItem(None, left=110, top=0, right=120, bottom=100)
        self.assertTrue(is_out_of_bounds(child, PARENT))

    def test_a_child_with_no_bounds_can_be_in_bounds(self):
        child = FakeItem(None, left=10, top=10, right=20, bottom=20)
        self.assertFalse(is_out_of_bounds(child, PARENT))

    def test_a_parent_with_no_bounds_uses_its_sides(self):
        parent = FakeItem(None, left=0, top=0, right=100, bottom=100)
        self.assertTrue(is_out_of_bounds(item(110, 0, 120, 100), parent))
        self.assertFalse(is_out_of_bounds(item(10, 10, 20, 20), parent))

    def test_both_sides_only(self):
        child = FakeItem(None, left=110, top=0, right=120, bottom=100)
        parent = FakeItem(None, left=0, top=0, right=100, bottom=100)
        self.assertTrue(is_out_of_bounds(child, parent))


class TestHiddenSingletonIsNotWritable(unittest.TestCase):
    """Bounds.hidden is shared by the whole process.

    It used to be handed out by the `bounds` property of a hidden item while
    set_bounds() wrote *through* that property -- so setting the bounds of one
    hidden column rewrote the sentinel, and every hidden element in the
    process reported real on-screen coordinates and stopped testing as hidden.
    """

    EXPECTED = (-1011, -1011, -999, -999)

    def _assert_sentinel_intact(self):
        h = Bounds.hidden
        self.assertEqual(
            self.EXPECTED, (h.left, h.top, h.right, h.bottom),
            "Bounds.hidden was mutated; every hidden layout item in the "
            "process now reports these coordinates")

    def test_the_sentinel_starts_where_we_think(self):
        self._assert_sentinel_intact()

    def test_setting_bounds_on_a_hidden_column_leaves_it_alone(self):
        from sbs_utils.pages.layout.column import Column
        col = Column()
        col.show(False)
        col.is_presenting = True            # the state where bounds is the sentinel
        col.set_bounds(Bounds(5, 6, 7, 8))
        col.is_presenting = False
        self._assert_sentinel_intact()
        self.assertEqual(
            (5, 6, 7, 8),
            (col._bounds.left, col._bounds.top, col._bounds.right, col._bounds.bottom),
            "the write must land on the column's own bounds")

    def test_one_hidden_column_does_not_unhide_another(self):
        """The cross-contamination the sentinel bug actually caused."""
        from sbs_utils.pages.layout.column import Column
        first, second = Column(), Column()
        first.show(False)
        second.show(False)
        first.is_presenting = True
        first.set_bounds(Bounds(5, 6, 7, 8))
        first.is_presenting = False
        self.assertTrue(second.is_hidden,
                        "hiding and repositioning one column un-hid another")
        self._assert_sentinel_intact()


class TestNoScaffoldingInTheMastNamespace(unittest.TestCase):
    """Debug helpers must not become callable from mission scripts.

    MastGlobals.import_python_function() puts a name into the ONE global MAST
    namespace every mission shares. A smoke-check named test_oob was registered
    there, so any script could call it -- and it printed rather than asserted,
    so it could never fail a build either.
    """

    def _globals(self):
        import sbs_utils.procedural.gui  # noqa: F401
        import sbs_utils.pages.layout.layout  # noqa: F401
        from sbs_utils.mast.mast_globals import MastGlobals
        return MastGlobals.globals

    def test_the_smoke_check_is_not_scriptable(self):
        self.assertNotIn("test_oob", self._globals())

    def test_the_smoke_check_is_gone_entirely(self):
        import sbs_utils.pages.layout.bounds as bounds_mod
        self.assertFalse(hasattr(bounds_mod, "test_oob"),
                         "replaced by the real tests in this file")

    def test_the_clipping_helper_is_not_scriptable(self):
        """Its own docstring says it should not be used in scripting at all."""
        self.assertNotIn("is_out_of_bounds", self._globals())


if __name__ == "__main__":
    unittest.main()
