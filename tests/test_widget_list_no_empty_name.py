"""An empty widget name must never reach the engine's widget list.

`gui_update_widgets("", "grid_face")` (LegendaryMissions Engineering) split "" into
{""}, and "" always iterates first, so the list went out with a LEADING caret. The
engine read that as one widget named after the rest of the list, saved it to
data/guiboxdata.txt, and null-derefed in GUIBoxTick every time Engineering opened.
"""
import unittest
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from cosmos_dev.mock import sbs  # noqa: F401 - registers the mock `sbs` module
from sbs_utils.helpers import FrameContext
from sbs_utils.mast_sbs.maststorypage import StoryPage
from sbs_utils.procedural.gui.widgets import gui_update_widgets

ENG = "ship_internal_view^eng_presets^grid_object_list^grid_face^grid_control^eng_heat_controls^eng_power_controls^ship_data"


class _Page:
    add_console_widget = StoryPage.add_console_widget

    def __init__(self, widgets):
        self.pending_widgets = widgets


def _check(tc, widgets):
    tc.assertFalse(widgets.startswith("^"), widgets)
    tc.assertFalse(widgets.endswith("^"), widgets)
    tc.assertNotIn("^^", widgets)


class TestNoEmptyWidgetName(unittest.TestCase):
    def tearDown(self):
        FrameContext.page = None

    def test_update_widgets_with_empty_add(self):
        page = _Page(ENG)
        FrameContext.page = page
        gui_update_widgets("", "grid_face")
        _check(self, page.pending_widgets)
        self.assertEqual(set(page.pending_widgets.split("^")),
                         set(ENG.split("^")) - {"grid_face"})

    def test_then_add_console_widget(self):
        page = _Page(ENG)
        FrameContext.page = page
        gui_update_widgets("", "grid_face")
        page.add_console_widget("grid_control")
        page.add_console_widget("grid_object_list")
        _check(self, page.pending_widgets)

    def test_add_console_widget_repairs_a_leading_caret(self):
        page = _Page("^ship_data^grid_control")
        page.add_console_widget("eng_presets")
        _check(self, page.pending_widgets)
        self.assertEqual(set(page.pending_widgets.split("^")),
                         {"ship_data", "grid_control", "eng_presets"})


if __name__ == "__main__":
    unittest.main()
