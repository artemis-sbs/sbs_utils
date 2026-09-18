import typing


class DragDispatcher:
    """Routes console drag events (drag one object onto another) to handlers.

    The engine sends one event per console that supports dragging, e.g.
    ``comms_drag_event``: origin = the dragged object, selected = the drop
    target, parent = the player ship of the console.
    """
    COMMS = "comms"

    _dispatch_comms = set()

    @classmethod
    def clear(cls):
        """Drop all registered drag routes (fresh mission / in-process recompile)."""
        cls._dispatch_comms = set()

    def _handlers(console):
        match console:
            case DragDispatcher.COMMS:
                return DragDispatcher._dispatch_comms
        return None

    def add_comms(cb: typing.Callable):
        DragDispatcher._dispatch_comms.add(cb)

    def remove_comms(cb: typing.Callable):
        DragDispatcher._dispatch_comms.discard(cb)

    def dispatch_comms(event):
        for func in list(DragDispatcher._dispatch_comms):
            func(event)

    def add_drag(console, cb: typing.Callable):
        handlers = DragDispatcher._handlers(console)
        if handlers is not None:
            handlers.add(cb)

    def remove_drag(console, cb: typing.Callable):
        handlers = DragDispatcher._handlers(console)
        if handlers is not None:
            handlers.discard(cb)

    def dispatch_drag(console, event):
        handlers = DragDispatcher._handlers(console)
        if handlers is None:
            return
        for func in list(handlers):
            func(event)
