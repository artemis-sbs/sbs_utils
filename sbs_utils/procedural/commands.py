from . import query 
from ..engineobject import EngineObject
from ..helpers import FrameContext
import sbs

def cmd_broadcast(ids_or_obj, msg, color="#fff"):
    
    if ids_or_obj is None:
        # default to the 
        ids_or_obj = FrameContext.context.event.parent_id

    _ids = query.to_id_list(ids_or_obj)
    if _ids:
        for id in _ids:
            if query.is_client_id(id):
                sbs.send_message_to_client(id, color, msg)
            else:
                # Just verify the id
                obj = EngineObject.get(id)
                if obj is not None or id==0:
                    sbs.send_message_to_player_ship(id, color, msg)

