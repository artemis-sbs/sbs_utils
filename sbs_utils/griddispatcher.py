import typing

class GridDispatcher:
    _dispatch_object = {}
    #_dispatch_object_select = {}
    _dispatch_point = {}
    
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

    def dispatch_grid_event(ctx, event):
        if event.tag == 'grid_object':
            object = GridDispatcher._dispatch_object.get(event.selected_id)
            if object:
                object(ctx, event)

        ############### MOved to console
        # elif event.tag == "grid_object_selection":
        #     object_select = GridDispatcher._dispatch_object_select.get(event.selected_id)
        #     if object_select:
        #         object_select(ctx, event)
        elif event.tag == "grid_point_selection":
            point = GridDispatcher._dispatch_point.get(event.origin_id)
            if point:
                point(ctx, event)

