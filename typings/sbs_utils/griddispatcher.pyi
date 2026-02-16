class GridDispatcher(object):
    """Manages dispatch of grid-related events to registered callbacks.
    
    Provides a registry system for handling grid object interactions and point
    selections. Allows registering object-specific and point-specific callbacks
    as well as catch-all handlers for any grid event."""
    def add_any_object (cb: callable):
        """Register a catch-all callback for any grid object selection.
        
        Args:
            cb (Callable): Callback function invoked for any object selection event."""
    def add_any_point (cb: callable):
        """Register a catch-all callback for any grid point selection.
        
        Args:
            cb (Callable): Callback function invoked for any point selection event."""
    def add_object (id: int, cb: callable):
        """Register a callback for a specific grid object.
        
        Args:
            id (int): The unique identifier of the grid object.
            cb (Callable): Callback function to invoke when the object is selected."""
    def add_point (id: int, cb: callable):
        """Register a callback for a specific grid point.
        
        Args:
            id (int): The unique identifier of the grid point.
            cb (Callable): Callback function to invoke when the point is selected."""
    def dispatch_grid_event (event):
        """Dispatch a grid event to registered callbacks.
        
        Routes grid events to specific callbacks registered for object IDs or point IDs,
        and also invokes catch-all handlers.
        
        Args:
            event: The grid event object containing tag, selected_id, and origin_id."""
    def remove_any_object (cb: callable):
        """Unregister a catch-all callback for grid object selection.
        
        Args:
            cb (Callable): The callback function to remove."""
    def remove_any_point (cb: callable):
        """Unregister a catch-all callback for grid point selection.
        
        Args:
            cb (Callable): The callback function to remove."""
    def remove_object (id: int):
        """Unregister a callback for a specific grid object.
        
        Args:
            id (int): The unique identifier of the grid object to remove."""
    def remove_point (id: int):
        """Unregister a callback for a specific grid point.
        
        Args:
            id (int): The unique identifier of the grid point to remove."""
