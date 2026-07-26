"""The info panel is log-first: cards are filed, and only interrupt on purpose.

Overlays took over the attention job, so a plain card no longer takes over the
panel's tab -- it goes in the tab's log, readable any time. A card that carries a
BUTTON still always interrupts: a mission awaiting the press deadlocks if the
player never sees it, so that one is not the caller's choice to get wrong.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

from cosmos_dev.mock import sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
from sbs_utils.mast_sbs.maststorypage import StoryPage
from sbs_utils.agent import Agent
from sbs_utils.gui import GuiClient
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.procedural.gui.tabbed_panel import (
    gui_info_panel_send_message, INFO_PANEL_LOG_MAX)


class _FakePanel:
    """Records tab switches so a test can assert on the interrupt."""
    def __init__(self):
        self.tabs = []

    def set_tab(self, path):
        self.tabs.append(path)


class _FakeMain:
    def __init__(self, page):
        self.page = page


class _FakeGuiTask:
    def __init__(self, page):
        self.main = _FakeMain(page)
        self.vars = {}

    def set_variable(self, name, value):
        self.vars[name] = value

    def get_variable(self, name, default=None):
        return self.vars.get(name, default)

    def compile_and_format_string(self, s):
        return s

    def format_string(self, s):
        return s


class InfoPanelBase(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        SpaceObject.clear()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        self.page = StoryPage()
        self.page.pending_gui = False
        self.page.client_id = 1001
        self.page.gui_task = _FakeGuiTask(self.page)
        self.panel = _FakePanel()
        self.page.info_panel = self.panel
        client = GuiClient(1001)
        client.page_stack.append(self.page)
        FrameContext.page = self.page

    def tearDown(self):
        FrameContext.page = None
        FrameContext.context = None
        Agent.clear()
        SpaceObject.clear()

    def live(self):
        return self.page.gui_task.get_variable("$MESSAGE", [])

    def log(self):
        return self.page.gui_task.get_variable("$MESSAGES", [])


class TestLogFirstDefault(InfoPanelBase):
    def test_plain_card_is_filed_not_shown(self):
        gui_info_panel_send_message(1001, "ambient chatter")
        self.assertEqual(len(self.log()), 1, "filed in the log")
        self.assertEqual(self.live(), [], "not queued as a live card")
        self.assertEqual(self.panel.tabs, [], "did not steal the tab")

    def test_notify_true_interrupts(self):
        gui_info_panel_send_message(1001, "look now", notify=True)
        self.assertEqual(len(self.live()), 1)
        self.assertEqual(self.panel.tabs, ["message"])
        self.assertEqual(len(self.log()), 1, "an interrupt is still logged")

    def test_button_card_always_interrupts(self):
        # a progression gate: the mission awaits the press
        prom = gui_info_panel_send_message(1001, "decide", button="OK")
        self.assertIsNotNone(prom)
        self.assertEqual(len(self.live()), 1)
        self.assertEqual(self.panel.tabs, ["message"])

    def test_button_card_interrupts_even_when_notify_false(self):
        gui_info_panel_send_message(1001, "decide", button="OK", notify=False)
        self.assertEqual(len(self.live()), 1, "notify=False cannot hide a gate")
        self.assertEqual(self.panel.tabs, ["message"])

    def test_history_false_skips_the_log(self):
        gui_info_panel_send_message(1001, "transient", notify=True, history=False)
        self.assertEqual(self.log(), [])
        self.assertEqual(len(self.live()), 1)

    def test_log_keeps_depth_and_caps(self):
        for i in range(INFO_PANEL_LOG_MAX + 5):
            gui_info_panel_send_message(1001, f"line {i}")
        entries = self.log()
        self.assertEqual(len(entries), INFO_PANEL_LOG_MAX)
        self.assertEqual(entries[-1]["message"], f"line {INFO_PANEL_LOG_MAX + 4}")

    def test_log_is_deeper_than_the_old_nine(self):
        self.assertGreater(INFO_PANEL_LOG_MAX, 9)

    def test_a_quiet_card_still_reaches_the_log_of_every_target(self):
        gui_info_panel_send_message({1001}, "to a set")
        self.assertEqual(len(self.log()), 1)


class TestCommsInfoCardPassesNotify(InfoPanelBase):
    def test_card_defaults_to_quiet(self):
        from sbs_utils.procedural.comms import comms_info_card
        comms_info_card(1001, "chatter", title="Clan")
        self.assertEqual(self.panel.tabs, [])
        self.assertEqual(len(self.log()), 1)

    def test_card_notify_true_interrupts(self):
        from sbs_utils.procedural.comms import comms_info_card
        comms_info_card(1001, "dispatch", title="Command", notify=True)
        self.assertEqual(self.panel.tabs, ["message"])


class TestAnnounceLeavesTheInterruptToTheOverlay(InfoPanelBase):
    def test_announce_alert_files_the_card_without_stealing_the_tab(self):
        from sbs_utils.procedural.announce import announce
        announce("Raiders inbound", title="TSN Command", level="alert", to=1001)
        # the banner is the attention half...
        self.assertIn("top_banner", self.page.overlays.slots)
        # ...so the record half stays quiet
        self.assertEqual(self.panel.tabs, [])
        self.assertEqual(len(self.log()), 1)


if __name__ == "__main__":
    unittest.main()
