from sbs_utils.quests.storyquest import Quest
from sbs_utils.quests.questrunner import PollResults, QuestAsync, QuestRuntimeNode, QuestRunner
from sbs_utils.quests.storyquest import StoryQuest, Face, Ship, Text, Button, Row, Choices, Section, Blank, Area
import os

class StoryRuntimeNode(QuestRuntimeNode):
    def on_message(sim, message, an_id, event):
        pass

class FaceRunner(StoryRuntimeNode):
    def enter(self, quest:Quest, thread:QuestAsync, node: Face):
        tag = thread.main.page.get_tag()
        face = node.face
        if node.code:
            face = thread.eval_code(node.code)

        

class ShipRunner(StoryRuntimeNode):
    def enter(self, quest:Quest, thread:QuestAsync, node: Ship):
        pass


class TextRunner(StoryRuntimeNode):
    def enter(self, quest:Quest, thread:QuestAsync, node: Text):
        pass


class ButtonRunner(StoryRuntimeNode):
    def enter(self, quest:Quest, thread:QuestAsync, node: Button):
        pass

class RowRunner(StoryRuntimeNode):
    def enter(self, quest:Quest, thread:QuestAsync, node: Row):
        pass
        

class SeparatorRunner(StoryRuntimeNode):
    def enter(self, quest:Quest, thread:QuestAsync, node: Blank):
        pass

class SectionRunner(StoryRuntimeNode):
    def enter(self, quest:Quest, thread:QuestAsync, node: Section):
        pass

class SizeRunner(StoryRuntimeNode):
    def enter(self, quest:Quest, thread:QuestAsync, node: Area):
        pass


class ChoicesRunner(StoryRuntimeNode):
    def enter(self, quest:Quest, thread:QuestAsync, node: Choices):
        pass


class FakeObject:
    def __init__(self, name):
        self.name = name



over =     {
    "Row": RowRunner,
    "Text": TextRunner,
    "Face": FaceRunner,
    "Ship": ShipRunner,
    "Button": ButtonRunner,
    "Separator": SeparatorRunner,
    "Choices": ChoicesRunner,
    "Section": SectionRunner,
    "Size": SizeRunner
}


basedir = os.path.dirname(os.path.realpath(__file__))
files = ["story_gui.story"]

for file in files:
    with open(os.path.join(basedir, './tests/quests', file)) as f:
        content = f.read()
        q = StoryQuest(content)
    
        run = QuestRunner(q, over)
        run.start_thread(inputs={"player": FakeObject("fred"), "ship": FakeObject("wilma")})
        run2 = QuestRunner(q, over)
        run2.start_thread(inputs={"player": FakeObject("fred"), "ship": FakeObject("wilma")})
        while run.tick() and run2.tick():
            pass
        run.start_thread(inputs={"player": FakeObject("fred"), "ship": FakeObject("wilma")})
        while not run.tick():
            pass

