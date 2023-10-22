from . import query 
from .inventory import get_inventory_value
from .roles import has_role
from .. import faces
from ..engineobject import EngineObject
from ..helpers import FrameContext
import sbs

def comms_broadcast(ids_or_obj, msg, color="#fff"):
    
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

def comms_message(msg, from_ids_or_obj, to_ids_or_obj, title=None, face=None, color="#fff"):
    if to_ids_or_obj is None:
        # internal message
        to_ids_or_obj = from_ids_or_obj
    
    from_objs = query.to_object_list(from_ids_or_obj)
    to_objs = query.to_object_list(to_ids_or_obj)
    for from_obj in from_objs:
        for to_obj in to_objs:
            # From face should be used
            if not title:
                title = from_obj.comms_id +" > "+to_obj.comms_id
                face = faces.get_face(from_obj.get_id())

            if face is None:
                face = ""
            # Only player ships send messages
            if has_role(from_obj.id, "__PLAYER__"):
                sbs.send_comms_message_to_player_ship(
                    from_obj.id,
                    to_obj.id,
                    color,
                    face, 
                    title, 
                    msg)
            else:
                sbs.send_comms_message_to_player_ship(
                    to_obj.id,
                    from_obj.id,
                    color,
                    face, 
                    title, 
                    msg)

def _comms_get_origin_id():
    #
    # Event 
    #
    if FrameContext.context.event is not None:
        if FrameContext.context.event.tag == "press_comms_button":
            return FrameContext.context.event.origin_id
    #
    # 
    #
    if FrameContext.task is not None:
        return FrameContext.task.get_variable("COMMS_ORIGIN_ID")

def _comms_get_selected_id():
    #
    # Event 
    #
    if FrameContext.context.event is not None:
        if FrameContext.context.event.tag == "press_comms_button":
            return FrameContext.context.event.selected_id
    
    if FrameContext.task is not None:
        return FrameContext.task.get_variable("COMMS_SELECTED_ID")



def comms_transmit(msg, title=None, face=None, color="#fff"):
    from_ids_or_obj = _comms_get_origin_id()
    to_ids_or_obj = _comms_get_selected_id()
    if to_ids_or_obj is None or from_ids_or_obj is None:
        #
        # Communicate an error
        #
        pass 
    # player transmits a message
    comms_message(msg, from_ids_or_obj, to_ids_or_obj,  title, face, color)

def comms_receive(msg, title=None, face=None, color="#fff"):
    to_ids_or_obj = _comms_get_origin_id()
    from_ids_or_obj = _comms_get_selected_id()
    if to_ids_or_obj is None or from_ids_or_obj is None:
        #
        # Communicate an error
        #
        pass 
    # player receives a message
    comms_message(msg, from_ids_or_obj, to_ids_or_obj,  title, face, color)


def comms_transmit_internal(msg, ids_or_obj=None, to_name=None,  title=None, face=None, color="#fff"):
    ids_or_obj = _comms_get_origin_id()
    # player transmits a message to a named internal
    for ship in query.to_object_list(ids_or_obj):
        if to_name is None:
            to_name = ship.name
        if title is None:
            title = f"{ship.name} > {to_name}"
        if face is None and to_name is not None:
            # try to find a face
            face = get_inventory_value(ship.id, f"face_{to_name}", None)
        comms_message(msg, ship, ship,  title, face, color)


def comms_receive_internal(msg, ids_or_obj=None, from_name=None,  title=None, face=None, color="#fff"):
    if ids_or_obj is None:
        ids_or_obj = _comms_get_origin_id()
    # player transmits a message to a named internal
    for ship in query.to_object_list(ids_or_obj):
        if from_name is None:
            from_name = ship.name
        if title is None:
            title = f"{from_name} > {ship.name}"
        if face is None and from_name is not None:
            # try to find a face
            face = get_inventory_value(ship.id, f"face_{from_name}", None)
        comms_message(msg, ship, ship,  title, face, color)
        
        
        
