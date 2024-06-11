from ..consoledispatcher import ConsoleDispatcher
from ..griddispatcher import GridDispatcher
from ..lifetimedispatcher import LifetimeDispatcher
from ..damagedispatcher import DamageDispatcher, CollisionDispatcher
from .execution import task_schedule
from .query import to_id, to_object
from ..mast.label import is_pymast_label

from ..helpers import FrameContext, FakeEvent
from .gui import ButtonPromise

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
_MESSAGE = 5


class HandleConsoleSelect:
    just_once = set()
    def __init__(self, console, label, etype, filter=None) -> None:
        self.console = console
        #
        # Get a scheduler to schedule future tasks
        # since the task may not be around later
        # This will be the main server scheduler
        #
        # Also avoid adding twice, e.g. each client can added the route
        #
        self.etype = etype
        self.filter = filter
        if not label in HandleConsoleSelect.just_once:
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
        self.selected(event)

    def selected(self, event):
        if self.filter is not None:
            if not self.filter:
                return

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
        
        data = {
                    f"{console}_POINT": event.source_point,
                    f"EVENT": event,
                    f"{console}_ROUTED": True
        }
        

        if event.origin_id:
            data[f"{console}_ORIGIN_ID"] = event.origin_id
            data[f"{console}_ORIGIN"] = to_object(event.origin_id)
        else:
            data[f"{console}_ORIGIN_ID"] = 0
            data[f"{console}_ORIGIN"] = None

        if event.parent_id:
            data[f"{console}_PARENT_ID"] = event.parent_id
            data[f"{console}_PARENT"] = to_object(event.parent_id)
        else:
            data[f"{console}_PARENT_ID"] = 0
            data[f"{console}_PARENT"] = None

        if event.selected_id:
            data[f"{console}_SELECTED_ID"] = event.selected_id
            data[f"{console}_SELECTED"] = to_object(event.selected_id)
        else:
            data[f"{console}_SELECTED_ID"] = 0
            data[f"{console}_SELECTED"] = None



        task = FrameContext.task
        t = task.start_task(self.label, data)
        


def route_comms_focus(label):
    """called when comms changes selection.

    Note: 
        The label called should not be long running.
        Use route_comms_select for long running tasks.

    Args:
        label (label): The label to run

    Returns:
        The route: Used rarely to cancel the route
    """    
    return HandleConsoleSelect("comms", label, _FOCUS)
    
def route_science_focus(label):
    """called when science changes selection.

    Note: 
        The label called should not be long running.
        Use route_science_select for long running tasks.

    Args:
        label (label): The label to run

    Returns:
        The route: Used rarely to cancel the route
    """    
    return HandleConsoleSelect("science", label, _FOCUS)

def route_weapons_focus(label):
    """called when weapons changes selection.

    Note: 
        The label called should not be long running.
        Use route_weapons_select for long running tasks.

    Args:
        label (label): The label to run

    Returns:
        The route: Used rarely to cancel the route
    """    
    return HandleConsoleSelect("weapons", label, _FOCUS)
        
def route_grid_focus(label):
    """called when engineering grid changes selection.

    Note: 
        The label called should not be long running.
        Use route_grid_select for long running tasks.

    Args:
        label (label): The label to run

    Returns:
        The route: Used rarely to cancel the route
    """    
    return HandleConsoleSelect("grid", label, _FOCUS)


def route_comms_select(label):
    """called when comms changes selection.
    Note:
        Typically used to run a task that uses an await comms
    
    Args:
        label (label): The label to run


    Returns:
        The route: Used rarely to cancel the route
    """    
    return HandleConsoleSelect("comms", label, _SELECT)
    



def route_comms_navigate(path, label):
    """ called to extend a comms navigation

    
    Args:
        path: (str): The navigation path to extend
        label (label): The label to run
    """
    
    if path == "":
        path = "comms"
    elif not path.startswith("comms"):
        path = f"comms/{path}"
    path_labels = ButtonPromise.navigation_map.get(path)
    if path_labels is None:
        path_labels = set()
    path_labels.add(label)
    ButtonPromise.navigation_map[path] = path_labels

def route_science_navigate(path, label):
    """ called to extend a gui navigation

    
    Args:
        path: (str): The navigation path to extend
        label (label): The label to run
    """
    path = f"sci/{path}"
    path_labels = ButtonPromise.navigation_map.get(path)
    if path_labels is None:
        path_labels = set()
    path_labels.add(label)
    ButtonPromise.navigation_map[path] = path_labels
    


def route_gui_navigate(path, label):
    """ called to extend a gui navigation

    
    Args:
        path: (str): The navigation path to extend
        label (label): The label to run
    """
    path = f"gui/{path}"
    path_labels = ButtonPromise.navigation_map.get(path)
    if path_labels is None:
        path_labels = set()
    path_labels.add(label)
    ButtonPromise.navigation_map[path] = path_labels
    
    


def route_science_select(label):
    """called when science changes selection.

    Note:
        Typically used to run a task that uses an await scan

    Args:
        label (label): The label to run

    Returns:
        The route: Used rarely to cancel the route
    """    
    return HandleConsoleSelect("science", label, _SELECT)

def route_weapons_select(label):
    """called when weapons changes selection.

    Note:
        No know use for this yet

    Args:
        label (label): The label to run

    Returns:
        The route: Used rarely to cancel the route
    """    
    return HandleConsoleSelect("weapons", label, _SELECT)
        
def route_grid_select(label):
    """called when grid changes selection.

    Note:
        Typically used to run a task that uses an await comms

    Args:
        label (label): The label to run

    Returns:
        The route: Used rarely to cancel the route
    """    
    return HandleConsoleSelect("grid", label, _SELECT)

def route_grid_object(label):
    """called when a grid object event occurs. i.e. grid object reached a location.

    Note:
        Typically not a long running task

    Args:
        label (label): The label to run

    Returns:
        The route: Used rarely to cancel the route
    """    
    return HandleConsoleSelect("grid", label, _GRID_OBJECT)


def route_comms_point(label):
    """called when a a point event occurs in comms.

    Note:
        No know use for this currently

    Args:
        label (label): The label to run

    Returns:
        The route: Used rarely to cancel the route
    """    
    return HandleConsoleSelect("comms", label, _POINT)
    
def route_science_point(label):
    """called when a a point event occurs in science by clicking the 2d view.

    Note:
        This is not intended for long running tasks

    Args:
        label (label): The label to run

    Returns:
        The route: Used rarely to cancel the route
    """    
    return HandleConsoleSelect("science", label, _POINT)

def route_weapons_point(label):
    """called when a a point event occurs in weapons by clicking the 2d view.

    Note:
        This is not intended for long running tasks

    Args:
        label (label): The label to run

    Returns:
        The route: Used rarely to cancel the route
    """    
    return HandleConsoleSelect("weapons", label, _POINT)
        
def route_grid_point(label):
    """called when a a point event occurs in the engineering grid.

    Note:
        This is not intended for long running tasks

    Args:
        label (label): The label to run

    Returns:
        The route: Used rarely to cancel the route
    """    
    return HandleConsoleSelect("grid", label, _POINT)



class HandleLifetime:
    just_once = set()
    cycles = ["SPAWNED", "SPAWNED", "DESTROYED", "DOCK"]
    def __init__(self, lifecycle, label, filter_func=None) -> None:
        #
        #
        # Also avoid adding twice, e.g. each client can added the route
        #
        if lifecycle >= len(HandleLifetime.cycles):
            return
        self.filer_func = filter_func
        self.cycle = HandleLifetime.cycles[lifecycle] 
        if not label in HandleLifetime.just_once:
            self.label = label
            HandleLifetime.just_once.add(label)
            LifetimeDispatcher.add_lifecycle(lifecycle, self.selected)
            
    def selected(self, so):
        if self.filer_func is not None:
            if not self.filer_func(so):
                return
            
        task = FrameContext.task
        if self.cycle == "DOCK":
            event = so # argument is an event
            t = task.start_task(self.label, {
                    f"{self.cycle}_ID": event.origin_id,
                    f"EVENT": event,
                    f"{self.cycle}_ROUTED": True
            })
        else:
            t = task.start_task(self.label, {
                    f"{self.cycle}_ID": so.get_id(),
                    f"{self.cycle}_OBJ": so,
                    f"{self.cycle}_ROUTED": True
            })
           #   if not .done():
        #         MastAsyncTask.add_dependency(event.origin_id,t)


        


def route_spawn(label):
    """called when a space_object is spawned.

    Args:
        label (label): The label to run

    Returns:
        The route: Used rarely to cancel the route
    """    
    return HandleLifetime(LifetimeDispatcher.SPAWN, label)

def route_grid_spawn(label):
    """called when a grid_object is spawned.

    Args:
        label (label): The label to run

    Returns:
        The route: Used rarely to cancel the route
    """    

    return HandleLifetime(LifetimeDispatcher.GRID_SPAWN, label)

def route_destroy(label):
    """called when a space_object is destroyed.

    Note:
        This is not intended for long running tasks

    Args:
        label (label): The label to run

    Returns:
        The route: Used rarely to cancel the route
    """    

    return HandleLifetime(LifetimeDispatcher.DESTROYED, label)

def route_dock(label):
    """called when a space_object docks.

    Note:
        This is not intended for long running tasks

    Args:
        label (label): The label to run

    Returns:
        The route: Used rarely to cancel the route
    """    
    return HandleLifetime(LifetimeDispatcher.DOCK, label)



class HandleDamage:
    just_once = set()

    def __init__(self, damage_type, label, ff=None) -> None:
        #
        #
        # Also avoid adding twice, e.g. each client can added the route
        #
        
        if not label in HandleDamage.just_once:
            self.label = label
            HandleDamage.just_once.add(label)
            if damage_type==DamageDispatcher._HEAT:
                DamageDispatcher.add_any_heat(self.selected)
            elif damage_type==DamageDispatcher._INTERNAL:
                DamageDispatcher.add_any_internal(self.selected)
            else:
                DamageDispatcher.add_any(self.selected)
            
    def selected(self, event):
        task = FrameContext.task
        
        t = task.start_task(self.label, {
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
    """called when a player ship takes heat damage.

    Note:
        This is not intended for long running tasks

    Args:
        label (label): The label to run

    Returns:
        The route: Used rarely to cancel the route
    """    
    return HandleDamage(DamageDispatcher._HEAT, label)

def route_damage_internal(label):
    """called when a player ship takes internal damage.

    Note:
        This is not intended for long running tasks

    Args:
        label (label): The label to run

    Returns:
        The route: Used rarely to cancel the route
    """    
    return HandleDamage(DamageDispatcher._INTERNAL, label)

def route_damage_object(label):
    """called when a space_object takes hull damage.

    Note:
        This is not intended for long running tasks

    Args:
        label (label): The label to run

    Returns:
        The route: Used rarely to cancel the route
    """    
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
    """called when a space_object takes a collision.

    Note:
        This is not intended for long running tasks

    Args:
        label (label): The label to run

    Returns:
        The route: Used rarely to cancel the route
    """    
    return HandleCollision(label)

def route_change_console(label):
    """called when a  change console button is pressed.

    Note:
        Typically this redirects the console gui to a console selection gui.

    Args:
        label (label): The label to run

    Returns:
        The route: Used rarely to cancel the route
    """    
    page = FrameContext.page
    page.change_console_label = label

def route_main_screen_change(label):
    """called when a  change to the main screen view occurs

    Note:
        Typically this redirects the console gui to a gui_console

    Args:
        label (label): The label to run

    Returns:
        The route: Used rarely to cancel the route
    """    
    page = FrameContext.page
    page.main_screen_change_label = label


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
    """ cause the comms selection route to execute

    Args:
        origin_id (agent): The agent id of the player ship
        selected_id (agent): The agent id of the target space object
    """    
    console = "comms_target_UID"
    widget = "comms_sorted_list"
    _follow_route_console(origin_id, selected_id, console, widget, None)
        

def follow_route_science_select(origin_id, selected_id):
    """ cause the science selection route to execute

    Args:
        origin_id (agent): The agent id of the player ship
        selected_id (agent): The agent id of the target space object
    """        
    console = "science_target_UID"
    widget = "science_sorted_list"
    extra_tag = "__init__"
    _follow_route_console(origin_id, selected_id, console, widget,extra_tag)

def follow_route_grid_select(origin_id, selected_id):
    """ cause the engineering grid selection route to execute

    Args:
        origin_id (agent): The agent id of the player ship
        selected_id (agent): The agent id of the target grid object
    """    
    console = "grid_selected_UID"
    widget = "grid_object_list"
    _follow_route_console(origin_id, selected_id, console, widget, None)


import inspect
#######################################
# Decorators for agent classes
#######################################
class RouteLifetime(object):
    def __init__(self, method, etype):
        s = method.__qualname__.split(".")
        self.cls = None
        ff = None
        if len(s)  == 2:
            self.cls == s[0]
            ff = self.filter_cls
        HandleLifetime(etype, method, ff)

    def filter_cls(self, so):
        if self.cls is None:
            return True
        if so is None:
            return False
        return self.cls is None or self.cls==so.__class__.__name__

class RouteSpawn(RouteLifetime):
    """ decorator for routing to a python function or python class method

    ??? Note
        The route is expected to be a label

    ??? Example
        ``` py
        @RouteSpawn
        @label
        def handle_spawn():
            ....
            yield PollResults.OK_YIELD
        ```

    """        
    def __init__(self, method):
        super().__init__(method, LifetimeDispatcher.SPAWN)


class RouteGridSpawn(RouteLifetime):
    """ decorator for routing to a python function or python class method

    Note:
        The route is expected to be a label

    ??? Example
        ``` py
        @RouteGridSpawn
        @label
        def handle_grid_spawn():
            ....
            yield PollResults.OK_YIELD
        ```

    """        
    def __init__(self, method):
        super().__init__(method, LifetimeDispatcher.GRID_SPAWN)

class RouteDestroy(RouteLifetime):
    """ decorator for routing to a python function or python class method

    Note:
        The route is expected to be a label

    ??? Example
        ``` py
        @RouteDestroy
        @label
        def handle_destroy():
            ....
            yield PollResults.OK_YIELD
        ```

    """        
    def __init__(self, method):
        super().__init__(method, LifetimeDispatcher.DESTROYED)

class RouteDock(RouteLifetime):
    """ decorator for routing to a python function or python class method

    Note:
        The route is expected to be a label

    ??? Example
        ``` py
        @RouteDock
        @label
        def handle_dock():
            ....
            yield PollResults.OK_YIELD
        ```
    """        
    def __init__(self, method):
        super().__init__(method, LifetimeDispatcher.DOCK)


class RouteConsole(object):
    def __init__(self, method, console, etype):
        s = method.__qualname__.split(".")
        self.cls = None
        if len(s)  == 2:
            self.cls == s[0]
        ff = None
        if self.cls is not None: 
            ff = self.filter_cls
        self.method = method

        HandleConsoleSelect(console, method, etype, ff)
        #if self.cls is None or self.cls==so.__class__.__name__:
        #    self.method(so, event)

    def filter_cls(self, event):
        if self.cls is None:
            return True
        so = to_object(event.origin_id)
        if so is None:
            return False
        return self.cls is None or self.cls==so.__class__.__name__





class RouteCommsSelect(RouteConsole):
    """ decorator for routing to a python function or python class method

    Note:
        The route is expected to be a label

    ??? Example
        ``` py
        @RouteCommsSelect
        @label
        def handle_comms_select():
            ....
            yield PollResults.OK_YIELD
        ```
    """            
    def __init__(self, method):
        super().__init__(method, "comms", _SELECT)

class RouteCommsFocus(RouteConsole):
    """ decorator for routing to a python function or python class method

    Note:
        The route is expected to be a label

    ??? Example
        ``` py
        @RouteCommsFocus
        @label
        def handle_comms_focus():
            ....
            yield PollResults.OK_YIELD
        ```
    """        
    def __init__(self, method):
        super().__init__(method, "comms", _FOCUS)

class RouteCommsMessage(RouteConsole):
    """ decorator for routing to a python function or python class method

    Note:
        The route is expected to be a label

    ??? Example
        ``` py
        @RouteCommsMessage
        @label
        def handle_comms_message():
            ....
            yield PollResults.OK_YIELD
        ```
    """        
    def __init__(self, method):
        super().__init__(method, "comms", _MESSAGE)





class RouteGridSelect(RouteConsole):
    """ decorator for routing to a python function or python class method

    Note:
        The route is expected to be a label

    ??? Example
        ``` py
        @RouteGridSelect
        @label
        def handle_grid_select():
            ....
            yield PollResults.OK_YIELD
        ```
    """            
    def __init__(self, method):
        super().__init__(method, "grid", _SELECT)

class RouteGridFocus(RouteConsole):
    """ decorator for routing to a python function or python class method

    Note:
        The route is expected to be a label

    ??? Example
        ``` py
        @RouteGridFocus
        @label
        def handle_grid_focus():
            ....
            yield PollResults.OK_YIELD
        ```
    """            
    def __init__(self, method):
        super().__init__(method, "grid", _FOCUS)

class RouteGridMessage(RouteConsole):
    """ decorator for routing to a python function or python class method

    Note:
        The route is expected to be a label

    ??? Example
        ``` py
        @RouteGridMessage
        @label
        def handle_grid_message():
            ....
            yield PollResults.OK_YIELD
        ```
    """            
    def __init__(self, method):
        super().__init__(method, "grid", _MESSAGE)

class RouteGridPoint(RouteConsole):
    """ decorator for routing to a python function or python class method

    Note:
        The route is expected to be a label

    ??? Example
        ``` py
        @RouteGridPoint
        @label
        def handle_grid_point():
            ....
            yield PollResults.OK_YIELD
        ```
    """            
    def __init__(self, method):
        super().__init__(method, "grid", _POINT)


class RouteScienceSelect(RouteConsole):
    """ decorator for routing to a python function or python class method

    Note:
        The route is expected to be a label

    ??? Example
        ``` py
        @RouteScienceSelect
        @label
        def handle_science_select():
            ....
            yield PollResults.OK_YIELD
        ```
    """            
    def __init__(self, method):
        super().__init__(method, "science", _SELECT)

class RouteScienceFocus(RouteConsole):
    """ decorator for routing to a python function or python class method

    Note:
        The route is expected to be a label

    ??? Example
        ``` py
        @RouteScienceFocus
        @label
        def handle_science_focus():
            ....
            yield PollResults.OK_YIELD
        ```
    """                
    def __init__(self, method):
        super().__init__(method, "science", _FOCUS)

class RouteScienceMessage(RouteConsole):
    """ decorator for routing to a python function or python class method

    Note:
        The route is expected to be a label

    ??? Example
        ``` py
        @RouteScienceMessage
        @label
        def handle_science_message():
            ....
            yield PollResults.OK_YIELD
        ```
    """                
    def __init__(self, method):
        super().__init__(method, "science", _MESSAGE)

class RouteSciencePoint(RouteConsole):
    """ decorator for routing to a python function or python class method

    Note:
        The route is expected to be a label

    ??? Example
        ``` py
        @RouteSciencePoint
        @label
        def handle_science_point():
            ....
            yield PollResults.OK_YIELD
        ```
    """                
    def __init__(self, method):
        super().__init__(method, "science", _POINT)


class RouteWeaponsSelect(RouteConsole):
    """ decorator for routing to a python function or python class method

    Note:
        The route is expected to be a label

    ??? Example
        ``` py
        @RouteWeaponsSelect
        @label
        def handle_weapons_select():
            ....
            yield PollResults.OK_YIELD
        ```
    """                
    def __init__(self, method):
        super().__init__(method, "weapons", _SELECT)

# class RouteWeaponsMessage(RouteConsole):
#     def __init__(self, method):
#         super().__init__(method, "weapons", _MESSAGE)


class RouteWeaponsFocus(RouteConsole):
    """ decorator for routing to a python function or python class method

    Note:
        The route is expected to be a label

    ??? Example
        ``` py
        @RouteWeaponsFocus
        @label
        def handle_weapons_focus():
            ....
            yield PollResults.OK_YIELD
        ```
    """
    def __init__(self, method):
        super().__init__(method, "weapons", _FOCUS)



class RouteWeaponsPoint(RouteConsole):
    """ decorator for routing to a python function or python class method

    Note:
        The route is expected to be a label

    ??? Example
        ``` py
        @RouteWeaponsPoint
        @label
        def handle_weapons_point():
            ....
            yield PollResults.OK_YIELD
        ```
    """                
    def __init__(self, method):
        super().__init__(method, "weapons", _POINT)





class RouteDamageSource(object):
    def __init__(self, method, damage_type):
        s = method.__qualname__.split(".")
        self.cls = None
        if len(s)  == 2:
            self.cls == s[0]
        ff = None
        if self.cls is not None:
            ff = self.filter_func

        self.method = method
        HandleDamage(damage_type, method, ff)

    def filter_func(self, event):
        if self.cls is None:
            return True
        so = to_object(event.origin_id)
        if so is None:
            return False
        return self.cls is None or self.cls==so.__class__.__name__        
        

class RouteDamageObject(RouteDamageSource):
    """ decorator for routing to a python function or python class method

    Note:
        The route is expected to be a label

    ??? Example
        ``` py
        @RouteDamageObject
        @label
        def handle_damage_object():
            ....
            yield PollResults.OK_YIELD
        ```
    """    
    def __init__(self, method):
        super().__init__(method, DamageDispatcher._HULL)

class RouteDamageHeat(RouteDamageSource):
    """ decorator for routing to a python function or python class method

    Note:
        The route is expected to be a label

    ??? Example
        ``` py
        @RouteDamageHeat
        @label
        def handle_damage_heat():
            ....
            yield PollResults.OK_YIELD
        ```
    """        
    def __init__(self, method):
        super().__init__(method, DamageDispatcher._HEAT)

class RouteDamageInternal(RouteDamageSource):
    """ decorator for routing to a python function or python class method

    Note:
        The route is expected to be a label

    ??? Example
        ``` py
        @RouteDamageInternal
        @label
        def handle_damage_internal():
            ....
            yield PollResults.OK_YIELD
        ```
    """        
    def __init__(self, method):
        super().__init__(method, DamageDispatcher._INTERNAL)

        