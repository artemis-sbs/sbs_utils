
import typing
# using Agent since it is lighter weight than query??
from .agent import Agent
from .helpers import FrameContext
from .procedural.inventory import get_inventory_value


class ConsoleDispatcher:
    _dispatch_select = {}
    _dispatch_messages = {}
    # tick dispatch
    convert_to_console_id = None
    
    def add_default_select(console: str, cb: typing.Callable):
        """ add a target for console selection
        :param console: The consoles unique ID
        :type console: string
        :param cb: call back function
        :type cb:  should have arguments of other ctx and object's id
        """
        ConsoleDispatcher.add_select(0, console, cb)

    def add_always_select(console: str, cb: typing.Callable):
        """ add a target for console selection
        :param console: The consoles unique ID
        :type console: string
        :param cb: call back function
        :type cb:  should have arguments of other ctx and object's id
        """
        ConsoleDispatcher.add_select(None, console, cb)

    def add_select(an_id: int, console: str, cb: typing.Callable):
        """ add a target for console selection
        
        :param an_id: A ships ID player or non-player
        :type an_id: int
        :param console: The consoles unique ID
        :type console: string
        :param cb: call back function
        :type cb:  should have arguments of other ctx and object's id
        """
        key = (an_id, console)
        collection = ConsoleDispatcher._dispatch_select.get(key, list())
        # Using a list in a set like fashion, but so there is a known order
        if cb in collection:
            # Make sure it is in only once
            # but allow it to move to the front 
            collection.remove(cb)
        collection.insert(0,cb)
        ConsoleDispatcher._dispatch_select[key] = collection

    def add_select_pair(an_id: int, another_id: int, console: str, cb: typing.Callable):
        """ add a target for console selection
        
        :param an_id: A ships ID player or non-player
        :type an_id: int
        :param console: The consoles unique ID
        :type console: string
        :param cb: call back function
        :type cb:  should have arguments of other ctx and object's id
        """
        ConsoleDispatcher._dispatch_select[(an_id, another_id, console)] = cb

    def add_default_message(console: str, cb: typing.Callable):
        """ add a target for console message
        
        :param console: The consoles unique ID
        :type console: string
        :param cb: call back function
        :type cb:  should have arguments of other ctx, message and object's id
        """
        ConsoleDispatcher.add_message(0, console, cb)

    def add_message(an_id: int, console: str, cb: typing.Callable):
        """ add a target for console message
        
        :param an_id: A ships ID player or non-player
        :type an_id: int
        :param console: The consoles unique ID
        :type console: string
        :param cb: call back function
        :type cb:  should have arguments of other ctx, message and object's id
        """
        key = (an_id, console)
        collection = ConsoleDispatcher._dispatch_messages.get(key, list())
        if cb in collection:
            # Make sure it is in only once
            # but allow it to move to the front 
            collection.remove(cb)
        collection.insert(0,cb)
        ConsoleDispatcher._dispatch_messages[key] = collection
        

    def add_message_pair(an_id: int, another, console: str, cb: typing.Callable):
        """ add a target for console message
        
        :param an_id: A ships ID player or non-player
        :type an_id: int
        :param console: The consoles unique ID
        :type console: string
        :param cb: call back function
        :type cb:  should have arguments of other ctx, message and object's id
        """
        ConsoleDispatcher._dispatch_messages[(an_id, another, console)] = cb


    def remove_select(an_id: int, console: str, cb=None):
        """ remove a target for console selection
        
        :param an_id: A ships ID player or non-player
        :type an_id: int
        :param console: The consoles unique ID
        :type console: string
        """
        key = (an_id, console)
        if not key in ConsoleDispatcher._dispatch_select:
            return
        if cb is None:
            ConsoleDispatcher._dispatch_select.pop((an_id, console))
        else:
            collection = ConsoleDispatcher._dispatch_select.get(key, set())
            collection.discard(cb)
            if len(collection) == 0:
                ConsoleDispatcher._dispatch_select.pop((an_id, console))
            else:
                ConsoleDispatcher._dispatch_select[key] = collection

    def remove_select_pair(an_id: int, another_id:int, console: str):
        """ remove a target for console selection
        
        :param an_id: A ships ID player or non-player
        :type an_id: int
        :param console: The consoles unique ID
        :type console: string
        """
        ConsoleDispatcher._dispatch_select.pop((an_id, another_id, console))

    def remove_message(an_id: int, console: str, cb=None):
        """ remove a target for console messages
        
        :param an_id: A ships ID player or non-player
        :type an_id: int
        :param console: The consoles unique ID
        :type console: string
        """
        key = (an_id, console)
        if not key in ConsoleDispatcher._dispatch_messages:
            return
        if cb is None:
            ConsoleDispatcher._dispatch_messages.pop((an_id, console))
        else:
            collection = ConsoleDispatcher._dispatch_messages.get(key, set())
            collection.discard(cb)
            if len(collection) == 0:
                ConsoleDispatcher._dispatch_messages.pop((an_id, console))
            else:
                ConsoleDispatcher._dispatch_messages[key] = collection

    def remove_message_pair(an_id: int, another_id:int, console: str):
        """ remove a target for console messages
        
        :param an_id: A ships ID player or non-player
        :type an_id: int
        :param console: The consoles unique ID
        :type console: string
        """
        ConsoleDispatcher._dispatch_messages.pop((an_id, another_id, console))

    def dispatch_select(event):
        """ dispatches a console selection
        
        :param player_id: A player ship ID
        :type player_id: int
        :param console: The consoles unique ID
        :type console: string
        :param other_id: A non player ship ID player
        :type other_id: int
        """
        console = ConsoleDispatcher.convert_to_console_id(event)
        if console is None:
            return False
        ConsoleDispatcher.do_select(event, console)

        #
        # Allow to route to always
        #
        cb_set = ConsoleDispatcher._dispatch_select.get((None, console))
        if cb_set is not None:
            for cb in cb_set:
                cb(event)

        #handled = False
        cb = ConsoleDispatcher._dispatch_select.get((event.origin_id, event.selected_id, console))
        if cb is not None:
            cb(event)
            return True
            
        # Allow to route to the selected ship too
        cb = ConsoleDispatcher._dispatch_select.get((event.selected_id, event.origin_id, console))
        if cb is not None:
            cb(event)
            return True

        cb_set = ConsoleDispatcher._dispatch_select.get((event.origin_id, console))
        if cb_set is not None:
            for cb in cb_set:
                cb(event)
            return True
            
        # Allow to route to the selected ship too
        cb_set = ConsoleDispatcher._dispatch_select.get((event.selected_id, console))
        if cb_set is not None:
            for cb in cb_set:
                cb(event)
            return True
        
        # Allow to route to defaults too
        cb_set = ConsoleDispatcher._dispatch_select.get((0, console))
        if cb_set is not None:
            for cb in cb_set:
                cb(event)
            return True

        return False


    def dispatch_message(event, console):
        """ dispatches a console message
        
        :param message_tag: The message
        :type message_tag: string
        :param player_id: A player ship ID
        :type player_id: int
        :param console: The consoles unique ID
        :type console: string
        :param other_id: A non player ship ID player
        :type other_id: int
        """
        cb = ConsoleDispatcher._dispatch_messages.get((event.origin_id, event.selected_id, console))
        if cb is not None:
            cb(event)
            return

        cb = ConsoleDispatcher._dispatch_messages.get((event.selected_id, event.origin_id, console))
        # Allow the target to process
        if cb is not None:
            cb(event)
            return

        cb_set = ConsoleDispatcher._dispatch_messages.get((event.origin_id, console))
        if cb_set is not None:
            for cb in cb_set:
                cb(event)
            return True
            
        # Allow to route to the selected ship too
        cb_set = ConsoleDispatcher._dispatch_messages.get((event.selected_id, console))
        if cb_set is not None:
            for cb in cb_set:
                cb(event)
            return True
        
        # Allow to route to the default too
        cb_set = ConsoleDispatcher._dispatch_messages.get((0, console))
        if cb_set is not None:
            for cb in cb_set:
                cb(event)
            return True

        
    def convert(event):
        if "science_sorted_list" in event.value_tag or event.sub_tag == "science_target_UID":
            return "science_target_UID"
        if "comms_sorted_list" == event.value_tag or event.sub_tag == "comms_target_UID":
            return "comms_target_UID"
        if "grid_object_list" == event.value_tag or event.sub_tag == "grid_selected_UID":
            return "grid_selected_UID"
        
        # Catch the 2dview
        if "weap" in event.sub_tag or event.sub_tag == "weapon_target_UID":
            return "weapon_target_UID"
        if "sci" in event.sub_tag or event.sub_tag == "science_target_UID":
            return "science_target_UID"
        
        return None


    def do_select(event, console):
        #
        # This was from a follow route, don't select
        #
        if event.extra_tag=="__init__":
            return
        my_ship = FrameContext.context.sim.get_space_object(event.origin_id)

        blob = my_ship.data_set
        target = event.selected_id

        disabled_count = get_inventory_value(event.origin_id, console, 0)
        # if the console selection is disable don't allow selection
        if disabled_count > 0: 
            target = 0

        blob.set(console, target,0)

            
        co = Agent.get(event.client_id)
        # Set the selection as inventory
        if co:
            co.set_inventory_value(console.upper(), event.selected_id)
        if "grid" in console:
            blob.set("grid_selected_ship_UID", event.parent_id,0)
            if co:
                co.set_inventory_value("grid_selected_ship_UID".upper(), event.parent_id)

        

############
### Set the initial 
ConsoleDispatcher.convert_to_console_id = ConsoleDispatcher.convert

class MCommunications:
    def enable_comms(self, face_desc=None):
        """ includes in ConsoleDispatch system
        
        :param face_desc: Face Description
        :type face_desc: string
        """
        self.face_desc = face_desc if face_desc is not None \
            else f"ter #964b00 8 1;ter #968b00 3 0;ter #968b00 4 0;ter #968b00 5 2;ter #fff 3 5;ter #964b00 8 4;"

        ConsoleDispatcher.add_select(self.id, 'comms_target_UID', self.comms_selected)
        ConsoleDispatcher.add_message(self.id, 'comms_target_UID', self.comms_message)

    def comms_selected(self, an_id, event):
        """ handle a comms selection
        :param an_id: The other ship involved
        :type an_id: int
        """
        pass

    def comms_message(self, message, an_id, event):
        """ handle a comms message
        
        :param message_tag: The message
        :type message_tag: string
        :param an_id: The other ship involved
        :type an_id: int
        """
        pass


