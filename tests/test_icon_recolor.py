"""Recoloring an icon that is already on screen (gui_icon_recolor + Icon.update).

Two things are under test and they are separate failures. The TINT has to land on
whichever widget `gui_icon_name` produced - an Icon for a built-in glyph, an Image when
a mission has re-skinned that name - and the widget has to SAY it changed, or the new
color sits in the object until something else happens to rebuild the page.

    python -m unittest tests.test_icon_recolor
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.pages.layout.icon import Icon
from sbs_utils.pages.layout.icon_button import IconButton
from sbs_utils.procedural.gui.icon import gui_icon_recolor


class _Marked:
    """Records the dirty call the layout base class would make."""

    def __init__(self):
        self.marks = 0

    def mark_value_dirty(self, force_layout=False):
        self.marks += 1


class _TestIcon(Icon):
    # _Marked FIRST would be cleaner, but Column already defines mark_value_dirty and
    # would win the MRO - so the counter is declared right here where it cannot lose.
    def __init__(self, props):
        Icon.__init__(self, "tag", props)
        self.marks = 0

    mark_value_dirty = _Marked.mark_value_dirty


class _TestIconButton(IconButton):
    def __init__(self, props):
        IconButton.__init__(self, "tag", props)
        self.marks = 0

    mark_value_dirty = _Marked.mark_value_dirty


class _AtlasIcon(_Marked):
    """What `gui_icon_name` returns for a re-skinned name: an Image, whose tint is a
    plain attribute rather than a props string."""

    is_hidden_by_script = False

    def __init__(self):
        _Marked.__init__(self)
        self.color = "white"


class UpdateSaysItChanged(unittest.TestCase):
    def test_an_icon_marks_itself_dirty(self):
        """Without this a damage light recolors in the object and goes on DRAWING its
        old color until the console is left and re-entered."""
        icon = _TestIcon("icon_index:33;color:springgreen;")
        icon.update("icon_index:33;color:Crimson;")
        self.assertEqual(icon.props, "icon_index:33;color:Crimson;")
        self.assertEqual(icon.marks, 1)

    def test_an_icon_button_marks_itself_dirty(self):
        button = _TestIconButton("icon_index:54;color:#fff")
        button.update("icon_index:54;color:#0ff")
        self.assertEqual(button.marks, 1)

    def test_a_hidden_icon_does_not_bother(self):
        icon = _TestIcon("icon_index:33;")
        icon._show = False          # what gui_hide() sets; is_hidden_by_script reads it
        icon.update("icon_index:33;color:Crimson;")
        self.assertEqual(icon.marks, 0)


class RecolorFindsTheColorWhereverItLives(unittest.TestCase):
    def test_a_built_in_glyph_keeps_its_index(self):
        icon = _TestIcon("icon_index:33;color:springgreen;")
        self.assertTrue(gui_icon_recolor(icon, "Crimson"))
        self.assertIn("icon_index:33", icon.props)
        self.assertIn("color:Crimson", icon.props)

    def test_a_glyph_with_no_color_yet_gains_one(self):
        icon = _TestIcon("icon_index:27;")
        gui_icon_recolor(icon, "Crimson")
        self.assertIn("color:Crimson", icon.props)
        self.assertIn("icon_index:27", icon.props)

    def test_a_reskinned_name_is_an_IMAGE_and_still_recolors(self):
        """The whole point of asking for an icon by name is that the caller does not
        know which of the two it got."""
        image = _AtlasIcon()
        self.assertTrue(gui_icon_recolor(image, "Crimson"))
        self.assertEqual(image.color, "Crimson")
        self.assertEqual(image.marks, 1)

    def test_nothing_to_recolor_is_not_an_error(self):
        """gui_icon_name returns None for an unknown name, and a console that drew a
        row of them should not have to check each one."""
        self.assertFalse(gui_icon_recolor(None, "Crimson"))
        self.assertFalse(gui_icon_recolor(_TestIcon("icon_index:1;"), ""))
