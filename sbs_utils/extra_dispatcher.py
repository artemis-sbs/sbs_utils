
import typing


class ClientStringDispatcher:
    """
    Low level handler for client strings
    at the Mast level this will dispatch to a promise

    """
    _dispatch_any = set()
    
    def add_any(cb: typing.Callable):
        ClientStringDispatcher._dispatch_any.add(cb)

    def remove_any(cb: typing.Callable):
        ClientStringDispatcher._dispatch_any.discard(cb)


    def dispatch(event):
        for func in list(ClientStringDispatcher._dispatch_any):
            func(event)

class HotkeyDispatcher:
    """
    Low level handler for Hot keys
    at the Mast level this will dispatch to a trigger?

    """
    _dispatch_any = set()
    
    def add_any(cb: typing.Callable):
        HotkeyDispatcher._dispatch_any.add(cb)

    def remove_any(cb: typing.Callable):
        HotkeyDispatcher._dispatch_any.discard(cb)


    def dispatch(event):
        for func in HotkeyDispatcher._dispatch_any:
            func(event)

