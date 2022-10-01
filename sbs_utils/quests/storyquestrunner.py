from .questrunner import PollResults, QuestRunner, QuestRuntimeNode, QuestRunner, QuestAsync
from .quest import Quest
import sbs
from ..gui import FakeEvent, Gui, Page

from ..pages import layout

from .errorpage import ErrorPage
from .storyquest import AppendText, StoryQuest, Choices, Text, Blank, Ship, Face, Button, Row, Section, Area, Refresh
import traceback
from .sbsquestrunner import SbsQuestRunner

class StoryRuntimeNode(QuestRuntimeNode):
    def on_message(self, sim, event):
        pass

class FaceRunner(StoryRuntimeNode):
    def enter(self, quest:Quest, thread:QuestAsync, node: Face):
        tag = thread.main.page.get_tag()
        face = node.face
        if node.code:
            face = thread.eval_code(node.code)
        if face is not None:
            thread.main.page.add_content(layout.Face(face, tag), self)

    def poll(self, quest, thread, node:Face):
        return PollResults.OK_ADVANCE_TRUE

class RefreshRunner(StoryRuntimeNode):
    def enter(self, quest:Quest, thread:QuestAsync, node: Refresh):
        thread.main.quest.refresh_runners(thread.main, node.label)
        

class ShipRunner(StoryRuntimeNode):
    def enter(self, quest:Quest, thread:QuestAsync, node: Ship):
        tag = thread.main.page.get_tag()
        thread.main.page.add_content(layout.Ship(node.ship, tag), self)


class TextRunner(StoryRuntimeNode):
    current = None
    def enter(self, quest:Quest, thread:QuestAsync, node: Text):
        tag = thread.main.page.get_tag()
        msg = ""
        value = True
        if node.code is not None:
            value = thread.eval_code(node.code)
        if value:
            msg = thread.format_string(node.message)
            self.layout_text = layout.Text(msg, tag)
            TextRunner.current = self
            thread.main.page.add_content(self.layout_text, self)

class AppendTextRunner(StoryRuntimeNode):
    def enter(self, quest:Quest, thread:QuestAsync, node: AppendText):
        msg = ""
        value = True
        if node.code is not None:
            value = thread.eval_code(node.code)
        if value:
            msg = thread.format_string(node.message)
            text = TextRunner.current
            if text is not None:
                text.layout_text.message += '\n'
                text.layout_text.message += msg
        



class ButtonRunner(StoryRuntimeNode):
    def enter(self, quest:Quest, thread:QuestAsync, node: Button):
        self.tag = thread.main.page.get_tag()
        value = True
        if node.code is not None:
            value = self.thread.eval_code(node.code)
        if value and node.should_present(thread.main.client_id):
            thread.main.page.add_content(layout.Button(node.message, self.tag), self)
        self.button_node = node
        self.thread = thread
    def on_message(self, sim, event):
        if event.sub_tag == self.tag:
            if self.button_node.jump:
                if self.button_node.push:
                    self.thread.push_label(self.button_node.jump)
                elif self.button_node.pop:
                    self.thread.pop_label()
                else:
                    self.thread.jump(self.button_node.jump)
 

class RowRunner(StoryRuntimeNode):
    def enter(self, quest:Quest, thread:QuestAsync, node: Row):
        thread.main.page.add_row()
        

class BlankRunner(StoryRuntimeNode):
    def enter(self, quest:Quest, thread:QuestAsync, node: Blank):
        tag = thread.main.page.get_tag()
        thread.main.page.add_content(layout.Separate(), self)

class SectionRunner(StoryRuntimeNode):
    def enter(self, quest:Quest, thread:QuestAsync, node: Section):
        thread.main.page.add_section()

class AreaRunner(StoryRuntimeNode):
    def enter(self, quest:Quest, thread:QuestAsync, node: Area):
        thread.main.page.set_section_size(node.left, node.top, node.right, node.bottom)


class ChoicesRunner(StoryRuntimeNode):
    def enter(self, quest:Quest, thread:QuestAsync, node: Choices):
        
        self.timeout = node.minutes*60+node.seconds
        if self.timeout == 0:
            self.timeout = None

        button_layout = layout.Layout(None, 30,95,90,100)

        active = 0
        row: Row
        layout_row = layout.Row()

        for button in node.buttons:
            match button.__class__.__name__:
                case "Button":
                    value = True
                    if button.code is not None:
                        value = thread.eval_code(button.code)
                    if value and button.should_present(thread.main.client_id):
                        runner = ChoiceButtonRunner()
                        runner.enter(quest, thread, button)
                        layout_button = layout.Button(button.message, runner.tag)
                        layout_row.add(layout_button)
                        thread.main.page.add_tag(runner)
                        active += 1
                case "Separator":
                    # Handle face expression
                    layout_row.add(layout.Separate())

        if active>0:    
            button_layout.add(layout_row)
            thread.main.page.set_button_layout(button_layout)
        else:
            thread.main.page.set_button_layout(None)

        self.active = active
        self.buttons = node.buttons
        self.button = None


    def poll(self, quest:Quest, thread:QuestAsync, node: Choices):
        if self.active==0 and self.timeout is None:
            return PollResults.OK_ADVANCE_TRUE

        if self.button is not None:
            button = self.buttons[self.button]
            if button.push:
                thread.push_label(button)
            elif button.pop:
                thread.pop_label()
            else:
                button.jump(button.jump)
            return PollResults.OK_JUMP

        if self.timeout:
            self.timeout -= 1
            if self.timeout <= 0:
                if node.time_push:
                    thread.push_label(node.time_jump)
                elif node.time_pop:
                    thread.pop_label()
                else:
                    thread.jump(node.time_jump)
                return PollResults.OK_JUMP
            else:
                PollResults.OK_ADVANCE_FALSE

        return PollResults.OK_RUN_AGAIN


class ChoiceButtonRunner(StoryRuntimeNode):
    def enter(self, quest:Quest, thread:QuestAsync, node: Button):
        self.tag = thread.main.page.get_tag()
        self.thread = thread
        self.button_node = node

    def on_message(self, sim, event):
        if event.sub_tag == self.tag:
            self.button_node.visit(event.client_id)
            if self.button_node.jump:
                if self.button_node.push:
                    self.thread.push_label(self.button_node.jump)
                else:
                    self.thread.jump(self.button_node.jump)
            elif  self.button_node.pop:
                self.thread.pop_label()


over =     {
    "Row": RowRunner,
    "Text": TextRunner,
    "AppendText": AppendTextRunner,
    "Face": FaceRunner,
    "Ship": ShipRunner,
    "Button": ButtonRunner,
    "Blank": BlankRunner,
    "Choices": ChoicesRunner,
    "Section": SectionRunner,
    "Area": AreaRunner,
    "Refresh": RefreshRunner

}

class StoryRunner(SbsQuestRunner):
    def __init__(self, quest: Quest, overrides=None):
        if overrides:
            super().__init__(quest, over|overrides)
        else:
            super().__init__(quest,  over)
        self.sim = None
        self.paint_refresh = False

    def run(self, sim, page, label="main", inputs=None):
        self.sim = sim
        self.page = page
        inputs = inputs if inputs else {}
        super().start_thread( label, inputs)

    def tick(self, sim, client_id):
        self.sim = sim
        self.client_id = client_id
        self.vars['sim'] = sim
        return super().tick(sim)

    def refresh(self, label):
        for thread in self.threads:
            if label == thread.active_label:
                thread.jump(thread.active_label)
                self.tick(self.sim, self.client_id)
                Gui.dirty(self.client_id)

    def runtime_error(self, message):
        if self.sim:
            sbs.pause_sim()
        err = traceback.format_exc()
        if not err.startswith("NoneType"):
            message += str(err)
            self.errors.append(message)
        
        

class StoryPage(Page):
    tag = 0
    def __init__(self) -> None:
        self.gui_state = 'repaint'
        self.story_runner = None
        self.layouts = []
        self.pending_layouts = None
        self.pending_row = None
        self.pending_tag_map = {}
        self.tag_map = {}
        self.aspect_ratio = sbs.vec2(1920,1071)
        self.client_id = None
        self.sim = None
        #self.tag = 0
        self.errors = []
                    

    def run(self, sim, story_script):
        story = StoryQuest()
        errors = story.compile(story_script)
        if len(errors) > 0:
            message = "Compile errors\n".join(errors)
            self.errors.append(message)
            self.errors.extend(errors)
        else:    
            self.story_runner = StoryRunner(story)
            self.story_runner.run(sim, self)

    def swap_layout(self):
        self.layouts = self.pending_layouts
        self.tag_map = self.pending_tag_map
        self.tag = 0
        if self.layouts:
            for layout in self.layouts:
                layout.calc()
            self.pending_layouts = None
            self.pending_row = None
            self.pending_tag_map = {}
        self.gui_state = 'repaint'

    def get_tag(self):
        self.tag += 1
        return str(self.tag)

    def add_row(self):
        if not self.pending_layouts:
            self.pending_layouts = [layout.Layout(None, 20,10, 100, 90)]
        if self.pending_row:
            self.pending_layouts[-1].add(self.pending_row)
        if self.pending_tag_map is None:
            self.pending_tag_map = {}
        self.pending_row = layout.Row()

    def add_tag(self, layout_item):
        if self.pending_tag_map is not None:
            if hasattr(layout_item, 'tag'):
                #print(f"TAGGED: {layout_item.__class__.__name__} {layout_item.tag}")
                self.pending_tag_map[layout_item.tag] = layout_item

    def add_content(self, layout_item, runner):
        if self.pending_layouts is None:
            self.add_row()

        self.add_tag(runner)
        self.pending_row.add(layout_item)

    
    def add_section(self):
        if not self.pending_layouts:
            self.pending_layouts = [layout.Layout(None, 20,10, 100, 90)]
        else:
            self.add_row()
            self.pending_layouts.append(layout.Layout(None, 20,10, 100, 90))

    def set_section_size(self, left, top, right, bottom):
        #print( f"SIZE: {left} {top} {right} {bottom}")
        if not self.pending_layouts:
            self.add_row()
        l = self.pending_layouts[-1]
        l.set_size(left,top, right, bottom)
    

    def set_button_layout(self, layout):
        if self.pending_row and self.pending_layouts:
            if self.pending_row:
                self.pending_layouts[-1].add(self.pending_row)
            if layout:
                self.pending_layouts.append(layout)
            self.swap_layout()
    
    def present(self, sim, event):
        """ Present the gui """
        if self.story_runner is not None:
            if self.story_runner.paint_refresh:
                if self.gui_state != "repaint":  
                    self.gui_state = "refresh"
                self.story_runner.paint_refresh = False
            if not self.story_runner.tick(sim, event.client_id):
                #self.story_runner.quest.remove_runner(self)
                Gui.pop(sim, event.client_id)
                return
        elif len(self.errors) > 0:
            #errors = self.errors.reverse()
            message = "Compile errors\n".join(self.errors)
            sbs.send_gui_clear(event.client_id)
            sbs.send_gui_text(event.client_id, message, "error", 30,20,100,100)
            self.gui_state = "errors"


        
        sz = sbs.get_screen_size()
        if sz is not None and sz.y != 0:
            aspect_ratio = sz
            if (self.aspect_ratio.x != aspect_ratio.x or 
                self.aspect_ratio.y != aspect_ratio.y):
                self.aspect_ratio = sz
                for layout in self.layouts:
                    layout.aspect_ratio = aspect_ratio
                    layout.calc()
                self.gui_state = 'repaint'

        
        match self.gui_state:
            case  "repaint":
                sbs.send_gui_clear(event.client_id)
                # Setting this to a state we don't process
                # keeps the existing GUI displayed

                for layout in self.layouts:
                    layout.present(sim,event)
                
                self.gui_state = "presenting"
            case  "refresh":
                for layout in self.layouts:
                    layout.present(sim,event)
                self.gui_state = "presenting"


    def on_message(self, sim, event):
        message_tag = event.sub_tag
        runner = self.tag_map.get(message_tag)
        if runner:
            runner.on_message(sim, event)
            self.present(sim, event)



