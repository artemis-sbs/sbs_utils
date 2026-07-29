"""Icons by NAME (sbs_utils.procedural.gui.icon_sheet).

    python -m unittest tests.test_icon_sheet
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.procedural.gui import icon_sheet as IN


class NamesInsteadOfNumbers(unittest.TestCase):
    """Every caller wrote a bare sheet index, so the quest log's state square and the
    list box's fold arrows were magic constants nothing could re-skin."""

    def test_a_look_resolves_to_the_built_in_sheet(self):
        self.assertEqual(IN.icon_resolve("square"), (101, None))
        self.assertEqual(IN.icon_resolve("crosshair"), (112, None))

    def test_a_meaning_follows_its_alias(self):
        self.assertEqual(IN.icon_resolve("quest.job"), IN.icon_resolve("wanted"))
        self.assertEqual(IN.icon_resolve("list.expand"), (154, None))

    def test_the_indices_the_code_already_relied_on(self):
        """These three were hardcoded in quest.py and the list box; the names must land
        on the same glyphs or every existing screen changes."""
        self.assertEqual(IN.icon_resolve("quest.state")[0], 101)
        self.assertEqual(IN.icon_resolve("list.expand")[0], 154)
        self.assertEqual(IN.icon_resolve("list.collapse")[0], 155)

    def test_an_unknown_name_draws_nothing(self):
        """A wrong icon is worse than a missing one - it looks deliberate."""
        self.assertEqual(IN.icon_resolve("no-such-icon"), (None, None))

    def test_every_index_is_on_the_drawn_part_of_the_sheet(self):
        """0..175 are drawn; 176..399 are empty slots waiting for custom art."""
        for name, idx in IN.ICON_INDEX.items():
            self.assertTrue(0 <= idx <= 175, "%s -> %d" % (name, idx))

    def test_no_two_names_are_the_same_glyph_by_accident(self):
        seen = {}
        for name, idx in IN.ICON_INDEX.items():
            self.assertNotIn(idx, seen, "%s and %s are both %d" % (name, seen.get(idx), idx))
            seen[idx] = name

    def test_every_alias_points_at_something_real(self):
        for meaning in IN.ICON_ALIAS:
            self.assertIsNotNone(IN.icon_resolve(meaning)[0], meaning)

    def test_a_mission_can_re_skin_a_meaning(self):
        """Register the LOOK on a sheet of your own and every screen drawing that meaning
        changes, with no edit to the code that draws it."""
        from sbs_utils.procedural.gui.image import ImageAtlas
        try:
            ImageAtlas.all["icon:wanted"] = object()
            index, key = IN.icon_resolve("quest.job")
            self.assertIsNone(index)
            self.assertEqual(key, "icon:wanted")
        finally:
            ImageAtlas.all.pop("icon:wanted", None)

    def test_an_ordinary_image_named_square_does_NOT_re_skin_icons(self):
        """The guard. `ImageAtlas.all` is one process-wide dict, and `square` or `flag`
        are words any mission might use for an unrelated image - without the domain that
        would silently re-skin every icon meaning pointing there."""
        from sbs_utils.procedural.gui.image import ImageAtlas
        try:
            ImageAtlas.all["square"] = object()
            self.assertEqual(IN.icon_resolve("quest.state"), (101, None))
        finally:
            ImageAtlas.all.pop("square", None)


class TheAtlasBackedPath(unittest.TestCase):
    """A named icon backed by a mission's own sheet goes out as an IMAGE (the engine has
    no icon concept for art it did not ship), so that path has to reach the engine with
    the same cell and tint the built-in path would have."""

    def setUp(self):
        from cosmos_dev.mock import sbs
        from sbs_utils.helpers import FrameContext, Context, FakeEvent
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())

    def _atlas(self, key, *rect, color=None):
        """A registered cell. `is_valid` is stubbed because whether the PNG is on disk is
        a different question from whether the right properties reach the engine, and the
        suite must not need the game's art installed to answer the second."""
        from sbs_utils.procedural.gui.image import ImageAtlas
        atlas = ImageAtlas(key, "media/icons/sheet", *rect, color=color)
        atlas.is_valid = lambda: True
        atlas.get_size = lambda: (64, 64)
        return atlas

    def _present(self, widget):
        """Draw the widget and return the property string handed to the engine."""
        from sbs_utils.helpers import FrameContext, FakeEvent
        sent = []
        ctx = FrameContext.context
        original = ctx.sbs.send_gui_image
        ctx.sbs.send_gui_image = lambda cid, parent, tag, props, *b: sent.append(props)
        try:
            widget.region_tag = "r"
            widget._present(FakeEvent())
        finally:
            ctx.sbs.send_gui_image = original
        return sent[0] if sent else None

    def test_the_cell_survives_not_the_whole_sheet(self):
        """ImageAtlas parses only image and color out of a property STRING - a sub_rect in
        one is dropped - so the key must travel, never pre-rendered props."""
        from sbs_utils.procedural.gui.image import ImageAtlas
        from sbs_utils.pages.layout.image import Image
        try:
            self._atlas("wanted", 0, 128, 128, 256)
            props = self._present(Image("t", "wanted", 3))
            self.assertIn("sub_rect:0,128,128,256", props)
        finally:
            ImageAtlas.all.pop("wanted", None)

    def test_one_registered_cell_serves_every_state(self):
        """Per-USE color, not per-key: a state pip is one cell recolored, not six."""
        from sbs_utils.procedural.gui.image import ImageAtlas
        from sbs_utils.pages.layout.image import Image
        try:
            self._atlas("pip", 0, 0, 64, 64, color="white")
            self.assertIn("color:#f66", self._present(Image("t", "pip", 3, "#f66")))
            self.assertIn("color:white", self._present(Image("t", "pip", 3)))
        finally:
            ImageAtlas.all.pop("pip", None)


if __name__ == "__main__":
    unittest.main()
