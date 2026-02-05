import typing

class GridDispatcher:
    """Manages dispatch of grid-related events to registered callbacks.
    
    Provides a registry system for handling grid object interactions and point
    selections. Allows registering object-specific and point-specific callbacks
    as well as catch-all handlers for any grid event.
    """
    
    _dispatch_object = {}
    #_dispatch_object_select = {}
    _dispatch_point = {}
    _dispatch_any_point = set()
    _dispatch_any_object = set()
    
    def add_object(id: int, cb: typing.Callable):
        """Register a callback for a specific grid object.
        
        Args:
            id (int): The unique identifier of the grid object.
            cb (Callable): Callback function to invoke when the object is selected.
        """
        GridDispatcher._dispatch_object[id] = cb

    # def add_object_select(id: int, cb: typing.Callable):
    #     GridDispatcher._dispatch_object_select[id] = cb

    def add_point(id: int, cb: typing.Callable):
        """Register a callback for a specific grid point.
        
        Args:
            id (int): The unique identifier of the grid point.
            cb (Callable): Callback function to invoke when the point is selected.
        """
        GridDispatcher._dispatch_point[id] = cb

    def remove_object(id: int):
        """Unregister a callback for a specific grid object.
        
        Args:
            id (int): The unique identifier of the grid object to remove.
        """
        # Callback should have arguments of other object's id, message
        GridDispatcher._dispatch_object.pop(id)

    # def remove_object_select(id: int):
    #     # Callback should have arguments of other object's id, message
    #     GridDispatcher._dispatch_object_select.pop(id)

    def remove_point(id: int):
        """Unregister a callback for a specific grid point.
        
        Args:
            id (int): The unique identifier of the grid point to remove.
        """
        # Callback should have arguments of other object's id, message
        GridDispatcher._dispatch_point.pop(id)

    def add_any_point(cb: typing.Callable):
        """Register a catch-all callback for any grid point selection.
        
        Args:
            cb (Callable): Callback function invoked for any point selection event.
        """
        GridDispatcher._dispatch_any_point.add(cb)

    def add_any_object(cb: typing.Callable):
        """Register a catch-all callback for any grid object selection.
        
        Args:
            cb (Callable): Callback function invoked for any object selection event.
        """
        GridDispatcher._dispatch_any_object.add(cb)

    def remove_any_point(cb: typing.Callable):
        """Unregister a catch-all callback for grid point selection.
        
        Args:
            cb (Callable): The callback function to remove.
        """
        GridDispatcher._dispatch_any_point.discard(cb)

    def remove_any_object(cb: typing.Callable):
        """Unregister a catch-all callback for grid object selection.
        
        Args:
            cb (Callable): The callback function to remove.
        """
        GridDispatcher._dispatch_any_object.discard(cb)


    def dispatch_grid_event(event):
        """Dispatch a grid event to registered callbacks.
        
        Routes grid events to specific callbacks registered for object IDs or point IDs,
        and also invokes catch-all handlers.
        
        Args:
            event: The grid event object containing tag, selected_id, and origin_id.
        """
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
     

