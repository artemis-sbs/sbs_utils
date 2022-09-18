from .quest import Quest, QuestRunner, PollResults, QuestRuntimeNode, QuestNode, Comms, Tell, Near,QuestThread
import sbs
from .spaceobject import SpaceObject
from .consoledispatcher import ConsoleDispatcher

class TellRunner(QuestRuntimeNode):
    def enter(self, quest:Quest, thread:QuestThread, node: QuestNode):
        to_so:SpaceObject = thread.main.inputs.get(node.to_tag)
        self.face = ""
        self.title = ""
        if to_so:
            self.to_id = to_so.get_id()
            print('TELL TO')
        from_so:SpaceObject = thread.main.inputs.get(node.from_tag)
        if from_so:
            self.from_id = from_so.get_id()
            self.title = from_so.comm_id(thread.main.sim)
            print('TELL FROM')

    def poll(self, quest:Quest, thread:QuestThread, node: QuestNode):
        msg = node.message.format(**thread.main.vars)
        

        sbs.send_comms_message_to_player_ship(
            self.to_id,
            self.from_id,
            "white",
            self.face, self.title, msg)
        return PollResults.OK_ADVANCE_TRUE

class CommsRunner(QuestRuntimeNode):
    def enter(self, quest:Quest, thread:QuestThread, node: QuestNode):
        self.timeout = node.minutes*60+node.seconds
        if self.timeout == 0:
            self.timeout = None

        self.tag = None
        self.buttons = node.buttons
        self.button = None
        

        to_so:SpaceObject = thread.main.inputs.get(node.to_tag)
        if to_so:
            self.to_id = to_so.get_id()
        from_so:SpaceObject = thread.main.inputs.get(node.from_tag)
        if from_so:
            self.from_id = from_so.get_id()
            self.comms_id = from_so.comm_id(thread.main.sim)
            ConsoleDispatcher.add_select(self.from_id, 'comms_targetUID', self.comms_selected)
            ConsoleDispatcher.add_message(self.from_id, 'comms_targetUID', self.comms_message)
            # from_so.face_desc
            

    def comms_selected(self, sim, an_id, event):
        from_so = SpaceObject.get(event.selected_id)
        sbs.send_comms_selection_info(self.to_id, "", "green", from_so.comm_id(sim))
        for i, button in enumerate(self.buttons):
            sbs.send_comms_button_info(self.to_id, "blue", button.message, f"{i}")

    def comms_message(self, sim, message, an_id, event):
        self.button = int(event.sub_tag)

    def leave(self, quest:Quest, thread:QuestThread, node: QuestNode):
        sbs.send_comms_selection_info(self.to_id, "", "green", self.comms_id)
        ConsoleDispatcher.remove_select(self.from_id, 'comms_targetUID')
        ConsoleDispatcher.remove_message(self.from_id, 'comms_targetUID')

    def poll(self, quest:Quest, thread:QuestThread, node: QuestNode):

        if len(node.buttons)==0:
            # clear the comms buttons
            return PollResults.OK_ADVANCE_TRUE

        if self.button is not None:
            jump = self.buttons[self.button].jump 
            thread.jump(jump)
            return PollResults.OK_JUMP

        if self.timeout:
            self.timeout -= 1
            if self.timeout <= 0:
                thread.jump(node.time_jump)
                return PollResults.OK_JUMP
            else:
                PollResults.OK_ADVANCE_FALSE

        return PollResults.OK_RUN_AGAIN



class NearRunner(QuestRuntimeNode):
    def enter(self, quest:Quest, thread:QuestThread, node: QuestNode):
        self.timeout = node.minutes*60+node.seconds
        if self.timeout==0:
            self.timeout = None
        self.tag = None

        to_so:SpaceObject = thread.main.inputs.get(node.to_tag)
        if to_so:
            self.to_id = to_so.get_id()
        from_so:SpaceObject = thread.main.inputs.get(node.from_tag)
        if from_so:
            self.from_id = from_so.get_id()

    def poll(self, quest:Quest, thread:QuestThread, node: Near):
        # Need to check the distance
        dist = sbs.distance_id(self.to_id, self.from_id)
        if dist <= node.distance:
            if node.jump:
                thread.jump(node.jump)
                return PollResults.OK_JUMP
            else:
                return PollResults.OK_ADVANCE_TRUE

        if self.timeout is not None:
            self.timeout -= 1
            if self.timeout <= 0:
                thread.jump(node.time_jump)
                return PollResults.OK_JUMP
            else:
                PollResults.OK_ADVANCE_FALSE

        return PollResults.OK_RUN_AGAIN

over =     {
        "Comms": CommsRunner,
        "Tell": TellRunner,
        "Near": NearRunner
    }

class SbsQuestRunner(QuestRunner):
    def __init__(self, quest: Quest, inputs, overrides=None):
        if overrides:
            super().__init__(quest, inputs, over|overrides)
        else:
            super().__init__(quest, inputs, over)

    def start(self, sim, label="main"):
        print("jump: {sim}")
        self.sim = sim
        super().start(label)

    def tick(self, sim):
        self.sim = sim
        super().tick()

