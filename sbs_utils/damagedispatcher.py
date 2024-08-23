
import typing

class DamageDispatcher:
    _dispatch_source = {}
    _dispatch_target = {}
    _dispatch_internal = {}
    _dispatch_any = set()
    _dispatch_any_internal = set()
    _dispatch_heat = {}
    _dispatch_any_heat = set()
    _dispatch_killed = {}
    _dispatch_any_killed = set()

    _HULL = 1
    _INTERNAL = 2
    _HEAT = 3
    _SOURCE = 4
    _TARGET = 4
    _KILLED = 6

    

    
    def add_source(id: int, cb: typing.Callable):
        DamageDispatcher._dispatch_source[id] = cb

    def add_target(id: int, cb: typing.Callable):
        DamageDispatcher._dispatch_target[id] = cb

    def add_any(cb: typing.Callable):
        DamageDispatcher._dispatch_any.add(cb)


    def add_internal(id: int, cb: typing.Callable):
        DamageDispatcher._dispatch_internal[id] = cb

    def add_any_internal(cb: typing.Callable):
        DamageDispatcher._dispatch_any_internal.add(cb)

    def add_heat(id: int, cb: typing.Callable):
        DamageDispatcher._dispatch_heat[id] = cb
    
    def add_any_heat(cb: typing.Callable):
        DamageDispatcher._dispatch_any_heat.add(cb)
    
    def remove_source(id: int):
        # Callback should have arguments of other object's id, message
        DamageDispatcher._dispatch_source.pop(id)

    def remove_target(id: int):
        # Callback should have arguments of other object's id, message
        DamageDispatcher._dispatch_target.pop(id)

    def remove_any(cb: typing.Callable):
        DamageDispatcher._dispatch_any.discard(cb)

    def remove_internal(id: int):
        # Callback should have arguments of other object's id, message
        DamageDispatcher._dispatch_internal.pop(id)

    def remove_any_internal(cb: typing.Callable):
        DamageDispatcher._dispatch_any_internal.discard(cb)

    def remove_heat(id: int):
        # Callback should have arguments of other object's id, message
        DamageDispatcher._dispatch_heat.pop(id)

    def remove_any_heat(cb: typing.Callable):
        DamageDispatcher._dispatch_any_heat.discard(cb)

    def add_killed(id: int, cb: typing.Callable):
        DamageDispatcher._dispatch_killed[id] =cb

    def remove_killed(id :int):
        # Callback should have arguments of other object's id, message
        DamageDispatcher._dispatch_killed.pop(id)

    def add_any_killed(cb: typing.Callable):
        DamageDispatcher._dispatch_any_killed.add(cb)

    def remove_any_killed(cb: typing.Callable):
        # Callback should have arguments of other object's id, message
        DamageDispatcher._dispatch_any_killed.discard(cb)


    def dispatch_internal(damage_event):
        internal = DamageDispatcher._dispatch_internal.get(damage_event.origin_id)
        if  internal is not None:
            internal(damage_event)

        for func in DamageDispatcher._dispatch_any_internal:
            func(damage_event)

    def dispatch_heat(damage_event):
        heat_damage = DamageDispatcher._dispatch_heat.get(damage_event.origin_id)
        if  heat_damage is not None:
            heat_damage(damage_event)

        for func in DamageDispatcher._dispatch_any_heat:
            func(damage_event)

    def dispatch_killed(damage_event):
        killed_damage = DamageDispatcher._dispatch_killed.get(damage_event.origin_id)
        if  killed_damage is not None:
            killed_damage(damage_event)

        for func in DamageDispatcher._dispatch_any_killed:
            func(damage_event)

    def dispatch_damage(damage_event):
        parent = DamageDispatcher._dispatch_source.get(damage_event.parent_id)
        source = DamageDispatcher._dispatch_source.get(damage_event.origin_id)
        target = DamageDispatcher._dispatch_target.get(damage_event.selected_id)

        for func in DamageDispatcher._dispatch_any:
            func(damage_event)
            

        if parent is not None:
            parent(damage_event)
        if source is not None:
            source(damage_event)
        if target is not None:
            target(damage_event)
        

class CollisionDispatcher:
    _dispatch_passive = set()
    _dispatch_interactive = set()

    _PASSIVE = 1
    _INTERACTION = 2



    def add_passive(cb: typing.Callable):
        CollisionDispatcher._dispatch_passive.add(cb)

    def remove_passive(cb: typing.Callable):
        CollisionDispatcher._dispatch_passive.discard(cb)

    def dispatch_passive(collision_event):
        for func in CollisionDispatcher._dispatch_passive:
            func(collision_event)

    def add_interactive(cb: typing.Callable):
        CollisionDispatcher._dispatch_interactive.add(cb)

    def remove_interactive(cb: typing.Callable):
        CollisionDispatcher._dispatch_interactive.discard(cb)

    def dispatch_collision(collision_event):
        for func in CollisionDispatcher._dispatch_passive:
            func(collision_event)
        
    def dispatch_interactive(collision_event):
        for func in CollisionDispatcher._dispatch_interactive:
            func(collision_event)
            
    
