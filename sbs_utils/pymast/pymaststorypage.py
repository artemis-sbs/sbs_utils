import sbs
from ..mast.parsers import StyleDefinition, LayoutAreaParser
from ..gui import Page, Context
from ..pages import layout
from .pollresults import PollResults
from .pymastscheduler import PyMastScheduler
import traceback
from .. import query
import inspect
import logging

class CodePusher:
    def __init__(self, page, func_or_tuple, end_await=True) -> None:
        self.func_or_tuple = func_or_tuple
        self.end_await = end_await
        self.page = page


    def on_message(self, ctx, event):
        if event.client_id != self.page.client_id:
            return
        data = None
        button_func = self.func_or_tuple
        if isinstance(self.func_or_tuple, tuple):
            data = self.func_or_tuple[1]
            button_func = self.func_or_tuple[0]

        if button_func is None:
            return
            
        
        def pusher(story):
            if data is not None:
                gen = button_func(data)
            else:
                gen = button_func()
            if gen is not None:
                for res in gen:
                    yield res
            self.page.task.pop()

        # Skip if Already
            if self.page is not None and not self.end_await:
                self.page.end_await = True 

        self.page.task.push_jump_pop(pusher)
        # Tick the page task to get things running faster if needed
        self.page.tick_gui_task(ctx)



class PyMastStoryPage(Page):
    tag = 0
    story=None

    def __init__(self) -> None:
        self.gui_state = 'repaint'
        self.story_scheduler = None
        self.layouts = []
        self.pending_layouts = self.pending_layouts = [layout.Layout(None, None, None, 0,0, 100, 90)]
        self.pending_row = self.pending_row = layout.Row()
        self.pending_tag_map = {}
        self.tag_map = {}
        self.aspect_ratio = sbs.vec2(1920,1071)
        self.client_id = None
        self.sim = None
        self.console = ""
        self.widgets = ""
        self.pending_console = ""
        self.pending_widgets = ""
        #self.tag = 0
        self.errors = []
        self.on_message_cb = None
        self.test_end_await_cb = None
        self.test_refresh_cb = None
        self.disconnect_cb = None
        self.end_await = True
        self.task = None
        self.disconnected = False
        self.change_console_label = None
        self.gui_popped = False

    def run(self, time_out):
        self.gui_state = 'repaint'
        #self.present(Context(self.story.sim, sbs, self.aspect_ratio), None)
        #self.present(self.story.sim, None)
        # ?? Change task??
        #self.task = self.story.task
        self.end_await = False
        def pusher(story):
            return self._run(time_out)
        return self.task.push_jump_pop(pusher)
    
    def _run(self, time_out):    
        self.end_await = False
        # Assume time_out for gui is app seconds
        if time_out is not None:
            end_timeout = sbs.app_seconds()+ time_out
        while self.end_await == False:
            #print(f"running ")
            self.present(Context(self.story.sim, sbs, self.aspect_ratio), None)
            # Get out faster if ended
            if self.end_await:
                break
            if time_out is not None:
                if sbs.app_seconds() > end_timeout:
                    break

            yield PollResults.OK_RUN_AGAIN
        self.present(Context(self.story.sim, sbs, self.aspect_ratio), None)
        yield self.task.pop()


    def reroute_gui(self, label):
        if self.task: 
            if not self.task.done:
                self.task.jump(label)
            else:
                ## Task ended start another
                self.task = self.task.scheduler.schedule_task(label)
                self.task.page = self
                # is this needed?
                self.gui_state = "repaint"
                self.present(Context(self.story.sim, sbs, self.aspect_ratio), None)


    def swap_layout(self):
        self.layouts = self.pending_layouts
        self.tag_map = self.pending_tag_map
        self.console = self.pending_console
        self.widgets = self.pending_widgets
        
        self.tag = 10000
        
        if self.layouts:
            for layout_obj in self.layouts:
                layout_obj.calc()
            
            self.pending_layouts = self.pending_layouts = [layout.Layout(None, None, None, 0,0, 100, 90)]
            self.pending_row = self.pending_row = layout.Row()
            self.pending_tag_map = {}
            self.pending_console = ""
            self.pending_widgets = ""

        self.gui_state = 'repaint'
        

    def get_tag(self):
        self.tag += 1
        return str(self.tag)

    def add_row(self):
        if not self.pending_layouts:
            self.pending_layouts = [layout.Layout(None, None, None, 20,10, 100, 90)]
        if self.pending_row:
            if len(self.pending_row.columns):
                self.pending_layouts[-1].add(self.pending_row)
        if self.pending_tag_map is None:
            self.pending_tag_map = {}
        self.pending_row = layout.Row()
        return self.pending_row

    def add_tag(self, layout_item, runtime_node):
        if self.pending_tag_map is None:
            self.pending_tag_map = {}
        if hasattr(layout_item, 'tag'):
            self.pending_tag_map[layout_item.tag] = runtime_node

    def add_content(self, layout_item, runtime_node):
        if self.pending_layouts is None:
            self.add_row()

        self.add_tag(layout_item, runtime_node)

        self.pending_row.add(layout_item)

    def set_widget_list(self, console,widgets):
        self.pending_console = console
        self.pending_widgets = widgets

    def activate_console_widgets(self, console):

        match console.lower():
            case "helm":
                console =  "normal_helm"
                widgets = "3dview^2dview^helm_movement^throttle^request_dock^shield_control^ship_data^text_waterfall^main_screen_control"
            case "weapons":
                console =  "normal_weap"
                widgets = "2dview^weapon_control^weap_beam_freq^ship_data^shield_control^text_waterfall^main_screen_control"
            case "science":
                console =  "normal_sci"
                widgets = "science_2d_view^ship_data^text_waterfall^science_data^science_sorted_list"
            case "engineering":
                console =  "normal_engi"
                widgets = "ship_internal_view^grid_object_list^grid_face^grid_control^text_waterfall^eng_heat_controls^eng_power_controls^ship_data"
            case "comms":
                console =  "normal_comm"
                widgets = "text_waterfall^comms_waterfall^comms_control^comms_face^comms_sorted_list^ship_data^red_alert"
            case "mainscreen":
                console =  "normal_main"
        self.set_widget_list(console,widgets)

    
    def activate_console(self, console):
        match console.lower():
            case "helm":
                console =  "normal_helm"
            case "weapons":
                console =  "normal_weap"
            case "science":
                console =  "normal_sci"
            case "engineering":
                console =  "normal_engi"
            case "comms":
                console =  "normal_comm"
            case "mainscreen":
                console =  "normal_main"
        self.pending_console = console
        

    def add_console_widget(self, widget):
        if self.pending_widgets == "":
            self.pending_widgets = widget
        # BUG? 3dview needs to be first???
        elif widget=="3dview":
            self.pending_widgets = widget + "^" + self.pending_widgets 
        else:
            self.pending_widgets += "^"+widget
        

    def add_section(self, click_tag, click_props):
        if not self.pending_layouts:
            self.pending_layouts = [layout.Layout(click_tag, click_props, None, 0,0, 100, 90)]
        else:
            self.add_row()
            self.pending_layouts.append(layout.Layout(click_tag, click_props,None, 0,0, 100, 90))
        return self.pending_layouts[-1]

    def get_pending_layout(self):
        if not self.pending_layouts:
            self.add_row()
        return self.pending_layouts[-1]

    def get_pending_row(self):
        if not self.pending_layouts:
            self.add_row()
        return self.pending_row
    

    def set_buttons(self, buttons):
        if buttons is None:
            self.set_button_layout(None)
            return
        top = ((self.aspect_ratio.y - 50)/self.aspect_ratio.y)*100
        button_layout = layout.Layout(None, None, None, 0,top,100,100)
        layout_row = layout.Row()
        for button, value in buttons.items():
            the_button = layout.Button(self.get_tag(), button)
            layout_row.add(the_button)
            self.add_tag(the_button, CodePusher(self, value))
        button_layout.add(layout_row)
        self.set_button_layout(button_layout)


    def set_button_layout(self, layout):
        if self.pending_row and self.pending_layouts:
            if self.pending_row:
                self.pending_layouts[-1].add(self.pending_row)
        
        if not self.pending_layouts:
            self.add_section()
        
        if layout:
            self.pending_layouts.append(layout)
        
        self.end_await = False
        self.swap_layout()

    def present(self, ctx, event):
        #do_tick = True
        #print(f"**{self.gui_state} {self.task.id & 0xFFFFFFFFF if self.task else 99}**")
        if self.gui_popped:
            return

        
        # This is called via run if event is None
        if event is None:
            class Fake(object):
                pass
            event = Fake()
            event.client_id = self.client_id
         #   do_tick = False
            #self.gui_state = 'repaint'
        else:
            if event.tag == "gui_push":
                self.gui_state = 'repaint'
        
        
        """ Present the gui """
        if self.client_id is None:
            self.client_id = event.client_id
        if self.gui_state == "errors":
            return
        
        if self.gui_state == "task_ended":
            sbs.send_gui_clear(event.client_id)
            sbs.send_gui_text(event.client_id, "error", f"text: Empty content. Did task end? Or did you forget to use yield?", 0,96,100,100)
            self.gui_state = "errors"
            return



        if self.story_scheduler is None:
            if self.story is not None:
                label = self.story.start_server if self.client_id ==0 else self.story.start_client
                # print(f"Spawning task {label}")
                self.story.sim = ctx.sim if ctx else None
                self.story_scheduler = self.story.add_scheduler(ctx, label)
                #self.story_scheduler.page = self
                self.task = self.story_scheduler.task
                #print(f"Task Started {self.task.id & 0xFFFFFFFFF}")
                #
                # Initial kick
                #
                self.task.page = self
                self.story_scheduler.page = self 
                self.story.page = self

                self.tick_gui_task(ctx)
                    
                self.gui_state = "repaint"
                
        # This should not occur???
        if self.client_id != event.client_id:
            return
        
        if self.task and self.task.done:
            # Delay this by one cycle
            # to let truly ending guis to purge
            sbs.send_gui_clear(event.client_id)
            cls_name = self.__class__.__name__
            #print(f"Task Done {self.task.id & 0xFFFFFFFFF}")
            sbs.send_gui_text(event.client_id, "error", f"text: {cls_name} Empty content. Did task end? Or did you forget to use yield?", 0,96,100,100)
            self.gui_state = "task_ended"
            return



        if self.test_end_await_cb is not None:
            self.end_await = self.test_end_await_cb()

        # clear gui, until the next gui await
        # show clear screen in case tasks ends unexpectedly
        
        if self.test_refresh_cb is not None:
            if self.test_refresh_cb():
                self.gui_state = 'refresh'


        if len(self.errors) > 0:
            #message = "PyMast errors\n".join(self.errors)
            message = "".join(self.errors)
            #TODO: Commas should be legal chars
            message = message.replace(",", " ")
            
            sbs.send_gui_clear(event.client_id)
            if event.client_id != 0:
                sbs.send_client_widget_list(event.client_id, "", "")
            sbs.send_gui_text(event.client_id, "error", f"text:{message}", 0,6,100,100)
            self.gui_state = "errors"
            return
        

        if ctx is None:
            return
        match self.gui_state:
            case  "repaint":
                ctx.sbs.send_gui_clear(event.client_id)
                if event.client_id != 0:
                    ctx.sbs.send_client_widget_list(event.client_id, self.console, self.widgets)
                # Setting this to a state we don't process
                # keeps the existing GUI displayed
                for layout in self.layouts:
                    layout.present(Context(ctx.sim, ctx.sbs, self.aspect_ratio),event)
                if ctx is None or len(self.layouts)==0:
                    self.gui_state = "repaint"
                else:
                    self.gui_state = "presenting"
                ctx.sbs.send_gui_complete(event.client_id)
            case  "refresh":
                for layout in self.layouts:
                    layout.present(Context(ctx.sim, ctx.sbs, self.aspect_ratio),event)
                if ctx is None or len(self.layouts)==0:
                    self.gui_state = "repaint"
                else:
                    self.gui_state = "presenting"

    def tick_gui_task(self, ctx):
        if ctx is None:
            #print("Context is NONE")
            return
        
        if self.task is None:
            #print("gui task is None")
            return

        try:
            #self.story.scheduler.tick()# = self.story_scheduler
            #self.story.task = self.task
            if self.disconnected:
                self.task.end()
                return
            self.story_scheduler.tick(ctx)# = self.story_scheduler
        except BaseException as err:
            sbs.pause_sim()
            text_err = traceback.format_exc()
            print(text_err)
            text_err = text_err.replace(chr(94), " ")
            #text_err = text_err.replace('', "")
            logger = logging.getLogger("pymast.runtime")
            logger.info(text_err)
            self.errors.append(text_err)

    def on_pop(self, ctx):
        #print(f"On Gui Pop {self.__class__.__name__}")
        self.gui_popped = True
        self.story_scheduler.stop_all()


    def on_message(self, ctx, event):
        message_tag = event.sub_tag
        # This should not occur???
        if self.client_id != event.client_id:
            return
        #
        # Not sure why this cannot be higher in the function
        # but without this a popped gui was refreshing
        #
        if self.task.done or self.gui_popped:
            return
        
        self.story.scheduler = self.story_scheduler
        self.story.task = self.task
        if self.disconnect_cb and message_tag == "mast:client_disconnect":
            self.disconnected = False
            self.disconnect_cb()
        
        refresh = False        
        call_label = self.tag_map.get(message_tag)
        if call_label:
            if isinstance(call_label, CodePusher):
                call_label.on_message(ctx, event)
                refresh=True
            elif inspect.isfunction(call_label):
                call_label(ctx, event)
                refresh=True
            else:
                call_label.on_message(ctx, event)
                refresh=True
                
        # else:
        for layout in self.layouts:
            layout.on_message(Context(ctx.sim, ctx.sbs, self.aspect_ratio),event)
        if self.on_message_cb is not None:
            refresh = self.on_message_cb(ctx, event)

        
        
        if refresh:
            self.gui_state = "refresh"
            self.present(ctx, event)


    def on_event(self, ctx, event):
        if self.task is None:
            return
        
        try:
            # This should not occur???
            if self.client_id != event.client_id:
                return
            self.story.scheduler = self.story_scheduler
            self.story.task = self.task
            if event.tag == "mast:client_disconnect":
                self.disconnected = True
                if self.disconnect_cb:
                    self.disconnect_cb()

            if event.tag == "client_change":
                if event.sub_tag == "change_console":
                    if self.change_console_label:
                        # Remember it is awaiting gui already
                        self.task.jump(self.change_console_label)
                        #self.present(ctx,event)

            elif event.tag == "screen_size":
                if event.source_point.x!=0 and event.source_point.y != 0:
                    if (self.aspect_ratio.x != event.source_point.x or 
                        self.aspect_ratio.y != event.source_point.y):
                        self.aspect_ratio.x = event.source_point.x
                        self.aspect_ratio.y = event.source_point.y

                        for layout in self.layouts:
                            layout.aspect_ratio.x = self.aspect_ratio.x
                            layout.aspect_ratio.y = self.aspect_ratio.y
                            layout.calc()
                        self.gui_state = 'repaint'


            self.task.on_event(ctx, event)
        except BaseException as err:
            sbs.pause_sim()
            text_err = traceback.format_exc()
            print(text_err)
            text_err = text_err.replace(chr(94), "")
            logger = logging.getLogger("pymast.runtime")
            logger.info(text_err)
            self.errors.append(text_err)

    def assign_player_ship(self, player):
        if player is None:
            id = None
            ids = query.to_list(query.role('__PLAYER__'))
            #
            # If none was sent, assign it to the first ship found
            #
            if len(ids)>0:
                id = ids[0]
                sbs.assign_client_to_ship(self.client_id, id)
                query.set_inventory_value(self.client_id, "assigned_ship", id)
            return
        elif isinstance(player, str):
            #
            # If a name is sent try to find it
            #
            id = None
            for player_obj in query.to_object_list(query.role('__PLAYER__')):
                id = player_obj.id
                if player_obj.name == player:
                    break
                if player_obj.comms_id == player:
                    break
            if id is not None:
                #print(f"assigned to {id}")
                sbs.assign_client_to_ship(self.client_id, id)
                query.set_inventory_value(self.client_id, "assigned_ship", id)
            return
        else:
            id = query.to_id(player)
            sbs.assign_client_to_ship(self.client_id, id)
            query.set_inventory_value(self.client_id, "assigned_ship", id)


    def apply_style_name(self, style_name, layout_item):
        style_def = StyleDefinition.styles.get(style_name)
        self.apply_style_def(style_def, layout_item)
    def apply_style_def(self, style_def, layout_item):
        if style_def is None:
            return
        symbols = {}
        #task.get_symbols()
        aspect_ratio = self.aspect_ratio
        if isinstance(style_def, str):
            style_def = StyleDefinition.parse(style_def)
        area = style_def.get("area")
        if area is not None:
            i = 1
            values=[]
            for ast in area:
                if i >0:
                    ratio =  aspect_ratio.x
                else:
                    ratio =  aspect_ratio.y
                i=-i
                values.append(LayoutAreaParser.compute(ast, symbols,ratio))
            layout_item.set_bounds(layout.Bounds(*values))

        height = style_def.get("row-height")
        if height is not None:
            height = LayoutAreaParser.compute(height, symbols,aspect_ratio.y)
            layout_item.set_row_height(height)        
        width = style_def.get("col-width")
        if width is not None:
            width = LayoutAreaParser.compute(height, symbols,aspect_ratio.x)
            layout_item.set_col_width(height)        
        padding = style_def.get("padding")
        if padding is not None:
            aspect_ratio = self.aspect_ratio
            i = 1
            values=[]
            for ast in padding:
                if i >0:
                    ratio =  aspect_ratio.x
                else:
                    ratio =  aspect_ratio.y
                i=-i
                values.append(LayoutAreaParser.compute(ast, symbols,ratio))
            while len(values)<4:
                values.append(0.0)
            layout_item.set_padding(layout.Bounds(*values))
