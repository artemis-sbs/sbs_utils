
import typing
from  .agent import Agent

class LifetimeDispatcher:
    _dispatch_spawn = set()
    _dispatch_spawn_grid = set()
    _dispatch_destroy = set()
    _dispatch_dock = set()

    SPAWN = 0
    GRID_SPAWN = 1
    DESTROYED = 2
    DOCK = 3

    # The LIBRARY's own handlers, registered once at module import. `clear()` runs on
    # every mission reset, but a module is imported once per process, so a handler it
    # registered at import was never put back: in the dev runner's in-process reload
    # run 2 had no comms/science selection and leaked tasks for every destroyed object.
    # `add_library` records the call so `clear()` can replay it; mission routes, which
    # re-register when their story recompiles, are still dropped.
    _library_calls = []

    @classmethod
    def add_library(cls, method, *args):
        """Register a LIBRARY handler that must survive `clear()`.

        Args:
            method (str): The name of this class's `add_*` method to call.
            *args: Its arguments.
        """
        call = (method, args)
        if call not in cls._library_calls:
            cls._library_calls.append(call)
        getattr(cls, method)(*args)

    @classmethod
    def _replay_library(cls):
        for method, args in cls._library_calls:
            getattr(cls, method)(*args)

    @classmethod
    def clear(cls):
        """Drop all registered lifetime routes (fresh mission / in-process recompile).

        The library's own handlers (`add_library`) are put back."""
        cls._dispatch_spawn = set()
        cls._dispatch_spawn_grid = set()
        cls._dispatch_destroy = set()
        cls._dispatch_dock = set()
        cls._replay_library()

    def add_spawn(cb: typing.Callable):
        LifetimeDispatcher._dispatch_spawn.add(cb)

    def add_spawn_grid(cb: typing.Callable):
        LifetimeDispatcher._dispatch_spawn_grid.add(cb)

    def add_destroy(cb: typing.Callable):
        LifetimeDispatcher._dispatch_destroy.add(cb)
    
    def add_dock(cb: typing.Callable):
        LifetimeDispatcher._dispatch_dock.add(cb)

    
    def remove_spawn(cb: typing.Callable):
        # Callback should have arguments of other object's id, message
        LifetimeDispatcher._dispatch_spawn.discard(cb)

    def remove_spawn_grid(cb: typing.Callable):
        # Callback should have arguments of other object's id, message
        LifetimeDispatcher._dispatch_spawn_grid.discard(cb)

    def remove_destroy(cb: typing.Callable):
        # Callback should have arguments of other object's id, message
        LifetimeDispatcher._dispatch_destroy.discard(cb)
    
    def remove_dock(cb: typing.Callable):
        # Callback should have arguments of other object's id, message
        LifetimeDispatcher._dispatch_dock.discard(cb)


    def add_lifecycle(lifecycle, cb: typing.Callable):
        match lifecycle:
            case LifetimeDispatcher.SPAWN:
                LifetimeDispatcher.add_spawn(cb)
            case LifetimeDispatcher.GRID_SPAWN:
                LifetimeDispatcher.add_spawn_grid(cb)
            case LifetimeDispatcher.DESTROYED:
                LifetimeDispatcher.add_destroy(cb)
            case LifetimeDispatcher.DOCK:
                LifetimeDispatcher.add_dock(cb)


    def remove_lifecycle(lifecycle, cb: typing.Callable):
        match lifecycle:
            case LifetimeDispatcher.SPAWN:
                LifetimeDispatcher.remove_spawn(cb)
            case LifetimeDispatcher.GRID_SPAWN:
                LifetimeDispatcher.remove_spawn_grid(cb)
            case LifetimeDispatcher.DESTROYED:
                LifetimeDispatcher.remove_destroy(cb)
            case LifetimeDispatcher.DOCK:
                LifetimeDispatcher.remove_dock(cb)

    def dispatch_spawn():
        objects = Agent.get_role_objects("__space_spawn__")
        for so in objects:
            for func in LifetimeDispatcher._dispatch_spawn:
                func(so)
            so.remove_role("__space_spawn__")

        objects = Agent.get_role_objects("__grid_spawn__")
        for so in objects:
            for func in LifetimeDispatcher._dispatch_spawn_grid:
                func(so)
            so.remove_role("__grid_spawn__")

    def dispatch_dock(damage_event):
        for func in LifetimeDispatcher._dispatch_dock:
            func(damage_event)



    def dispatch_damage(damage_event):
        if damage_event.sub_tag == 'destroyed':
            so:Agent = Agent.get(damage_event.selected_id)
            if so is not None:
                # Pass the event so destroy routes can credit the killer
                # (origin_id/parent_id); spawn callbacks ignore the 2nd arg.
                for func in LifetimeDispatcher._dispatch_destroy:
                    func(so, damage_event)
                so.destroyed()
        elif damage_event.tag == 'npc_killed':
            so:Agent = Agent.get(damage_event.selected_id)
            if so is not None:
                for func in LifetimeDispatcher._dispatch_killed:
                    func(so)
                so.destroyed()
            
          
        

