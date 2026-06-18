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

from ...helpers import FrameContext, FakeEvent

from ...futures import AwaitBlockPromise, Trigger, awaitable
from ...gui import get_client_aspect_ratio
from ..style import apply_control_styles
from ...mast.pollresults import PollResults

from ..execution import task_all, AWAIT
from .change import ChangeTrigger
from ...agent import Agent

import re


def gui_screen_size(client_id):
    """Return the pixel dimensions of a client's screen.

    Args:
        client_id (int): The client whose screen to query.

    Returns:
        Vec3: Screen dimensions in pixels (x=width, y=height, z=0).

    Example:
        size = gui_screen_size(CLIENT_ID)
        ~~ print(size.x, size.y) ~~
    """
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

    def pressed_set_values(self, task):
        pass

    def pressed_test(self):
        return True


    def cancel(self, msg=None):
        if self.nav_sub_task_promise is not None:
            self.nav_sub_task_promise.cancel()
            self.nav_sub_task_promise = None

    def handle_button_sub_task(self, sub_task):
        pass

    def poll(self):
        res = super().poll()
        if res != PollResults.OK_RUN_AGAIN and self.done():
            return res
        

        if self.sub_task is not None and not self.sub_task.done:
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
            self.task = self.server_task
            # First run could have no gui_task
            if self.task is None:
                self.task = FrameContext.task

        if self.button is not None:
            if self.var:
                task.set_value_keep_scope(self.var, self.button.index)

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
                self.sub_task = None
                return PollResults.OK_JUMP
            else:
                self.pre_button_run(self.running_button)
                
                sub_task = self.running_button.run(self.task, self)
                #
                # GUI sub_task run themselves
                # COMMS and Science are on an unscheduled task
                # So they need to handle it differently
                #
                self.handle_button_sub_task(sub_task)

                if sub_task is not None:
                    self.pressed_set_values(sub_task)
                    self.sub_task = sub_task
                    if self.running_button.is_block:
                        if not sub_task.done:
                            #
                            # OK Since we are no longer scheduled
                            # We check if buttons were not built
                            # from the button run, if not try 
                            # to build them now
                            #
                            print("WARNING: Button Handlers should not have any awaits")
                    #
                    if len(self.buttons) == 0:
                        self.show_buttons()

                self.post_button_run(self.running_button)
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
        # The sub task is for a running button
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
        promise_buttons = self.build_promise_buttons()
        buttons.extend(promise_buttons)
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
        restore_page = FrameContext.page 
        FrameContext.task = self.task
        FrameContext.page= self.task.main.page
        p = task_all(*path_labels, sub_tasks=True)

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
        FrameContext.task = t
        FrameContext.page = restore_page

    def build_promise_buttons(self):
        return []
    def pre_button_run(self, button):
        return
    def post_button_run(self, button):
        return

class PropertyChangeTrigger(Trigger):
    def __init__(self, task, var, label=None):
        self.task = task
        self.value = self.task.get_variable(var)
        self.label = label
        self.var = var

    def test(self):
        prev = self.value
        self.value = self.task.get_variable(self.var)
        return prev!=self.value
    
    def run(self):
        event = FrameContext.context.event
        fake_event = FakeEvent(self.task.main.client_id, "gui_change")
        FrameContext.context.event = fake_event
        
        self.task.push_inline_block(self.label, 0)
        self.task.tick_in_context()
        FrameContext.context.event = event


        
def gui_properties_change(var, label):
    """Watch a MAST variable and run an inline block when its value changes.

    Registers a per-tick change detector on the current client's GUI task.
    When ``var`` changes value, the block at ``label`` is pushed and executed
    immediately within the current tick.

    Args:
        var (str): Name of the MAST variable to watch.
        label: The inline label or block to execute on change.

    Example:
        gui_properties_change("shield_level", shield_changed)
        ///shield_changed
            gui_text("Shields: {shield_level}")
    """
    if FrameContext.client_page is None:
        return
    
    task = FrameContext.client_task
    changes = task.get_variable("__PROP_CHANGES__", [])
    trig = PropertyChangeTrigger(task, var, label)
    changes.append(trig)
    task.set_variable("__PROP_CHANGES__", changes)
    task.on_change_items.append(trig)
    # Need to track and remove
    return None
    

        
        
    
    
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

def handle_gui_from_child_task(p):
    yield AWAIT(p)


@awaitable
def gui(buttons=None, timeout=None):
    """Present the GUI layout that has been queued up for the current client.

    Suspends execution until the player presses a button or the timeout fires.
    GUI elements (text, images, sections, etc.) must be queued with ``gui_*``
    calls before ``await gui()``; they are rendered when the promise activates.

    Args:
        buttons (dict, optional): Extra buttons to add, mapping label text to
            jump target label name. e.g. ``{"Start": "start_label"}``.
            Defaults to None.
        timeout (Promise, optional): A promise (e.g. ``timeout_sim(30)``) that
            cancels the GUI when it resolves. Defaults to None.

    Returns:
        Promise: Resolves when a button is pressed or timeout fires.

    Example:
        gui_text("Choose your mission")
        await gui():
            + "Patrol":
                jump patrol_mission
            + "Escort":
                jump escort_mission
    """
    from ...mast_sbs.story_nodes.button import Button
    from ...futures import Promise
    page = FrameContext.page
    task = FrameContext.task
    gui_task = FrameContext.page.gui_task


    ret = GuiPromise(page, timeout)
    if buttons is not None:
        for k in buttons:
            ret .buttons.append(Button(k, label=buttons[k],loc=0))
    
    if task != gui_task:
        print("await gui() was not called in gui's main task. Consider using gui_task_jump.")
    else:
        page.swap_gui_promise(ret)
    return ret
    



from .update import gui_hide, gui_represent
def gui_hide_choice():
    """Hide the button that was just pressed during its handler block.

    Call this from inside a button's handler block to remove the button
    from the layout immediately after it is clicked, without waiting for
    the ``await gui()`` to complete. Has no effect if called outside of
    a running button handler.

    Example:
        await gui():
            + "Launch Missile":
                gui_hide_choice()
                ~~ fire_torpedo(SHIP_ID) ~~
    """
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
    """Convert a pixel size to GUI percentage coordinates for a client's screen.

    GUI layout positions are expressed as percentages (0–100) of the screen
    dimensions. Use this to convert a fixed pixel measurement to the equivalent
    percentage for a specific client's resolution.

    Args:
        client_id (int): The client whose screen resolution to use.
        pixels (float): The pixel size to convert.

    Returns:
        Vec3: Percentage values (x=horizontal %, y=vertical %, z=0).

    Example:
        pct = gui_percent_from_pixels(CLIENT_ID, 40)
        gui_section(style="height:{pct.y}%;")
    """
    aspect_ratio = get_client_aspect_ratio(client_id)
    x = (pixels/aspect_ratio.x)*100
    y = (pixels/aspect_ratio.y)*100
    return Vec3(x,y,0)

def gui_percent_from_ems(client_id, ems, font):
    """Convert an em-based size to GUI percentage coordinates for a client's screen.

    An em is the width/height of the character "X" in the given font. Use this
    to size layout elements relative to text size rather than fixed pixels.

    Args:
        client_id (int): The client whose screen resolution to use.
        ems (float): The number of em units to convert.
        font (str): Font name used to measure one em (e.g. ``"hud_font"``).

    Returns:
        Vec3: Percentage values (x=horizontal %, y=vertical %, z=0).

    Example:
        pct = gui_percent_from_ems(CLIENT_ID, 2, "hud_font")
        gui_section(style="width:{pct.x}%;")
    """
    h = FrameContext.context.sbs.get_text_line_height(font, "X")
    w = FrameContext.context.sbs.get_text_line_width(font, "X")
    aspect_ratio = get_client_aspect_ratio(client_id)
    x = ((ems*w)/aspect_ratio.x)*100
    y = ((ems*h)/aspect_ratio.y)*100
    return Vec3(x,y,0)

def gui_task_for_client(client_id):
    """Return the GUI task currently running for a client.

    Each connected client has a dedicated GUI task that drives its page layout.
    Returns ``None`` if the client has no active page.

    Args:
        client_id (int): The client to look up.

    Returns:
        MastAsyncTask | None: The client's GUI task, or ``None`` if unavailable.

    Example:
        task = gui_task_for_client(CLIENT_ID)
        if task is not None:
            ~~ task.set_variable("score", 10) ~~
    """
    gui = Agent.get(client_id)
    if gui is None:
        return None
    page = gui.page
    if page is None:
        return None
    return page.gui_task

def gui_page_for_client(client_id):
    """Return the active GUI page for a client.

    Args:
        client_id (int): The client to look up.

    Returns:
        Page | None: The client's current page, or ``None`` if unavailable.

    Example:
        page = gui_page_for_client(CLIENT_ID)
        if page is not None:
            ~~ page.dirty() ~~
    """
    gui = Agent.get(client_id)
    if gui is None:
        return None
    return gui.page


def gui_client_id():
    """Return the client ID for the currently executing GUI task.

    Shortcut for ``FrameContext.client_id``. Returns ``0`` when running on
    the server.

    Returns:
        int: Current client ID, or ``0`` for the server.

    Example:
        id = gui_client_id()
        gui_text("Your client ID is {id}")
    """
    return FrameContext.client_id

