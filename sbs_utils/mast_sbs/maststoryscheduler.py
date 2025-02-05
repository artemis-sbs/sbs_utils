from ..mast.mastscheduler import MastScheduler
from ..mast.mast import Mast, Scope
from ..agent import Agent
from ..gui import Gui
from ..helpers import FakeEvent, FrameContext, format_exception
from ..mast.mast_globals import MastGlobals




class StoryScheduler(MastScheduler):
    def __init__(self, mast: Mast, overrides=None):
        super().__init__(mast, overrides)
        self.paint_refresh = False
        self.errors = []
        self.client_id = None

    def is_server(self):
        return self.client_id == 0

    def run(self, client_id, page, label="main", inputs=None, task_name=None, defer=False):
        self.page = page
        self.client_id = client_id
        restore = FrameContext.page
        FrameContext.page = self.page
        ret =  super().start_task( label, inputs, task_name, defer)
        FrameContext.page = restore
        return ret

    def story_tick_tasks(self, client_id):
        #
        restore = FrameContext.page
        FrameContext.page = self.page
        ret = super().tick()
        FrameContext.page = restore
        return ret


    def refresh(self, label):
        for task in self.tasks:
            if label == task.active_label:
                restore = FrameContext.page
                FrameContext.page = self.page
                task.jump(task.active_label)
                task.tick()
                FrameContext.page = restore
                Gui.dirty(self.client_id)
            if label == None:
                # On change or element requested refresh?
                #task.jump(task.active_label)
                self.story_tick_tasks(self.client_id)
                self.page.gui_state = "repaint"
                event = FakeEvent(self.client_id, "gui_represent")
                self.page.present(event)


    def runtime_error(self, message):
        FrameContext.context.sbs.pause_sim()
        err = format_exception(message, "SBS Utils Page level Runtime Error:")
        print(err)
        FrameContext.error_message = err
        task = self.active_task
        if task is not None:
            err = task.get_runtime_error_info(err)
        #err = traceback.format_exc()
        if not err.startswith("NoneType"):
            #message += str(err)
            self.errors = [err]
        else:
            print(err)


    def get_value(self, key, defa=None):
        """_summary_

        Args:
            key (_type_): _description_
            defa (_type_, optional): _description_. Defaults to None.

        Returns:
            _type_: _description_
        """
        val = MastGlobals.globals.get(key, None) # don't use defa here
        if val is not None:
            return (val, Scope.SHARED)
        # Check shared
        val = Agent.SHARED.get_inventory_value(key, None) # don't use defa here
        if val is not None:
            return (val, Scope.SHARED)
        
        if self.client_id is not None and Agent.get(self.client_id) is not None:
            val = Agent.get(self.client_id).get_inventory_value(key, None) # don't use defa here
            if val is not None:
                return (val, Scope.CLIENT)
            
            assign = None
            if self.client_id is not None:
                _id = FrameContext.context.sbs.get_ship_of_client(self.client_id)
                if _id:
                    assign = Agent.get(_id)
            if assign is not None:
                val = assign.get_inventory_value(key, None) # don't use defa here
                if val is not None:
                    return (val, Scope.ASSIGNED)

        val = self.get_inventory_value(key, None) # now defa make sense
        if val is not None:
            #TODO: Should this no longer be NORMAL
            return (val, Scope.NORMAL) # NORMAL is the same as TASK
        return (val, Scope.UNKNOWN)
    
    def set_value(self, key, value, scope):
        if scope == Scope.SHARED:
            # self.main.mast.vars[key] = value
            Agent.SHARED.set_inventory_value(key, value)
            return scope
        
        if self.client_id is None:
            return Scope.UNKNOWN
        
        if scope == Scope.CLIENT:
            Agent.get(self.client_id).set_inventory_value(key, value) # don't use defa here
            return scope
        
        if scope == Scope.ASSIGNED:
            _ship = FrameContext.context.sbs.get_ship_of_client(self.client_id) 
            _ship = None if _ship == 0 else _ship
            assign = Agent.get(_ship)
            if assign is not None:
                assign.set_inventory_value(key, value) # don't use defa here
            return scope
    
        return Scope.UNKNOWN
    
    def get_symbols(self):
        return super().get_symbols()
        #####
        # mast_inv = super().get_symbols()
        # if self.client_id is None:        
        #     return mast_inv
        # m1 = mast_inv | Agent.get(self.client_id).inventory.collections
        # _ship = FrameContext.context.sbs.get_ship_of_client(self.client_id) 
        # _ship = None if _ship == 0 else _ship
        # assign = Agent.get(_ship)
        # if assign is not None:
        #     m1 = m1 | assign.inventory.collections
        # return m1

