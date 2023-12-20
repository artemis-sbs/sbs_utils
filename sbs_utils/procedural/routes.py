from ..consoledispatcher import ConsoleDispatcher
from ..griddispatcher import GridDispatcher
from ..lifetimedispatcher import LifetimeDispatcher
from ..damagedispatcher import DamageDispatcher, CollisionDispatcher
from .query import to_id

from ..helpers import FrameContext, FakeEvent

import sbs


uids = {
    "comms": "comms_target_UID",
    "science": "science_target_UID",
    "weapons": "weapon_target_UID",
    "grid": "grid_selected_UID"
}
_SELECT = 1
_POINT = 2
_FOCUS = 3
_GRID_OBJECT = 4


class HandleConsoleSelect:
    just_once = set()
    def __init__(self, console, label, etype) -> None:
        self.console = console
        #
        # Get a scheduler to schedule future tasks
        # since the task may not be around later
        # This will be the main server scheduler
        #
        # Also avoid adding twice, e.g. each client can added the route
        #
        self.etype = etype
        if not label in HandleConsoleSelect.just_once:
            task = FrameContext.task
            #
            # Mast Task inherit values
            # so use it to start new ones
            #
            self.task = task
            self.label = label
            HandleConsoleSelect.just_once.add(label)
            uid = uids.get(console)
            if self.etype == _SELECT:
                ConsoleDispatcher.add_default_select(uid, self.selected)
            if self.etype == _POINT:
                if console == "grid":
                    GridDispatcher.add_any_point(self.grid_selected)
                else:
                    ConsoleDispatcher.add_select(uid, self.selected)
            if self.etype == _FOCUS:
                ConsoleDispatcher.add_always_select(uid, self.selected)
            if self.etype == _GRID_OBJECT:
                GridDispatcher.add_any_object(self.grid_selected)


    def grid_selected(self, event):
        self.selected(None, event)

    def selected(self, __, event):
        if self.console == "grid" and self.etype == _SELECT:
            console = "COMMS"
        else:
            console = self.console.upper()
        point = None
        if event.selected_id == 0:
            point = sbs.vec3()
            point.x = event.source_point.x
            point.y = event.source_point.y
            point.z = event.source_point.z
        
        t = self.task.start_task(self.label, {
                    f"{console}_ORIGIN_ID": event.origin_id,
                    f"{console}_PARENT_ID": event.parent_id,
                    f"{console}_SELECTED_ID": event.selected_id,
                    f"{console}_POINT": event.source_point,
                    f"EVENT": event,
                    f"{console}_ROUTED": True
            })
        #   if not .done():
        #         MastAsyncTask.add_dependency(event.origin_id,t)
        #         MastAsyncTask.add_dependency(event.selected_id,t)



def route_comms_focus(label):
    return HandleConsoleSelect("comms", label, _FOCUS)
    
def route_science_focus(label):
    return HandleConsoleSelect("science", label, _FOCUS)

def route_weapons_focus(label):
    return HandleConsoleSelect("weapons", label, _FOCUS)
        
def route_grid_focus(label):
    return HandleConsoleSelect("grid", label, _FOCUS)


def route_comms_select(label):
    return HandleConsoleSelect("comms", label, _SELECT)
    
def route_science_select(label):
    return HandleConsoleSelect("science", label, _SELECT)

def route_weapons_select(label):
    return HandleConsoleSelect("weapons", label, _SELECT)
        
def route_grid_select(label):
    return HandleConsoleSelect("grid", label, _SELECT)

def route_grid_object(label):
    return HandleConsoleSelect("grid", label, _GRID_OBJECT)


def route_comms_point(label):
    return HandleConsoleSelect("comms", label, _POINT)
    
def route_science_point(label):
    return HandleConsoleSelect("science", label, _POINT)

def route_weapons_point(label):
    return HandleConsoleSelect("weapons", label, _POINT)
        
def route_grid_point(label):
    return HandleConsoleSelect("grid", label, _POINT)



class HandleLifetime:
    just_once = set()
    cycles = ["SPAWNED", "SPAWNED", "DESTROYED"]
    def __init__(self, lifecycle, label) -> None:
        #
        #
        # Also avoid adding twice, e.g. each client can added the route
        #
        if lifecycle >= len(HandleLifetime.cycles):
            return
        
        self.cycle = HandleLifetime.cycles[lifecycle] 
        if not label in HandleLifetime.just_once:
            task = FrameContext.task
            # Mast task inherit values
            # So it needs the task 
            self.task = task
            self.label = label
            HandleLifetime.just_once.add(label)
            LifetimeDispatcher.add_lifecycle(lifecycle, self.selected)
            
    def selected(self, so):
        t = self.task.start_task(self.label, {
                    f"{self.cycle}_ID": so.get_id(),
                    f"{self.cycle}_OBJ": so,
                    f"{self.cycle}_ROUTED": True
            })
           #   if not .done():
        #         MastAsyncTask.add_dependency(event.origin_id,t)


        


def route_spawn(label):
    return HandleLifetime(LifetimeDispatcher.SPAWN, label)

def route_grid_spawn(label):
    return HandleLifetime(LifetimeDispatcher.GRID_SPAWN, label)

def route_destroy(label):
    return HandleLifetime(LifetimeDispatcher.DESTROYED, label)



class HandleDamage:
    just_once = set()

    def __init__(self, damage_type, label) -> None:
        #
        #
        # Also avoid adding twice, e.g. each client can added the route
        #
        
        if not label in HandleDamage.just_once:
            task = FrameContext.task
            # Mast task inherit values
            # So it needs the task 
            self.task = task
            self.label = label
            HandleDamage.just_once.add(label)
            if damage_type==DamageDispatcher._HEAT:
                DamageDispatcher.add_any_heat(self.selected)
            elif damage_type==DamageDispatcher._INTERNAL:
                DamageDispatcher.add_any_internal(self.selected)
            else:
                DamageDispatcher.add_any(self.selected)
            
    def selected(self, event):
        t = self.task.start_task(self.label, {
                "DAMAGE_SOURCE_ID": event.origin_id,
                "DAMAGE_TARGET_ID": event.selected_id,
                "DAMAGE_PARENT_ID": event.parent_id,
                "DAMAGE_ORIGIN_ID": event.origin_id,
                "DAMAGE_SELECTED_ID": event.selected_id,
                "EVENT": event,
                "DAMAGE_ROUTED": True
            })
           #   if not .done():
        #         MastAsyncTask.add_dependency(event.origin_id,t)
        #         MastAsyncTask.add_dependency(event.selected_id,t)



def route_damage_heat(label):
    return HandleDamage(DamageDispatcher._HEAT, label)

def route_damage_internal(label):
    return HandleDamage(DamageDispatcher._INTERNAL, label)

def route_damage_object(label):
    return HandleDamage(DamageDispatcher._HULL, label)





class HandleCollision:
    just_once = set()

    def __init__(self, label) -> None:
        #
        #
        # Also avoid adding twice, e.g. each client can added the route
        #
        
        if not label in HandleCollision.just_once:
            task = FrameContext.task
            # Mast task inherit values
            # So it needs the task 
            self.task = task
            self.label = label
            HandleCollision.just_once.add(label)
            CollisionDispatcher.add_any(self.selected)
            
    def selected(self, event):
        t = self.task.start_task(self.label, {
                "COLLISION_SOURCE_ID": event.origin_id,
                "COLLISION_PARENT_ID": event.parent_id,
                "COLLISION_TARGET_ID": event.selected_id,
                "COLLISION_ORIGIN_ID": event.origin_id,
                "COLLISION_SELECTED_ID": event.selected_id,
                #"EVENT": event,
                "COLLISION_ROUTED": True
            })
        #   if not .done():
        #         MastAsyncTask.add_dependency(event.origin_id,t)
        #         MastAsyncTask.add_dependency(event.selected_id,t)


def route_collision_object(label):
    return HandleCollision(label)



def route_change_console(label):
    page = FrameContext.page
    page.change_console_label = label


def _follow_route_console(origin_id, selected_id, console, widget, extra_tag):
    origin_id = to_id(origin_id)
    selected_id = to_id(selected_id )
    event = FakeEvent(sub_tag=console, origin_id=origin_id, selected_id=selected_id, extra_tag=extra_tag,value_tag=widget)
    #
    # A bit of a hack directly using dispatchers data
    # forcing the default handlers
    #
    #print(f"Following {console} {event.extra_tag}")
    ConsoleDispatcher.dispatch_select(event)
        
def follow_route_comms_select(origin_id, selected_id):
    console = "comms_target_UID"
    widget = "comms_sorted_list"
    _follow_route_console(origin_id, selected_id, console, widget, None)
        

def follow_route_science_select(origin_id, selected_id):
    console = "science_target_UID"
    widget = "science_sorted_list"
    extra_tag = "__init__"
    _follow_route_console(origin_id, selected_id, console, widget,extra_tag)

def follow_route_grid_select(origin_id, selected_id):
    console = "grid_selected_UID"
    widget = "grid_object_list"
    _follow_route_console(origin_id, selected_id, console, widget, None)


