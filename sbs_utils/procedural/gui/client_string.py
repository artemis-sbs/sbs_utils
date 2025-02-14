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
    return ClientStringPromise(client_id, key, timeout )




    

