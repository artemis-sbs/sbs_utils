from ...helpers import FrameContext
from ...futures import AwaitBlockPromise

from ...extra_dispatcher import ClientStringDispatcher
class ClientStringPromise(AwaitBlockPromise):
    def __init__(self, client_id, key, timeout=None) -> None:
        super().__init__(timeout)
        self.client_id = client_id
        self.key =key
        FrameContext.context.sbs.request_client_string(client_id, key)
        ClientStringDispatcher.add_any(self.on_event)


    def on_event(self, event):
        if self.client_id != event.client_id or self.key != event.sub_tag:
            return
        self.set_result(event.value_tag)
        ClientStringDispatcher.remove_any(self.on_event)

def gui_request_client_string(client_id, key, timeout=None):
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
        ~~ player_name = result.result ~~
    """
    return ClientStringPromise(client_id, key, timeout)




    

