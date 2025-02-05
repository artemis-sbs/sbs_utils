
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
                for func in LifetimeDispatcher._dispatch_destroy:
                    func(so)
                so.destroyed()
        elif damage_event.tag == 'npc_killed':
            so:Agent = Agent.get(damage_event.selected_id)
            if so is not None:
                for func in LifetimeDispatcher._dispatch_killed:
                    func(so)
                so.destroyed()
            
          
        

