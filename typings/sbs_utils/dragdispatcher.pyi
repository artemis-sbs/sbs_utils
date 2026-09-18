class DragDispatcher(object):
    """Routes console drag events (drag one object onto another) to handlers.
    
    The engine sends one event per console that supports dragging, e.g.
    ``comms_drag_event``: origin = the dragged object, selected = the drop
    target, parent = the player ship of the console."""
    def add_comms (cb: callable):
        ...
    def add_drag (console, cb: callable):
        ...
    def clear ():
        """Drop all registered drag routes (fresh mission / in-process recompile)."""
    def dispatch_comms (event):
        ...
    def dispatch_drag (console, event):
        ...
    def remove_comms (cb: callable):
        ...
    def remove_drag (console, cb: callable):
        ...
