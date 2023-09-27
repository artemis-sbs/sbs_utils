import typing

class GridDispatcher:
    _dispatch_object = {}
    #_dispatch_object_select = {}
    _dispatch_point = {}
    _dispatch_any_point = set()
    _dispatch_any_object = set()
    
    def add_object(id: int, cb: typing.Callable):
        GridDispatcher._dispatch_object[id] = cb

    # def add_object_select(id: int, cb: typing.Callable):
    #     GridDispatcher._dispatch_object_select[id] = cb

    def add_point(id: int, cb: typing.Callable):
        GridDispatcher._dispatch_point[id] = cb

    def remove_object(id: int):
        # Callback should have arguments of other object's id, message
        GridDispatcher._dispatch_object.pop(id)

    # def remove_object_select(id: int):
    #     # Callback should have arguments of other object's id, message
    #     GridDispatcher._dispatch_object_select.pop(id)

    def remove_point(id: int):
        # Callback should have arguments of other object's id, message
        GridDispatcher._dispatch_point.pop(id)

    def add_any_point(cb: typing.Callable):
        GridDispatcher._dispatch_any_point.add(cb)

    def add_any_object(cb: typing.Callable):
        GridDispatcher._dispatch_any_object.add(cb)

    def remove_any_point(cb: typing.Callable):
        GridDispatcher._dispatch_any_point.discard(cb)

    def remove_any_object(cb: typing.Callable):
        GridDispatcher._dispatch_any_object.discard(cb)


    def dispatch_grid_event(event):
        if event.tag == 'grid_object':
            go = GridDispatcher._dispatch_object.get(event.selected_id)
            if go:
                go(event)
            else:
                for func in GridDispatcher._dispatch_any_object:
                    func(event)
     

        ############### MOved to console
        # elif event.tag == "grid_object_selection":
        #     object_select = GridDispatcher._dispatch_object_select.get(event.selected_id)
        #     if object_select:
        #         object_select(event)
        elif event.tag == "grid_point_selection":
            point = GridDispatcher._dispatch_point.get(event.origin_id)
            if point:
                point(event)
            else:
                for func in GridDispatcher._dispatch_any_point:
                    func(event)
     

