"""The screen a writer sees when the story does not compile.

One line pasted at the wrong indent and the mission runs nothing: this screen is all the
game shows. Seen in the real engine (2026-10-03), its text started at the very top of
the screen, so the title was drawn ON TOP of the engine's own Mission Select button, and
the first thing the writer read was two labels overprinted. It also called runtime
errors "Mast Compiler Errors".

Drives the page's own `present`, and reads what it hands the engine.

    python -m unittest tests.test_error_screen
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sys
import cosmos_dev.mock.sbs as mock_sbs
sys.modules.setdefault("sbs", mock_sbs)

from sbs_utils.agent import clear_shared
from sbs_utils.gui import Gui
from sbs_utils.helpers import Context, FakeEvent, FrameContext
from sbs_utils.mast.maststory import MastStory
from sbs_utils.mast_sbs import story_nodes  # noqa: F401
from sbs_utils.mast_sbs import maststorypage
from sbs_utils.mast_sbs.maststorypage import StoryPage
from sbs_utils.spaceobject import SpaceObject

ERROR = ("\nError: Bad indentation\nat story.mast Line 57 - "
         "'relics_spawn(get_mission_dir_filename(\"mission.amd\"))'\nmodule X\n")


class _Page(StoryPage):
    story = None


class ErrorScreenTests(unittest.TestCase):
    def setUp(self):
        from sbs_utils.handlerhooks import reset_mission_state
        reset_mission_state()
        mock_sbs.create_new_sim()
        clear_shared()
        SpaceObject.clear()
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent(0, "test"))
        story = MastStory()
        self.assertEqual(story.compile("gui_text('$text:x;')\nawait gui()\n", "t", story), [])
        _Page.story = story
        FrameContext.mast = story
        self.page = _Page()
        Gui.push(0, self.page)
        self.sent = []
        self._text = mock_sbs.send_gui_text
        self._button = mock_sbs.send_gui_button

        def text(client_id, parent, tag, props, left, top, right, bottom, *a, **k):
            self.sent.append(("text", props, left, top, right, bottom))

        def button(client_id, parent, tag, props, left, top, right, bottom, *a, **k):
            self.sent.append(("button", props, left, top, right, bottom))

        mock_sbs.send_gui_text = text
        mock_sbs.send_gui_button = button

    def tearDown(self):
        mock_sbs.send_gui_text = self._text
        mock_sbs.send_gui_button = self._button
        Gui.clients = {}
        _Page.story = None
        FrameContext.task = FrameContext.page = FrameContext.mast = None
        FrameContext.context = None

    def present(self):
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent(0, "gui_present"))
        self.page.present(FakeEvent(0, "gui_present"))
        return [s for s in self.sent if s[0] == "text"], [s for s in self.sent if s[0] == "button"]

    def test_the_text_starts_below_the_engines_own_bar(self):
        self.page.compiler_errors = [ERROR]
        texts, _buttons = self.present()
        self.assertEqual(len(texts), 1)
        _kind, _props, _left, top, _right, bottom = texts[0]
        self.assertGreaterEqual(top, 6)
        self.assertEqual(top, maststorypage.ERROR_TEXT_TOP)

    def test_the_text_stops_above_its_own_buttons(self):
        self.page.compiler_errors = [ERROR]
        texts, buttons = self.present()
        self.assertTrue(buttons)
        self.assertLessEqual(texts[0][5], min(b[3] for b in buttons))

    def test_it_says_what_happened_in_plain_words_first(self):
        self.page.compiler_errors = [ERROR]
        texts, _buttons = self.present()
        props = texts[0][1]
        head, _, rest = props.partition("\n")
        self.assertIn("did not compile", head)
        self.assertIn("Attempt Rerun", head)
        self.assertIn("Bad indentation", rest)
        # A comma or a semicolon in the style string would cut the text short.
        self.assertNotIn(",", head)
        self.assertNotIn(";", head)

    def test_a_runtime_error_is_not_called_a_compiler_error(self):
        self.page.errors = ["\nmast RUNTIME ERROR\nNameError: name 'x' is not defined\n"]
        texts, _buttons = self.present()
        self.assertTrue(texts)
        self.assertIn("Runtime Errors", texts[-1][1])
        self.assertNotIn("Compiler", texts[-1][1])
        self.assertEqual(texts[-1][3], maststorypage.ERROR_TEXT_TOP)


class RuntimeErrorPageTests(unittest.TestCase):
    """The page a line that fails mid-game puts up (`handlerhooks.ErrorPage`).

    Seen in the real engine (2026-10-04): its title was drawn over the engine's own
    Mission Select button, and its text ran on under its three buttons.
    """

    def setUp(self):
        mock_sbs.create_new_sim()
        FrameContext.context = Context(mock_sbs.sim, mock_sbs, FakeEvent(0, "test"))
        self.sent = []
        self._text = mock_sbs.send_gui_text
        self._button = mock_sbs.send_gui_button

        def text(client_id, parent, tag, props, left, top, right, bottom, *a, **k):
            self.sent.append(("text", props, left, top, right, bottom))

        def button(client_id, parent, tag, props, left, top, right, bottom, *a, **k):
            self.sent.append(("button", props, left, top, right, bottom))

        mock_sbs.send_gui_text = text
        mock_sbs.send_gui_button = button
        self.addCleanup(setattr, mock_sbs, "send_gui_text", self._text)
        self.addCleanup(setattr, mock_sbs, "send_gui_button", self._button)
        self.addCleanup(setattr, FrameContext, "context", None)

    def present(self):
        from sbs_utils.handlerhooks import ErrorPage
        page = ErrorPage("mast RUNTIME ERROR\nline: 109 in file: story.mast\n"
                         "NameError: name 'true' is not defined; tug_sent = true, x")
        page.present(FakeEvent(0, "gui_present"))
        return ([s for s in self.sent if s[0] == "text"],
                [s for s in self.sent if s[0] == "button"])

    def test_the_text_is_between_the_engines_bar_and_its_own_buttons(self):
        texts, buttons = self.present()
        self.assertEqual(len(texts), 1)
        _kind, _props, _left, top, _right, bottom = texts[0]
        self.assertGreaterEqual(top, 6)
        self.assertEqual(len(buttons), 3)
        self.assertLessEqual(bottom, min(b[3] for b in buttons))

    def test_it_says_what_happened_first_and_keeps_the_whole_message(self):
        texts, _buttons = self.present()
        props = texts[0][1]
        self.assertTrue(props.startswith("$text:Runtime error."), props[:60])
        self.assertIn("Resume Mission", props)
        self.assertIn("name 'true' is not defined", props)
        self.assertIn("story.mast", props)
        # One style string: a comma, colon or semicolon inside the text would cut it.
        body = props[len("$text:"):-1]
        for mark in ",;:":
            self.assertNotIn(mark, body)


if __name__ == "__main__":
    unittest.main()
