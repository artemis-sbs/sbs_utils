from .quest import Quest, QuestRunner, PollResults, QuestRuntimeNode, QuestNode, Comms, Tell, Near,QuestAsync, Target
import sbs
from ..spaceobject import SpaceObject
from ..consoledispatcher import ConsoleDispatcher
from ..gui import Gui, Page
import traceback

class TellRunner(QuestRuntimeNode):
    def enter(self, quest:Quest, thread:QuestAsync, node: QuestNode):
        to_so:SpaceObject = thread.inputs.get(node.to_tag)
        self.face = ""
        self.title = ""
        if to_so:
            self.to_id = to_so.get_id()
        else:
            thread.runtime_error("Tell has invalid TO")            
        from_so:SpaceObject = thread.inputs.get(node.from_tag)
        if from_so:
            self.from_id = from_so.get_id()
            self.title = from_so.comm_id(thread.main.sim)
        else:
            thread.runtime_error("Tell has invalid from")            

    def poll(self, quest:Quest, thread:QuestAsync, node: QuestNode):

        if self.to_id and self.from_id:
            msg = node.message.format(**thread.main.vars)
            sbs.send_comms_message_to_player_ship(
                self.to_id,
                self.from_id,
                "white",
                self.face, self.title, msg)
            return PollResults.OK_ADVANCE_TRUE
        else:
            PollResults.OK_ADVANCE_FALSE

class CommsRunner(QuestRuntimeNode):
    def enter(self, quest:Quest, thread:QuestAsync, node: QuestNode):
        self.timeout = node.minutes*60+node.seconds
        if self.timeout == 0:
            self.timeout = None

        self.tag = None
        self.buttons = node.buttons
        self.button = None
        

        to_so:SpaceObject = thread.inputs.get(node.to_tag)
        if to_so:
            self.to_id = to_so.get_id()
        from_so:SpaceObject = thread.inputs.get(node.from_tag)
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

    def leave(self, quest:Quest, thread:QuestAsync, node: QuestNode):
        sbs.send_comms_selection_info(self.to_id, "", "green", self.comms_id)
        ConsoleDispatcher.remove_select(self.from_id, 'comms_targetUID')
        ConsoleDispatcher.remove_message(self.from_id, 'comms_targetUID')

    def poll(self, quest:Quest, thread:QuestAsync, node: QuestNode):

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

class TargetRunner(QuestRuntimeNode):
    def enter(self, quest:Quest, thread:QuestAsync, node: Target):
        to_so:SpaceObject = thread.inputs.get(node.to_tag)
        self.to_id = to_so.get_id() if to_so else None
        from_so:SpaceObject = thread.inputs.get(node.from_tag)
        self.from_id = from_so.get_id() if from_so else None


    def poll(self, quest, thread, node:Target):
        if self.to_id:
            print(f"targeting {self.from_id} {self.to_id}")
            obj:SpaceObject = SpaceObject.get(self.from_id)
            obj.target(thread.main.sim, self.to_id, not node.approach)
        else:
            obj:SpaceObject = SpaceObject.get(self.from_id)
            obj.clear_target(thread.main.sim)
            print(f"clear targeting {self.from_id}")

        return PollResults.OK_ADVANCE_TRUE


class NearRunner(QuestRuntimeNode):
    def enter(self, quest:Quest, thread:QuestAsync, node: QuestNode):
        self.timeout = node.minutes*60+node.seconds
        if self.timeout==0:
            self.timeout = None
        self.tag = None

        to_so:SpaceObject = thread.inputs.get(node.to_tag)
        if to_so:
            self.to_id = to_so.get_id()
        from_so:SpaceObject = thread.inputs.get(node.from_tag)
        if from_so:
            self.from_id = from_so.get_id()

    def poll(self, quest:Quest, thread:QuestAsync, node: Near):
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

class ErrorPage(Page):
    def __init__(self, msg) -> None:
        self.gui_state = 'show'
        self.message = msg

    def present(self, sim, event):
        match self.gui_state:
            case  "sim_on":
                self.gui_state = "blank"
                sbs.send_gui_clear(event.client_id)

            case  "show":
                sbs.send_gui_clear(event.client_id)
                # Setting this to a state we don't process
                # keeps the existing GUI displayed
                self.gui_state = "presenting"
                sbs.send_gui_text(
                    event.client_id, f"{self.message}", "text", 25, 20, 99, 90)
                sbs.send_gui_button(event.client_id, "back", "back", 80, 90, 99, 94)
                sbs.send_gui_button(event.client_id, "Resume Mission", "resume", 80, 95, 99, 99)

    def on_message(self, sim, event):
        match event.sub_tag:
            case "back":
                Gui.pop(sim, event.client_id)

            case "resume":
                Gui.pop(sim, event.client_id)
                sbs.resume_sim()


over =     {
        "Comms": CommsRunner,
        "Tell": TellRunner,
        "Near": NearRunner,
        "Target": TargetRunner
    }

class SbsQuestRunner(QuestRunner):
    def __init__(self, quest: Quest, overrides=None):
        if overrides:
            super().__init__(quest, over|overrides)
        else:
            super().__init__(quest,  over)

    def run(self, sim, label="main", inputs=None):
        self.sim = sim
        inputs = inputs if inputs else {}
        super().start_thread( label, inputs)

    def tick(self, sim):
        self.sim = sim
        super().tick()

    def runtime_error(self, message):
        sbs.pause_sim()
        message += traceback.format_exc()
        Gui.push(self.sim, 0, ErrorPage(message))

