
import typing
from  .engineobject import EngineObject

class LifetimeDispatcher:
    _dispatch_spawn = set()
    _dispatch_spawn_grid = set()
    _dispatch_destroy = set()
    
    def add_spawn(cb: typing.Callable):
        LifetimeDispatcher._dispatch_spawn.add(cb)

    def add_spawn_grid(cb: typing.Callable):
        LifetimeDispatcher._dispatch_spawn_grid.add(cb)

    def add_destroy(cb: typing.Callable):
        LifetimeDispatcher._dispatch_destroy.add(cb)

    def remove_spawn(cb: typing.Callable):
        # Callback should have arguments of other object's id, message
        LifetimeDispatcher._dispatch_spawn.discard(cb)

    def remove_spawn_grid(cb: typing.Callable):
        # Callback should have arguments of other object's id, message
        LifetimeDispatcher._dispatch_spawn_grid.discard(cb)

    def remove_destroy(cb: typing.Callable):
        # Callback should have arguments of other object's id, message
        LifetimeDispatcher._dispatch_destroy.discard(cb)


    def dispatch_spawn():
        objects = EngineObject.get_role_objects("__space_spawn__")
        for so in objects:
            for func in LifetimeDispatcher._dispatch_spawn:
                func(so)
            so.remove_role("__space_spawn__")

        objects = EngineObject.get_role_objects("__grid_spawn__")
        for so in objects:
            #print("A grid object spawned")
            for func in LifetimeDispatcher._dispatch_spawn_grid:
                func(so)
            so.remove_role("__grid_spawn__")



    def dispatch_damage(damage_event):
        if damage_event.sub_tag == 'destroyed':
            so:EngineObject = EngineObject.get(damage_event.selected_id)
            if so is not None:
                for func in LifetimeDispatcher._dispatch_destroy:
                    func(so)
                so.destroyed()
            
          
        

