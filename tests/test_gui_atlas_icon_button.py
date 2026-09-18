"""A named icon drawn from a mission's own sheet can be a BUTTON.

`gui_icon_name_button` used to refuse atlas art ("an Image has no click path") and
draw nothing, so a mission that re-skinned an icon lost it from every button. The
engine has no image-button command, but any layout column can carry a click region,
so the button is an Image with a transparent click region over it. `gui_icon_rename`
then switches it between two named looks in place (a toggle's on/off).

    python -m unittest tests.test_gui_atlas_icon_button
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import os
import unittest

import cosmos_dev.mock.sbs as sbs
from sbs_utils.mast.mast_globals import MastGlobals
from sbs_utils.pages.layout.image import Image
from sbs_utils.procedural.gui.image import ImageAtlas
from sbs_utils.procedural.gui.icon import gui_icon_add_atlas

# _Base is reused; its HITS is NOT. Under `discover` that module is loaded twice (as
# `test_gui_icon_button_data` and `tests.test_gui_icon_button_data`), and the MAST
# global icb_hit appends to whichever copy registered last.
from tests.test_gui_icon_button_data import _Base, HEAD

# A real PNG the atlas can find, referenced absolutely (art outside the install).
SHEET = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "data", "crafting").replace("\\", "/")

PRESSES = []


def aib_press():
    PRESSES.append("pressed")


def aib_hit(what):
    PRESSES.append(what)


MastGlobals.import_python_function(aib_press)
MastGlobals.import_python_function(aib_hit)


class TestAtlasIconButton(_Base):

    def setUp(self):
        self._saved = dict(ImageAtlas.all)
        PRESSES.clear()
        self.sent = []
        self._orig = {}
        for name in ("send_gui_image", "send_gui_clickregion", "send_gui_iconbutton"):
            self._orig[name] = getattr(sbs, name)
            setattr(sbs, name, self._spy(name))

    def _spy(self, name):
        orig = getattr(sbs, name)

        def spy(client_id, parent, tag, props, *rect):
            self.sent.append((name, tag, props))
            return orig(client_id, parent, tag, props, *rect)
        return spy

    def tearDown(self):
        for name, fn in self._orig.items():
            setattr(sbs, name, fn)
        ImageAtlas.all.clear()
        ImageAtlas.all.update(self._saved)
        super().tearDown()

    def build(self, body):
        gui_icon_add_atlas("aib.on", SHEET, 0, 0, 64, 64)
        gui_icon_add_atlas("aib.off", SHEET, 64, 0, 128, 64)
        return self.start(HEAD + body + 'await gui()\n')

    def test_AN_ATLAS_NAME_BUILDS_A_CLICKABLE_IMAGE(self):
        self.build('s = gui_icon_name_button("aib.off", color="#8A9AAB")\n')
        _, widget, _ = self.only(Image)
        kinds = {k for k, _, _ in self.sent}
        self.assertIn("send_gui_image", kinds)
        self.assertNotIn("send_gui_iconbutton", kinds)
        regions = [p for k, t, p in self.sent if k == "send_gui_clickregion" and t == widget.click_tag]
        self.assertTrue(regions, "no click region over the image")
        # Transparent: the art is all that shows (the default fill is WHITE).
        self.assertIn("background_color:#0000", regions[-1])

    def test_A_CLICK_RUNS_ON_PRESS(self):
        self.build('s = gui_icon_name_button("aib.off", on_press=aib_press)\n')
        _, widget, _ = self.only(Image)
        self.click(widget.click_tag)
        self.assertNoRuntimeErrors()
        self.assertEqual(["pressed"], PRESSES)

    def test_a_click_fires_on_gui_message(self):
        self.build('s = gui_icon_name_button("aib.off")\n'
                   'on gui_message(s):\n'
                   '    aib_hit("msg")\n')
        _, widget, _ = self.only(Image)
        self.click(widget.click_tag)
        self.assertNoRuntimeErrors()
        self.assertEqual(["msg"], PRESSES)

    def test_RENAME_SWAPS_THE_LOOK_IN_PLACE_AND_REDRAWS(self):
        self.build('s = gui_icon_name_button("aib.off", color="#8A9AAB")\n'
                   'on gui_message(s):\n'
                   '    gui_icon_rename(s, "aib.on", "#F2C14E")\n')
        tag, widget, _ = self.only(Image)
        before = [p for k, t, p in self.sent if k == "send_gui_image" and t == tag][-1]
        self.sent.clear()
        self.click(widget.click_tag)
        self.assertNoRuntimeErrors()
        # The engine loop flushes dirty widgets after every event (handlerhooks).
        from sbs_utils.pages.layout.dirty import Dirty
        Dirty.represent_dirty()
        after = [p for k, t, p in self.sent if k == "send_gui_image" and t == tag]
        self.assertTrue(after, "the swapped image was never re-sent")
        self.assertNotEqual(before, after[-1])
        self.assertIn("#F2C14E", after[-1])
        # Same widget, same tag - not a rebuild.
        self.assertIs(widget, self.only(Image)[1])

    def test_a_built_in_name_is_still_an_icon_button(self):
        from sbs_utils.pages.layout.icon_button import IconButton
        self.build('s = gui_icon_name_button("gear")\n')
        self.only(IconButton)

    def test_an_unknown_name_draws_nothing(self):
        self.build('s = gui_icon_name_button("aib.nope")\n')
        self.assertEqual([], self.entries(Image))


class TestImageButton(TestAtlasIconButton):
    """`gui_image_button`: any image, not just a named icon. Inherits the spies."""

    # The parent's tests are not re-run here.
    test_AN_ATLAS_NAME_BUILDS_A_CLICKABLE_IMAGE = None
    test_A_CLICK_RUNS_ON_PRESS = None
    test_a_click_fires_on_gui_message = None
    test_RENAME_SWAPS_THE_LOOK_IN_PLACE_AND_REDRAWS = None
    test_a_built_in_name_is_still_an_icon_button = None
    test_an_unknown_name_draws_nothing = None

    def build(self, body):
        return self.start(HEAD + f'img = "{SHEET}"\n' + body + 'await gui()\n')

    def test_A_PLAIN_IMAGE_FILE_IS_A_BUTTON(self):
        self.build('b = gui_image_button(img, on_press=aib_press)\n')
        _, widget, _ = self.only(Image)
        regions = [p for k, t, p in self.sent if k == "send_gui_clickregion" and t == widget.click_tag]
        self.assertTrue(regions)
        self.assertIn("background_color:#0000", regions[-1])
        self.click(widget.click_tag)
        self.assertNoRuntimeErrors()
        self.assertEqual(["pressed"], PRESSES)

    def test_DATA_REACHES_THE_HANDLER(self):
        self.build('b = gui_image_button(img, data={"card": 7})\n'
                   'on gui_message(b):\n'
                   '    aib_hit(card)\n')
        _, widget, _ = self.only(Image)
        self.click(widget.click_tag)
        self.assertNoRuntimeErrors()
        self.assertEqual([7], PRESSES)

    def test_a_style_can_give_the_region_a_fill(self):
        self.build('b = gui_image_button(img, "click_background:#3366;")\n')
        _, widget, _ = self.only(Image)
        regions = [p for k, t, p in self.sent if k == "send_gui_clickregion" and t == widget.click_tag]
        self.assertIn("background_color:#3366", regions[-1])


if __name__ == "__main__":
    unittest.main()
