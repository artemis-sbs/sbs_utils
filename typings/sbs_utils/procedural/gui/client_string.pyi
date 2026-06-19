from sbs_utils.futures import AwaitBlockPromise
from sbs_utils.extra_dispatcher import ClientStringDispatcher
from sbs_utils.helpers import FrameContext
def gui_request_client_string (client_id, key, timeout=None):
    """Request a text string from the player via a native OS input dialog.
    
    Sends a ``request_client_string`` call to the engine for the given client.
    The engine shows an OS-level text input and returns the typed value as a
    ``client_string`` event. Suspends until the player submits or the timeout
    fires.
    
    Args:
        client_id (int): Client to prompt.
        key (str): Tag used to identify the response event (``event.sub_tag``).
        timeout (Promise, optional): A promise that cancels the request if it
            resolves first. Defaults to None.
    
    Returns:
        Promise: Resolves with the typed string as its result.
    
    Example:
        result = await gui_request_client_string(CLIENT_ID, "ship_name")
        ~~ player_name = result.result ~~"""
class ClientStringPromise(AwaitBlockPromise):
    """class ClientStringPromise"""
    def __init__ (self, client_id, key, timeout=None) -> None:
        """Initialize self.  See help(type(self)) for accurate signature."""
    def on_event (self, event):
        ...
