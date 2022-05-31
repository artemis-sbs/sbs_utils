
import typing
from  .spaceobject import SpaceObject

class DamageDispatcher:
    _dispatch_source = {}
    _dispatch_target = {}
    
    def add_source(id: int, cb: typing.Callable):
        DamageDispatcher._dispatch_source[id] = cb

    def add_target(id: int, cb: typing.Callable):
        DamageDispatcher._dispatch_target[id] = cb

    def remove_source(id: int):
        # Callback should have arguments of other object's id, message
        DamageDispatcher._dispatch_source.pop(id)

    def remove_target(id: int):
        # Callback should have arguments of other object's id, message
        DamageDispatcher._dispatch_target.pop(id)

    def dispatch_damage(sim, damage_event):
        source = DamageDispatcher._dispatch_source.get(damage_event.source_id)
        target = DamageDispatcher._dispatch_target.get(damage_event.target_id)
        if damage_event.damage_type == 'destroyed':
            so:SpaceObject = SpaceObject.get(damage_event.source_id)
            if so is not None:
                so.destroyed()

        if source is not None:
            source(sim, damage_event)
        if target is not None:
            target(sim, damage_event)
        

