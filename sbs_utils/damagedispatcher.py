
import typing
from  .spaceobject import SpaceObject

class DamageDispatcher:
    _dispatch_source = {}
    _dispatch_target = {}
    _dispatch_internal = {}
    _dispatch_any = set()
    _dispatch_any_internal = set()
    
    def add_source(id: int, cb: typing.Callable):
        DamageDispatcher._dispatch_source[id] = cb

    def add_target(id: int, cb: typing.Callable):
        DamageDispatcher._dispatch_target[id] = cb

    def add_internal(id: int, cb: typing.Callable):
        DamageDispatcher._dispatch_internal[id] = cb

    def add_any(cb: typing.Callable):
        DamageDispatcher._dispatch_any.add(cb)

    def add_any_internal(cb: typing.Callable):
        DamageDispatcher._dispatch_any_internal.add(cb)

    def remove_source(id: int):
        # Callback should have arguments of other object's id, message
        DamageDispatcher._dispatch_source.pop(id)

    def remove_target(id: int):
        # Callback should have arguments of other object's id, message
        DamageDispatcher._dispatch_target.pop(id)

    def remove_internal(id: int):
        # Callback should have arguments of other object's id, message
        DamageDispatcher._dispatch_internal.pop(id)

    def remove_any(cb: typing.Callable):
        DamageDispatcher._dispatch_any.discard(cb)

    def remove_any_internal(cb: typing.Callable):
        DamageDispatcher._dispatch_any_internal.discard(cb)

    def dispatch_internal(ctx, damage_event):
        internal = DamageDispatcher._dispatch_internal.get(damage_event.origin_id)
        if  internal is not None:
            internal(ctx, damage_event)

        for func in DamageDispatcher._dispatch_any_internal:
            func(ctx, damage_event)

    def dispatch_damage(ctx, damage_event):
        parent = DamageDispatcher._dispatch_source.get(damage_event.parent_id)
        source = DamageDispatcher._dispatch_source.get(damage_event.origin_id)
        target = DamageDispatcher._dispatch_target.get(damage_event.selected_id)

        for func in DamageDispatcher._dispatch_any:
            func(ctx, damage_event)
            

        if parent is not None:
            parent(ctx, damage_event)
        if source is not None:
            source(ctx, damage_event)
        if target is not None:
            target(ctx, damage_event)
        

