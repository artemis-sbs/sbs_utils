"""A quest completed by another quest's `Then: signal` announces itself - after that one.

Seen in the engine (author course 3, lesson 5): Science read the suit tags, "Six Names"
completed, and its `Then: signal names_known` completed "Account for the Crew" (the Tasks
app showed it Done) - but Helm's strip only ever read "Quest complete: Six Names".

The cause is the ORDER. A signal's route is ticked as it is emitted, so the `Then:` signal
completed the second quest INSIDE the first one's `quest_mark_complete` - and the first
announced itself afterwards. Both lines went out, the second quest's first, and the strip
shows the newest one. Driven here through a real `//shared/signal/quest_signal` route (the
LegendaryMissions quest driver's, verbatim), so the inner completion happens exactly where
the engine makes it happen.

    python -m unittest tests.test_quest_then_signal_announce
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest

import cosmos_dev.mock.sbs as sbs
from sbs_utils.mast.maststory import MastStory
from sbs_utils.mast_sbs import story_nodes  # noqa: F401  (registers route/gui nodes)
from sbs_utils.mast_sbs.maststorypage import StoryPage
from sbs_utils.mast.mastscheduler import MastScheduler
from sbs_utils.agent import Agent, clear_shared
from sbs_utils.gui import Gui
from sbs_utils.helpers import FrameContext, Context, FakeEvent, props_display_text
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.procedural import quest_driver as QD
from sbs_utils.procedural.amd_quest import amd_quest_data
from sbs_utils.procedural.quest import QuestState, quest_get_state, document_get_amd_file

CID = 0   # the server console: //shared/signal routes run there

QUESTS = """# [Account for the Crew](account)
---
Scope: shared
Starts when: at once
Done when: signal names_known
---
Somebody crewed that ship. Command wants names.

# [Six Names](six_names)
---
Scope: shared
Starts when: at once
Done when: signal names_read
Then: signal names_known
---
Six suits on their hooks, and nobody in them.
"""

STORY = """== qts_screen ==
    gui_section("area: 5,5,95,95;")
    gui_row()
    b = gui_button("Read the tags")
    on gui_message(b):
        signal_emit("quest_signal", {"SIGNAL_NAME": "names_read"})
    await gui()

//shared/signal/quest_signal
    default SIGNAL_NAME = None
    quest_on_signal(SIGNAL_NAME)
    ->END
"""


class QtsPage(StoryPage):
    story = None


class ThenSignalAnnounceTests(unittest.TestCase):
    def setUp(self):
        Gui.clients = {}
        Gui.widget_list_sent = {}
        sbs.create_new_sim()
        sbs.resume_sim()
        SpaceObject.clear()
        clear_shared()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent(0, "test"))
        self.lines = []
        self._bc = QD.comms_broadcast
        QD.comms_broadcast = lambda to, msg, *a, **k: self.lines.append(str(msg))
        QD.quest_grant_amd(Agent.SHARED_ID, document_get_amd_file(
            None, "d", content=QUESTS, data_parser=amd_quest_data))
        story = MastStory()
        errors = story.compile(STORY, "qts", story)
        self.assertEqual(errors, [], f"compile errors: {errors}")
        QtsPage.story = story
        FrameContext.mast = story
        self.errors = []
        self._rte = MastScheduler.on_runtime_error
        MastScheduler.on_runtime_error = self.errors.append
        self.page = QtsPage()
        Gui.push(CID, self.page)
        self.present(3)

    def tearDown(self):
        QD.comms_broadcast = self._bc
        MastScheduler.on_runtime_error = self._rte
        Gui.clients = {}
        Gui.widget_list_sent = {}
        QtsPage.story = None
        FrameContext.task = None
        FrameContext.page = None
        FrameContext.mast = None
        FrameContext.context = None

    def present(self, n=1):
        for _ in range(n):
            sbs.sim._time_tick_counter += 30
            self.page.present(FakeEvent(CID, "gui_present"))

    def press(self, text):
        for tag, entry in list(self.page.tag_map.items()):
            item = entry[0] if isinstance(entry, tuple) and entry else entry
            if (props_display_text(getattr(item, "message", None)) or "").strip() == text:
                FrameContext.context = Context(sbs.sim, sbs, FakeEvent(CID, "gui_message"))
                Gui.on_message(FakeEvent(client_id=CID, tag="gui_message", sub_tag=tag))
                self.present(1)
                return
        self.fail(f"no button {text!r}")

    def completions(self):
        return [ln for ln in self.lines if "complete:" in ln]

    def test_both_quests_complete(self):
        self.press("Read the tags")
        self.assertEqual(self.errors, [])
        self.assertEqual(quest_get_state(Agent.SHARED_ID, "six_names"), QuestState.COMPLETE)
        self.assertEqual(quest_get_state(Agent.SHARED_ID, "account"), QuestState.COMPLETE)

    def test_both_announce_once_in_the_order_they_happened(self):
        self.press("Read the tags")
        self.assertEqual(self.completions(),
                         ["Quest complete: Six Names",
                          "Quest complete: Account for the Crew"])


if __name__ == "__main__":
    unittest.main()
