"""
The gui module

This module exposes the gui function

The gui function is used to present the queued gui layout.

gui() returns  Promise and therefore an await should be used to allow the gui to run. 


=== ":mast-icon: MAST"
    ```
    gui_text("Hello, World")
    await gui()

    ```

Example:
    To insert a blank part of the layout just call gui_blank::

        gui_blank()

    Proving a count will allow inserting multiple blanks::

        gui_blank(4)

    One use of blanks it to help center an element but also adding space::

        gui_blank()
        gui_icon(...)
        gui_blank()
"""
from ...mast.mast import Scope

from ...helpers import FrameContext

from ...futures import AwaitBlockPromise
from ...gui import get_client_aspect_ratio
from ..style import apply_control_styles
from ...mast.pollresults import PollResults

from ..execution import task_all
from .change import ChangeTrigger
from ...agent import Agent

import re


def gui_screen_size(client_id):
    return get_client_aspect_ratio(client_id)


class ChoiceButtonRuntimeNode:
    def __init__(self, promise, button, tag):
        self.promise = promise
        self.button = button
        self.tag = tag
                
    def on_message(self, event):
        #
        # The 'right' page already filtered 
        # event to know it is for this client
        #
        if event.sub_tag == self.tag:
            self.promise.press_button(self.button)

import re
class ButtonPromise(AwaitBlockPromise):
    focus_rule = re.compile(r'focus')
    disconnect_rule = re.compile(r'disconnect')
    fail_rule = re.compile(r'fail')

    navigation_map = {}

    def __init__(self, path, task, timeout=None) -> None:
        super().__init__(timeout)

        self.path = path if path is not None else ""
        self.path_root = "gui"
        self.buttons = []
        self.nav_buttons = []
        self.nav_button_map = {}
        self.inlines = []
        self.button = None
        self.var = None
        self.task = task
        self.disconnect_label = None
        self.on_change = None
        self.focus_label = None
        self.run_focus = False
        self.running_button = None
        self.sub_task = None
        self.nav_sub_task_promise = None
        self.event = None 
        
    def initial_poll(self):
        if self._initial_poll:
            return
        # Will Build buttons
        self.expand_inlines()
        #self.show_buttons()
        super().initial_poll()

    def set_path(self, path):
        if path is None:
            path = self.path_root
        if path.startswith("//"):
            path = path[2:]
        if path.startswith(self.path_root):
            # typically this is overridden
            self.path = path
            self.show_buttons()
        else:

            print(f"possible wrong path SET {self.path_root} path= {path}")


    def check_for_button_done(self):
        #
        # THIS sets the promise to finish 
        # after you let the button process
        # science will override this to 
        # keep going until all scanned
        #
        # if self.running_button:
        #    self.set_result(self.running_button)
        pass

    def pressed_set_values(self):
        pass

    def pressed_test(self):
        return True


    def cancel(self, msg=None):
        if self.nav_sub_task_promise is not None:
            self.nav_sub_task_promise.cancel()
            self.nav_sub_task_promise = None

    def poll(self):
        res = super().poll()
        if res != PollResults.OK_RUN_AGAIN and self.done():
            return res
        
        if self.sub_task is not None:
            self.sub_task.poll()
            if self.sub_task.done:
                self.show_buttons()
                self.sub_task= None
            else:
                return PollResults.OK_RUN_AGAIN

        if not self.pressed_test():
            # If the test fails, this is no longer needed
            self.task.end()
            
            
            

        self.check_for_button_done()

        task = self.task
        if self.task is None:
            self.task = self.page.gui_task
            # First run could have no gui_task
            if self.task is None:
                self.task = FrameContext.task

        if self.button is not None:
            if self.var:
                task.set_value_keep_scope(self.var, self.button.index)
             
            # self.button.node.visit(self.button.client_id)
            # button = self.buttons[self.button.index]
            button = self.button
            # if button.for_name:
            #     task.set_value(button.for_name, button.data, Scope.TEMP)

            self.pressed_set_values()
            task.set_value("BUTTON_PROMISE", self, Scope.TEMP)

            #
            # If the button doesn't jump, make sure the 
            # promise has a chance to finish
            #
            self.running_button = self.button
            self.button = None
            #
            # Code to run the button is now with the button 
            # so the code is closer to the data
            #
            if self.running_button.path is not None:
                self.set_path(self.running_button.path)
                self.running_button = None
                return PollResults.OK_JUMP
            else:   
                sub_task = self.running_button.run(self.task, self)
                if sub_task is not None:
                    self.sub_task = sub_task
            return PollResults.OK_JUMP

        if self.disconnect_label is not None:
            page = task.main.page
            if page is not None and page.disconnected:
                # Await use a jump back to the await, so jump here is OK
                task.jump(task.active_label,self.disconnect_label.loc+1)
                #return PollResults.OK_JUMP
                self.set_result(True)
                return PollResults.OK_JUMP

        if self.on_change:
            for change in self.on_change:
                if change.test():
                    # Await use a jump back to the await, so jump here is OK
                    self.task.jump(change.label,change.node.loc+1)
                    return PollResults.OK_JUMP
                    
        if self.focus_label and self.run_focus:
            self.run_focus = False
            # Await use a jump back to the await, so jump here is OK
            self.task.jump(self.task.active_label,self.focus_label.loc+1)
            return PollResults.OK_JUMP

        return PollResults.OK_RUN_AGAIN

    def press_button(self, button):
        self.button = button
        self.poll()

    def expand_button(self, button):
        buttons = []
        return buttons

    def get_expanded_buttons(self):
        buttons = []
        #
        # Note: Always use clones in layouts
        # So we can have access to the layout item
        #
        # Expand all the 'for' buttons
        for button in self.buttons:
            if button.__class__.__name__ != "Button":
                # This could mess with order in gui?
                # if their are separators?
                buttons.append(button)
            else:
                buttons.append(button.clone())

            # else:
            #     buttons.extend(self.expand_button(button))
        self.build_navigation_buttons()
        buttons.extend(self.nav_buttons)
        i = 0
        order_weights = {}
        for button in buttons:
            weight = getattr(button, "weight", 0)
            order_weights[button] = weight * 1000 + i
            i +=1 
        
        def sort_by_weight(button):
            weight = order_weights.get(button, -1)
            #print(f"Button Promise {button.raw_weight} {weight} {button.message}")
            return weight

        buttons.sort(key=sort_by_weight)
        return buttons
    
    
    def expand_inline(self, inline):
        if inline.inline is  None:
            return
        # Handle =disconnect:
        if ButtonPromise.disconnect_rule.match(inline.inline):
            self.disconnect_label = inline
        # Handle focus
        if ButtonPromise.focus_rule.match(inline.inline):
            self.focus_label = inline
        # Handle Fail () maybe only for behaviors?
        if ButtonPromise.fail_rule.match(inline.inline):
            self.fail_label = inline
        # Handle change
        if inline.inline.startswith("change"):
            if self.on_change is None:
                self.on_change = []
            self.on_change.append(ChangeTrigger(self.task, inline))
        # Handle timeout
        #if ButtonPromise.focus_rule.match(inline.inline):
        #    self.focus_label = inline

    def expand_inlines(self):
        # Expand all the 'for' buttons
        for inline in self.inlines:
            self.expand_inline(inline)

    def add_nav_button(self, button):
        dup = self.nav_button_map.get(button.message)
        if dup is not None: # and not dup.is_block:
            if dup.path is not None and dup.path == button.path:
                return
            if dup.label is not None and dup.label == button.label:
                return
            # If the weight is greater
            # It overrides the other button
            # 0 Means it is overridable
            if button.priority > dup.priority:
                self.nav_buttons = [x for x in self.nav_buttons if x != dup]
            elif button.label_weight > dup.label_weight:
                self.nav_buttons = [x for x in self.nav_buttons if x != dup]
            else:
                return

        self.nav_buttons.append(button)
        self.nav_button_map[button.message] = button


    def build_navigation_buttons(self):
        self.nav_buttons = []
        self.nav_button_map = {}
        # if self.nav_sub_task_promise is not None:
        #     self.nav_sub_task_promise.cancel()
        #     self.nav_sub_task_promise = None

        path_labels = ButtonPromise.navigation_map.get(self.path)
        if path_labels is None:
            return
        
        ButtonPromise.navigating_promise = self
        #
        # Make sure to use the right task
        #
        t = FrameContext.task 
        FrameContext.task = self.task
        p = task_all(*path_labels, sub_tasks=True)
        FrameContext.task = t

        p.poll()
        #
        # This could get into a lock
        # but the expectation is this runs in one pass
        #
        count = 0
        while not p.done():
            p.poll()

            if p.is_idle:
                break

            if count > 100000:
                print(f"path {self.path} caused hang build navigation {self.__class__.__name__}")
                break
            count += 1
        #
        # Sub Tasks are still running
        #
        self.nav_sub_task_promise = p # if not p.done() else None
        ButtonPromise.navigating_promise = None
        
    

        
        
    
    
from ...pages.layout.layout import Layout
from ...pages.layout.row import Row
from ...pages.layout.button import Button
from ...pages.layout.blank import Blank
class GuiPromise(ButtonPromise):
    button_height_px = 40

    def __init__(self, page, timeout=None) -> None:
        path = page.get_path()
        super().__init__(path, page.gui_task, timeout)

        self.page = page
        self.button_layout = None

    def initial_poll(self):
        if self._initial_poll:
            return
        
        super().initial_poll()
        self.show_buttons()
        self.page.set_button_layout(self.button_layout, self)

    #
    # This 
    #
    def show_buttons(self):
        if self.task is None:
            self.task = self.page.gui_task
            # First run could have no gui_task
            if self.task is None:
                self.task = FrameContext.task
        task = self.task
        aspect_ratio = get_client_aspect_ratio(task.main.page.client_id)

        #
        # Create button Row
        #
        top = ((aspect_ratio.y - GuiPromise.button_height_px)/aspect_ratio.y)*100

        button_layout = Layout(None, None, 0,top,100,100)
        button_layout.tag = task.main.page.get_tag()

        active = 0
        index = 0
        layout_row: Row
        layout_row = Row()
        layout_row.tag = task.main.page.get_tag()

        buttons = self.get_expanded_buttons()
        
        if len(buttons) == 0:
            return
        
        
        for button in buttons:
            match button.__class__.__name__:
                case "Button":
                    value = True
                    #button.end_await_node = node.end_await_node
                    if button.code is not None:
                        value = task.eval_code(button.code)
                    if value and button.should_present(0):#task.main.client_id):
                        runtime_node = ChoiceButtonRuntimeNode(self, button, task.main.page.get_tag())
                        #runtime_node.enter(mast, task, button)
                        msg = task.format_string(button.message)
                        layout_button = Button(runtime_node.tag, msg)
                        button.layout_item = layout_button
                        layout_row.add(layout_button)

                        apply_control_styles(".choice", None, layout_button, task)
                        
                        # After style could change tag
                        task.main.page.add_tag(layout_button, runtime_node)
                        active += 1
                case "Separator":
                    # Handle face expression
                    layout_row.add(Blank())
            index+=1
        
        if active>0:
            button_layout.add(layout_row)
            self.button_layout = button_layout
            #task.main.page.set_button_layout(button_layout)
        else:
            self.button_layout = None
            #task.main.page.set_button_layout(None)

        self.active_buttons = active
        self.buttons = buttons
        self.button = None



def gui(buttons=None, timeout=None):
    """present the gui that has been queued up

    Args:
        buttons (dict, optional): _description_. Defaults to None.
        timeout (promise, optional): A promise that ends the gui. Typically a timeout. Defaults to None.

    Returns:
        Promise: The promise for the gui, promise is done when a button is selected
    """    
    from ...mast_sbs.story_nodes.button import Button
    page = FrameContext.page
    #sbs.send_gui_sub_region(page.client_id, "FULL", "", 0, 0, 100, 100)
    #sbs.target_gui_sub_region(page.client_id, "FULL")
    ret = GuiPromise(page, timeout)
    if buttons is not None:
        for k in buttons:
            ret .buttons.append(Button(k, label=buttons[k],loc=0))
    page.swap_gui_promise(ret)
    return ret
    



from .update import gui_hide, gui_represent
def gui_hide_choice():
    page = FrameContext.page
    if page is None:
        return
    task = page.gui_task
    
    promise = task.get_variable("BUTTON_PROMISE")
    if promise is None:
        return
    button_item = promise.running_button.layout_item
    button_layout = promise.button_layout

    gui_hide(button_item)
    gui_represent(button_layout)


from ...vec import Vec3
def gui_percent_from_pixels(client_id, pixels):
    aspect_ratio = get_client_aspect_ratio(client_id)
    x = (pixels/aspect_ratio.x)*100
    y = (pixels/aspect_ratio.y)*100
    return Vec3(x,y,0)

def gui_percent_from_ems(client_id, ems, font):
    h = FrameContext.context.sbs.get_text_line_height(font, "X")
    w = FrameContext.context.sbs.get_text_line_width(font, "X")
    aspect_ratio = get_client_aspect_ratio(client_id)
    x = ((ems*w)/aspect_ratio.x)*100
    y = ((ems*h)/aspect_ratio.y)*100
    return Vec3(x,y,0)

def gui_task_for_client(client_id):
    gui = Agent.get(client_id)
    if gui is None:
        return None
    page = gui.page
    if page is None:
        return None
    return page.gui_task

