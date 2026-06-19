from sbs_utils.procedural.gui.gui import ButtonPromise
from sbs_utils.damagedispatcher import CollisionDispatcher
from sbs_utils.damagedispatcher import DamageDispatcher
from sbs_utils.consoledispatcher import ConsoleDispatcher
from sbs_utils.helpers import FakeEvent
from sbs_utils.helpers import FrameContext
from sbs_utils.griddispatcher import GridDispatcher
from sbs_utils.launchdispatcher import LaunchDispatcher
from sbs_utils.lifetimedispatcher import LifetimeDispatcher
def _follow_route_console (origin_id, selected_id, console, widget, extra_tag):
    ...
def follow_route_select_comms (origin_id, selected_id):
    """Programmatically fire the comms selection route as if the player made a selection.
    
    Args:
        origin_id (Agent | int): The player ship agent ID or object.
        selected_id (Agent | int): The target space object agent ID or object."""
def follow_route_select_grid (origin_id, selected_id):
    """Programmatically fire the grid selection route as if the player made a selection.
    
    Args:
        origin_id (Agent | int): The player ship agent ID or object.
        selected_id (Agent | int): The target grid object agent ID or object."""
def follow_route_select_science (origin_id, selected_id):
    """Programmatically fire the science selection route as if the player made a selection.
    
    Args:
        origin_id (Agent | int): The player ship agent ID or object.
        selected_id (Agent | int): The target space object agent ID or object."""
def get_inventory_value (id_or_object, key: str, default=None):
    """Get an inventory value from an agent by key.
    
    Args:
        id_or_object (Agent | int): The agent ID or object.
        key (str): The inventory key.
        default (any, optional): Value returned when the key is absent.
            Defaults to None.
    
    Returns:
        any: The inventory value, or ``default`` if the key is not set."""
def route_change_console (label):
    """Set the label shown when the "change console" button is pressed.
    
    Typically redirects the console GUI to a console-selection screen.
    
    Args:
        label (str | Label): The label to display."""
def route_collision_interactive (label):
    """Run a label each time an interactive collision event occurs.
    
    Not intended for long-running tasks.
    
    Args:
        label (str | Label): The label to run.
    
    Returns:
        HandleCollision: Route handle (rarely needed to cancel the route)."""
def route_collision_passive (label):
    """Run a label each time a passive space object is involved in a collision.
    
    Not intended for long-running tasks.
    
    Args:
        label (str | Label): The label to run.
    
    Returns:
        HandleCollision: Route handle (rarely needed to cancel the route)."""
def route_common_navigate (path, label):
    """Register a label under a navigation path in the button navigation map.
    
    Args:
        path (str): The navigation path key to extend.
        label (str | Label): The label to add under that path."""
def route_comms_navigate (path, label):
    """Register a label under a comms navigation path (auto-prefixes ``comms/``).
    
    Args:
        path (str): Navigation sub-path (e.g. ``"hail"`` → ``"comms/hail"``).
            Pass ``""`` to register at the root comms path.
        label (str | Label): The label to add under that path."""
def route_console_mainscreen_change (label):
    """Set the label shown when the main-screen view changes.
    
    Typically redirects the console GUI to a ``gui_console`` view.
    
    Args:
        label (str | Label): The label to display."""
def route_damage_destroy (label):
    """Run a label each time a space object is destroyed. Not for long-running tasks.
    
    Args:
        label (str | Label): The label to run.
    
    Returns:
        HandleLifetime: Route handle (rarely needed to cancel the route)."""
def route_damage_heat (label):
    """Run a label each time a player ship takes heat damage. Not for long-running tasks.
    
    Args:
        label (str | Label): The label to run.
    
    Returns:
        HandleDamage: Route handle (rarely needed to cancel the route)."""
def route_damage_internal (label):
    """Run a label each time a player ship takes internal damage. Not for long-running tasks.
    
    Args:
        label (str | Label): The label to run.
    
    Returns:
        HandleDamage: Route handle (rarely needed to cancel the route)."""
def route_damage_killed (label):
    """Run a label when a space object is about to be removed from the engine.
    
    Not intended for long-running tasks.
    
    Args:
        label (str | Label): The label to run.
    
    Returns:
        HandleDamage: Route handle (rarely needed to cancel the route)."""
def route_damage_object (label):
    """Run a label each time a space object takes hull damage. Not for long-running tasks.
    
    Args:
        label (str | Label): The label to run.
    
    Returns:
        HandleDamage: Route handle (rarely needed to cancel the route)."""
def route_dock_hangar (label):
    """Run a label each time a space object docks. Not for long-running tasks.
    
    Args:
        label (str | Label): The label to run.
    
    Returns:
        HandleLifetime: Route handle (rarely needed to cancel the route)."""
def route_focus_comms (label):
    """Run a label on every comms selection change (not for long-running tasks).
    
    Use ``route_select_comms`` for tasks that need to await.
    
    Args:
        label (str | Label): The label to run.
    
    Returns:
        HandleConsoleSelect: Route handle (rarely needed to cancel the route)."""
def route_focus_comms_2d (label):
    """Run a label on every 2D-comms selection change (not for long-running tasks).
    
    Use ``route_select_comms`` for tasks that need to await.
    
    Args:
        label (str | Label): The label to run.
    
    Returns:
        HandleConsoleSelect: Route handle (rarely needed to cancel the route)."""
def route_focus_grid (label):
    """Run a label on every engineering-grid selection change (not for long-running tasks).
    
    Use ``route_select_grid`` for tasks that need to await.
    
    Args:
        label (str | Label): The label to run.
    
    Returns:
        HandleConsoleSelect: Route handle (rarely needed to cancel the route)."""
def route_focus_normal (label):
    """Run a label on every normal-view selection change (not for long-running tasks).
    
    Use ``route_select_comms`` for tasks that need to await.
    
    Args:
        label (str | Label): The label to run.
    
    Returns:
        HandleConsoleSelect: Route handle (rarely needed to cancel the route)."""
def route_focus_science (label):
    """Run a label on every science selection change (not for long-running tasks).
    
    Use ``route_select_science`` for tasks that need to await.
    
    Args:
        label (str | Label): The label to run.
    
    Returns:
        HandleConsoleSelect: Route handle (rarely needed to cancel the route)."""
def route_focus_weapons (label):
    """Run a label on every weapons selection change (not for long-running tasks).
    
    Use ``route_select_weapons`` for tasks that need to await.
    
    Args:
        label (str | Label): The label to run.
    
    Returns:
        HandleConsoleSelect: Route handle (rarely needed to cancel the route)."""
def route_gui_navigate (path, label):
    """Register a label under a GUI navigation path (auto-prefixes ``gui/``).
    
    Args:
        path (str): Navigation sub-path. Pass ``""`` to register at the root
            GUI path.
        label (str | Label): The label to add under that path."""
def route_launch_drone (label):
    """Run a label each time a drone is launched. Not for long-running tasks.
    
    Args:
        label (str | Label): The label to run.
    
    Returns:
        HandleLaunch: Route handle (rarely needed to cancel the route)."""
def route_launch_missile (label):
    """Run a label each time a missile is launched. Not for long-running tasks.
    
    Args:
        label (str | Label): The label to run.
    
    Returns:
        HandleLaunch: Route handle (rarely needed to cancel the route)."""
def route_message_science (label):
    """Run a label on each science message event. Supports ``await scan``.
    
    Args:
        label (str | Label): The label to run.
    
    Returns:
        HandleConsoleSelect: Route handle (rarely needed to cancel the route)."""
def route_object_grid (label):
    """Run a label when a grid-object event fires (e.g. object arrives at a location).
    
    Not intended for long-running tasks.
    
    Args:
        label (str | Label): The label to run.
    
    Returns:
        HandleConsoleSelect: Route handle (rarely needed to cancel the route)."""
def route_point_comms (label):
    """Run a label when a point (click) event occurs on the comms view.
    
    Args:
        label (str | Label): The label to run.
    
    Returns:
        HandleConsoleSelect: Route handle (rarely needed to cancel the route)."""
def route_point_comms_2d (label):
    """Run a label when a point (click) event occurs on the 2D comms view.
    
    Args:
        label (str | Label): The label to run.
    
    Returns:
        HandleConsoleSelect: Route handle (rarely needed to cancel the route)."""
def route_point_grid (label):
    """Run a label when a point (click) event occurs on the engineering grid.
    
    Not intended for long-running tasks.
    
    Args:
        label (str | Label): The label to run.
    
    Returns:
        HandleConsoleSelect: Route handle (rarely needed to cancel the route)."""
def route_point_normal (label):
    """Run a label when a point (click) event occurs on the normal view.
    
    Args:
        label (str | Label): The label to run.
    
    Returns:
        HandleConsoleSelect: Route handle (rarely needed to cancel the route)."""
def route_point_science (label):
    """Run a label when a point (click) event occurs on the science 2D view.
    
    Not intended for long-running tasks.
    
    Args:
        label (str | Label): The label to run.
    
    Returns:
        HandleConsoleSelect: Route handle (rarely needed to cancel the route)."""
def route_point_weapons (label):
    """Run a label when a point (click) event occurs on the weapons 2D view.
    
    Not intended for long-running tasks.
    
    Args:
        label (str | Label): The label to run.
    
    Returns:
        HandleConsoleSelect: Route handle (rarely needed to cancel the route)."""
def route_science_navigate (path, label):
    """Register a label under a science navigation path (auto-prefixes ``science/``).
    
    Args:
        path (str): Navigation sub-path. Pass ``""`` to register at the root
            science path.
        label (str | Label): The label to add under that path."""
def route_select_comms (label):
    """Run a label each time a comms selection is made. Supports ``await comms``.
    
    Args:
        label (str | Label): The label to run.
    
    Returns:
        HandleConsoleSelect: Route handle (rarely needed to cancel the route)."""
def route_select_comms_2d (label):
    """Run a label each time a 2D-comms selection is made. Supports ``await comms``.
    
    Args:
        label (str | Label): The label to run.
    
    Returns:
        HandleConsoleSelect: Route handle (rarely needed to cancel the route)."""
def route_select_grid (label):
    """Run a label each time an engineering-grid selection is made. Supports ``await``.
    
    Args:
        label (str | Label): The label to run.
    
    Returns:
        HandleConsoleSelect: Route handle (rarely needed to cancel the route)."""
def route_select_normal (label):
    """Run a label each time a normal-view selection is made. Supports ``await comms``.
    
    Args:
        label (str | Label): The label to run.
    
    Returns:
        HandleConsoleSelect: Route handle (rarely needed to cancel the route)."""
def route_select_science (label):
    """Run a label each time a science selection is made. Supports ``await scan``.
    
    Args:
        label (str | Label): The label to run.
    
    Returns:
        HandleConsoleSelect: Route handle (rarely needed to cancel the route)."""
def route_select_weapons (label):
    """Run a label each time a weapons selection is made.
    
    Args:
        label (str | Label): The label to run.
    
    Returns:
        HandleConsoleSelect: Route handle (rarely needed to cancel the route)."""
def route_spawn (label):
    """Run a label each time a space object is spawned.
    
    Args:
        label (str | Label): The label to run.
    
    Returns:
        HandleLifetime: Route handle (rarely needed to cancel the route)."""
def route_spawn_grid (label):
    """Run a label each time a grid object is spawned.
    
    Args:
        label (str | Label): The label to run.
    
    Returns:
        HandleLifetime: Route handle (rarely needed to cancel the route)."""
def to_id (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Extract the integer ID from an agent, ``CloseData``, ``SpawnData``, or bare int.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to convert.
    
    Returns:
        int: The integer agent ID."""
def to_object (other: sbs_utils.agent.Agent | sbs_utils.agent.CloseData | int):
    """Resolve an ID, ``CloseData``, or ``SpawnData`` to its Agent object.
    
    Returns ``None`` when the agent no longer exists.
    
    Args:
        other (Agent | CloseData | SpawnData | int): Value to resolve.
    
    Returns:
        Agent | None: The agent, or ``None`` if it could not be resolved."""
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
class HandleLaunch(object):
    """class HandleLaunch"""
    def __init__ (self, launch_type, label) -> None:
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
class RouteLaunchDrone(object):
    """decorator for routing to a python function or python class method
    
    Note:
        The route is expected to be a label
    
    ??? Example
        ``` py
        @RouteLaunchDrone
        @label
        def handle_drone_launch():
            ....
            yield PollResults.OK_YIELD
        ```"""
    def __init__ (self, method):
        """Initialize self.  See help(type(self)) for accurate signature."""
class RouteLaunchMissile(object):
    """decorator for routing to a python function or python class method
    
    Note:
        The route is expected to be a label
    
    ??? Example
        ``` py
        @RouteLaunchMissile
        @label
        def handle_missile_launch():
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
