from sbs_utils.procedural.gui import ButtonPromise
from sbs_utils.damagedispatcher import CollisionDispatcher
from sbs_utils.damagedispatcher import DamageDispatcher
from sbs_utils.consoledispatcher import ConsoleDispatcher
from sbs_utils.helpers import FakeEvent
from sbs_utils.helpers import FrameContext
from sbs_utils.griddispatcher import GridDispatcher
from sbs_utils.lifetimedispatcher import LifetimeDispatcher
def _follow_route_console (origin_id, selected_id, console, widget, extra_tag):
    ...
def follow_route_select_comms (origin_id, selected_id):
    """cause the comms selection route to execute
    
    Args:
        origin_id (agent): The agent id of the player ship
        selected_id (agent): The agent id of the target space object"""
def follow_route_select_grid (origin_id, selected_id):
    """cause the engineering grid selection route to execute
    
    Args:
        origin_id (agent): The agent id of the player ship
        selected_id (agent): The agent id of the target grid object"""
def follow_route_select_science (origin_id, selected_id):
    """cause the science selection route to execute
    
    Args:
        origin_id (agent): The agent id of the player ship
        selected_id (agent): The agent id of the target space object"""
def route_change_console (label):
    """called when a  change console button is pressed.
    
    Note:
        Typically this redirects the console gui to a console selection gui.
    
    Args:
        label (label): The label to run
    
    Returns:
        The route: Used rarely to cancel the route"""
def route_collision_interactive (label):
    """called when a space_object takes a collision.
    
    Note:
        This is not intended for long running tasks
    
    Args:
        label (label): The label to run
    
    Returns:
        The route: Used rarely to cancel the route"""
def route_collision_passive (label):
    """called when a space_object takes a collision.
    
    Note:
        This is not intended for long running tasks
    
    Args:
        label (label): The label to run
    
    Returns:
        The route: Used rarely to cancel the route"""
def route_comms_navigate (path, label):
    """called to extend a comms navigation
    
    
    Args:
        path: (str): The navigation path to extend
        label (label): The label to run"""
def route_console_mainscreen_change (label):
    """called when a  change to the main screen view occurs
    
    Note:
        Typically this redirects the console gui to a gui_console
    
    Args:
        label (label): The label to run
    
    Returns:
        The route: Used rarely to cancel the route"""
def route_damage_destroy (label):
    """called when a space_object is destroyed.
    
    Note:
        This is not intended for long running tasks
    
    Args:
        label (label): The label to run
    
    Returns:
        The route: Used rarely to cancel the route"""
def route_damage_heat (label):
    """called when a player ship takes heat damage.
    
    Note:
        This is not intended for long running tasks
    
    Args:
        label (label): The label to run
    
    Returns:
        The route: Used rarely to cancel the route"""
def route_damage_internal (label):
    """called when a player ship takes internal damage.
    
    Note:
        This is not intended for long running tasks
    
    Args:
        label (label): The label to run
    
    Returns:
        The route: Used rarely to cancel the route"""
def route_damage_killed (label):
    """called when a space_object is about to be removed from the engine.
    
    Note:
        This is not intended for long running tasks
    
    Args:
        label (label): The label to run
    
    Returns:
        The route: Used rarely to cancel the route"""
def route_damage_object (label):
    """called when a space_object takes hull damage.
    
    Note:
        This is not intended for long running tasks
    
    Args:
        label (label): The label to run
    
    Returns:
        The route: Used rarely to cancel the route"""
def route_dock_hangar (label):
    """called when a space_object docks.
    
    Note:
        This is not intended for long running tasks
    
    Args:
        label (label): The label to run
    
    Returns:
        The route: Used rarely to cancel the route"""
def route_focus_comms (label):
    """called when comms changes selection.
    
    Note:
        The label called should not be long running.
        Use route_select_comms for long running tasks.
    
    Args:
        label (label): The label to run
    
    Returns:
        The route: Used rarely to cancel the route"""
def route_focus_comms_2d (label):
    """called when comms changes selection.
    
    Note:
        The label called should not be long running.
        Use route_select_comms for long running tasks.
    
    Args:
        label (label): The label to run
    
    Returns:
        The route: Used rarely to cancel the route"""
def route_focus_grid (label):
    """called when engineering grid changes selection.
    
    Note:
        The label called should not be long running.
        Use route_select_grid for long running tasks.
    
    Args:
        label (label): The label to run
    
    Returns:
        The route: Used rarely to cancel the route"""
def route_focus_normal (label):
    """called when comms changes selection.
    
    Note:
        The label called should not be long running.
        Use route_select_comms for long running tasks.
    
    Args:
        label (label): The label to run
    
    Returns:
        The route: Used rarely to cancel the route"""
def route_focus_science (label):
    """called when science changes selection.
    
    Note:
        The label called should not be long running.
        Use route_select_science for long running tasks.
    
    Args:
        label (label): The label to run
    
    Returns:
        The route: Used rarely to cancel the route"""
def route_focus_weapons (label):
    """called when weapons changes selection.
    
    Note:
        The label called should not be long running.
        Use route_select_weapons for long running tasks.
    
    Args:
        label (label): The label to run
    
    Returns:
        The route: Used rarely to cancel the route"""
def route_gui_navigate (path, label):
    """called to extend a gui navigation
    
    
    Args:
        path: (str): The navigation path to extend
        label (label): The label to run"""
def route_message_science (label):
    """called when science changes selection.
    
    Note:
        Typically used to run a task that uses an await scan
    
    Args:
        label (label): The label to run
    
    Returns:
        The route: Used rarely to cancel the route"""
def route_object_grid (label):
    """called when a grid object event occurs. i.e. grid object reached a location.
    
    Note:
        Typically not a long running task
    
    Args:
        label (label): The label to run
    
    Returns:
        The route: Used rarely to cancel the route"""
def route_point_comms (label):
    """called when a a point event occurs in comms.
    
    Note:
        No know use for this currently
    
    Args:
        label (label): The label to run
    
    Returns:
        The route: Used rarely to cancel the route"""
def route_point_comms_2d (label):
    """called when a a point event occurs in comms.
    
    Note:
        No know use for this currently
    
    Args:
        label (label): The label to run
    
    Returns:
        The route: Used rarely to cancel the route"""
def route_point_grid (label):
    """called when a a point event occurs in the engineering grid.
    
    Note:
        This is not intended for long running tasks
    
    Args:
        label (label): The label to run
    
    Returns:
        The route: Used rarely to cancel the route"""
def route_point_normal (label):
    """called when a a point event occurs in comms.
    
    Note:
        No know use for this currently
    
    Args:
        label (label): The label to run
    
    Returns:
        The route: Used rarely to cancel the route"""
def route_point_science (label):
    """called when a a point event occurs in science by clicking the 2d view.
    
    Note:
        This is not intended for long running tasks
    
    Args:
        label (label): The label to run
    
    Returns:
        The route: Used rarely to cancel the route"""
def route_point_weapons (label):
    """called when a a point event occurs in weapons by clicking the 2d view.
    
    Note:
        This is not intended for long running tasks
    
    Args:
        label (label): The label to run
    
    Returns:
        The route: Used rarely to cancel the route"""
def route_science_navigate (path, label):
    """called to extend a gui navigation
    
    
    Args:
        path: (str): The navigation path to extend
        label (label): The label to run"""
def route_select_comms (label):
    """called when comms changes selection.
    Note:
        Typically used to run a task that uses an await comms
    
    Args:
        label (label): The label to run
    
    
    Returns:
        The route: Used rarely to cancel the route"""
def route_select_comms_2d (label):
    """called when comms changes selection.
    Note:
        Typically used to run a task that uses an await comms
    
    Args:
        label (label): The label to run
    
    
    Returns:
        The route: Used rarely to cancel the route"""
def route_select_grid (label):
    """called when grid changes selection.
    
    Note:
        Typically used to run a task that uses an await comms
    
    Args:
        label (label): The label to run
    
    Returns:
        The route: Used rarely to cancel the route"""
def route_select_normal (label):
    """called when comms changes selection.
    Note:
        Typically used to run a task that uses an await comms
    
    Args:
        label (label): The label to run
    
    
    Returns:
        The route: Used rarely to cancel the route"""
def route_select_science (label):
    """called when science changes selection.
    
    Note:
        Typically used to run a task that uses an await scan
    
    Args:
        label (label): The label to run
    
    Returns:
        The route: Used rarely to cancel the route"""
def route_select_weapons (label):
    """called when weapons changes selection.
    
    Note:
        No know use for this yet
    
    Args:
        label (label): The label to run
    
    Returns:
        The route: Used rarely to cancel the route"""
def route_spawn (label):
    """called when a space_object is spawned.
    
    Args:
        label (label): The label to run
    
    Returns:
        The route: Used rarely to cancel the route"""
def route_spawn_grid (label):
    """called when a grid_object is spawned.
    
    Args:
        label (label): The label to run
    
    Returns:
        The route: Used rarely to cancel the route"""
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """converts item passed to an agent id
    
    Args:
        other (Agent | CloseData | int): The agent
    
    Returns:
        id: The agent id"""
def to_object (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """converts the item passed to an agent
    
    ??? note
        Retrun of None could mean the agent no longer exists
    
    Args:
        other (Agent | CloseData | int): The agent ID or other agent like data
    
    Returns:
        agent | None: The agent or None"""
class HandleCollision(object):
    """class HandleCollision"""
    def __init__ (self, coll_type, label) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def selected (self, event):
        ...
class HandleConsoleSelect(object):
    """class HandleConsoleSelect"""
    def __init__ (self, console, label, etype, filter=None) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def grid_selected (self, event):
        ...
    def selected (self, event):
        ...
class HandleDamage(object):
    """class HandleDamage"""
    def __init__ (self, damage_type, label, ff=None) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def selected (self, event):
        ...
class HandleLifetime(object):
    """class HandleLifetime"""
    def __init__ (self, lifecycle, label, filter_func=None) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def selected (self, so):
        ...
class RouteCommsFocus(RouteConsole):
    """decorator for routing to a python function or python class method
    
    Note:
        The route is expected to be a label
    
    ??? Example
        ``` py
        @RouteCommsFocus
        @label
        def handle_comms_focus():
            ....
            yield PollResults.OK_YIELD
        ```"""
    def __init__ (self, method):
        """Initialize self.  See help(type(self)) for accurate signature."""
class RouteCommsMessage(RouteConsole):
    """decorator for routing to a python function or python class method
    
    Note:
        The route is expected to be a label
    
    ??? Example
        ``` py
        @RouteCommsMessage
        @label
        def handle_comms_message():
            ....
            yield PollResults.OK_YIELD
        ```"""
    def __init__ (self, method):
        """Initialize self.  See help(type(self)) for accurate signature."""
class RouteCommsSelect(RouteConsole):
    """decorator for routing to a python function or python class method
    
    Note:
        The route is expected to be a label
    
    ??? Example
        ``` py
        @RouteCommsSelect
        @label
        def handle_comms_select():
            ....
            yield PollResults.OK_YIELD
        ```"""
    def __init__ (self, method):
        """Initialize self.  See help(type(self)) for accurate signature."""
class RouteConsole(object):
    """class RouteConsole"""
    def __init__ (self, method, console, etype):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def filter_cls (self, event):
        ...
class RouteDamageDestroy(RouteLifetime):
    """decorator for routing to a python function or python class method
    
    Note:
        The route is expected to be a label
    
    ??? Example
        ``` py
        @RouteDestroy
        @label
        def handle_destroy():
            ....
            yield PollResults.OK_YIELD
        ```"""
    def __init__ (self, method):
        """Initialize self.  See help(type(self)) for accurate signature."""
class RouteDamageHeat(RouteDamageSource):
    """decorator for routing to a python function or python class method
    
    Note:
        The route is expected to be a label
    
    ??? Example
        ``` py
        @RouteDamageHeat
        @label
        def handle_damage_heat():
            ....
            yield PollResults.OK_YIELD
        ```"""
    def __init__ (self, method):
        """Initialize self.  See help(type(self)) for accurate signature."""
class RouteDamageInternal(RouteDamageSource):
    """decorator for routing to a python function or python class method
    
    Note:
        The route is expected to be a label
    
    ??? Example
        ``` py
        @RouteDamageInternal
        @label
        def handle_damage_internal():
            ....
            yield PollResults.OK_YIELD
        ```"""
    def __init__ (self, method):
        """Initialize self.  See help(type(self)) for accurate signature."""
class RouteDamageKilled(RouteLifetime):
    """decorator for routing to a python function or python class method
    
    Note:
        The route is expected to be a label
    
    ??? Example
        ``` py
        @RouteDestroy
        @label
        def handle_destroy():
            ....
            yield PollResults.OK_YIELD
        ```"""
    def __init__ (self, method):
        """Initialize self.  See help(type(self)) for accurate signature."""
class RouteDamageObject(RouteDamageSource):
    """decorator for routing to a python function or python class method
    
    Note:
        The route is expected to be a label
    
    ??? Example
        ``` py
        @RouteDamageObject
        @label
        def handle_damage_object():
            ....
            yield PollResults.OK_YIELD
        ```"""
    def __init__ (self, method):
        """Initialize self.  See help(type(self)) for accurate signature."""
class RouteDamageSource(object):
    """class RouteDamageSource"""
    def __init__ (self, method, damage_type):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def filter_func (self, event):
        ...
class RouteDockHangar(RouteLifetime):
    """decorator for routing to a python function or python class method
    
    Note:
        The route is expected to be a label
    
    ??? Example
        ``` py
        @RouteDockHangar
        @label
        def handle_dock():
            ....
            yield PollResults.OK_YIELD
        ```"""
    def __init__ (self, method):
        """Initialize self.  See help(type(self)) for accurate signature."""
class RouteGridFocus(RouteConsole):
    """decorator for routing to a python function or python class method
    
    Note:
        The route is expected to be a label
    
    ??? Example
        ``` py
        @RouteGridFocus
        @label
        def handle_grid_focus():
            ....
            yield PollResults.OK_YIELD
        ```"""
    def __init__ (self, method):
        """Initialize self.  See help(type(self)) for accurate signature."""
class RouteGridMessage(RouteConsole):
    """decorator for routing to a python function or python class method
    
    Note:
        The route is expected to be a label
    
    ??? Example
        ``` py
        @RouteGridMessage
        @label
        def handle_grid_message():
            ....
            yield PollResults.OK_YIELD
        ```"""
    def __init__ (self, method):
        """Initialize self.  See help(type(self)) for accurate signature."""
class RouteGridPoint(RouteConsole):
    """decorator for routing to a python function or python class method
    
    Note:
        The route is expected to be a label
    
    ??? Example
        ``` py
        @RouteGridPoint
        @label
        def handle_grid_point():
            ....
            yield PollResults.OK_YIELD
        ```"""
    def __init__ (self, method):
        """Initialize self.  See help(type(self)) for accurate signature."""
class RouteGridSelect(RouteConsole):
    """decorator for routing to a python function or python class method
    
    Note:
        The route is expected to be a label
    
    ??? Example
        ``` py
        @RouteGridSelect
        @label
        def handle_grid_select():
            ....
            yield PollResults.OK_YIELD
        ```"""
    def __init__ (self, method):
        """Initialize self.  See help(type(self)) for accurate signature."""
class RouteGridSpawn(RouteLifetime):
    """decorator for routing to a python function or python class method
    
    Note:
        The route is expected to be a label
    
    ??? Example
        ``` py
        @RouteGridSpawn
        @label
        def handle_grid_spawn():
            ....
            yield PollResults.OK_YIELD
        ```"""
    def __init__ (self, method):
        """Initialize self.  See help(type(self)) for accurate signature."""
class RouteLifetime(object):
    """class RouteLifetime"""
    def __init__ (self, method, etype):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def filter_cls (self, so):
        ...
class RouteScienceFocus(RouteConsole):
    """decorator for routing to a python function or python class method
    
    Note:
        The route is expected to be a label
    
    ??? Example
        ``` py
        @RouteScienceFocus
        @label
        def handle_science_focus():
            ....
            yield PollResults.OK_YIELD
        ```"""
    def __init__ (self, method):
        """Initialize self.  See help(type(self)) for accurate signature."""
class RouteScienceMessage(RouteConsole):
    """decorator for routing to a python function or python class method
    
    Note:
        The route is expected to be a label
    
    ??? Example
        ``` py
        @RouteScienceMessage
        @label
        def handle_science_message():
            ....
            yield PollResults.OK_YIELD
        ```"""
    def __init__ (self, method):
        """Initialize self.  See help(type(self)) for accurate signature."""
class RouteSciencePoint(RouteConsole):
    """decorator for routing to a python function or python class method
    
    Note:
        The route is expected to be a label
    
    ??? Example
        ``` py
        @RouteSciencePoint
        @label
        def handle_science_point():
            ....
            yield PollResults.OK_YIELD
        ```"""
    def __init__ (self, method):
        """Initialize self.  See help(type(self)) for accurate signature."""
class RouteScienceSelect(RouteConsole):
    """decorator for routing to a python function or python class method
    
    Note:
        The route is expected to be a label
    
    ??? Example
        ``` py
        @RouteScienceSelect
        @label
        def handle_science_select():
            ....
            yield PollResults.OK_YIELD
        ```"""
    def __init__ (self, method):
        """Initialize self.  See help(type(self)) for accurate signature."""
class RouteSpawn(RouteLifetime):
    """decorator for routing to a python function or python class method
    
    ??? Note
        The route is expected to be a label
    
    ??? Example
        ``` py
        @RouteSpawn
        @label
        def handle_spawn():
            ....
            yield PollResults.OK_YIELD
        ```"""
    def __init__ (self, method):
        """Initialize self.  See help(type(self)) for accurate signature."""
class RouteWeaponsFocus(RouteConsole):
    """decorator for routing to a python function or python class method
    
    Note:
        The route is expected to be a label
    
    ??? Example
        ``` py
        @RouteWeaponsFocus
        @label
        def handle_weapons_focus():
            ....
            yield PollResults.OK_YIELD
        ```"""
    def __init__ (self, method):
        """Initialize self.  See help(type(self)) for accurate signature."""
class RouteWeaponsPoint(RouteConsole):
    """decorator for routing to a python function or python class method
    
    Note:
        The route is expected to be a label
    
    ??? Example
        ``` py
        @RouteWeaponsPoint
        @label
        def handle_weapons_point():
            ....
            yield PollResults.OK_YIELD
        ```"""
    def __init__ (self, method):
        """Initialize self.  See help(type(self)) for accurate signature."""
class RouteWeaponsSelect(RouteConsole):
    """decorator for routing to a python function or python class method
    
    Note:
        The route is expected to be a label
    
    ??? Example
        ``` py
        @RouteWeaponsSelect
        @label
        def handle_weapons_select():
            ....
            yield PollResults.OK_YIELD
        ```"""
    def __init__ (self, method):
        """Initialize self.  See help(type(self)) for accurate signature."""
