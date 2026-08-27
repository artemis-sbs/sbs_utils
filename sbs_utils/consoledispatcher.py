
import typing
# using Agent since it is lighter weight than query??
from .agent import Agent
from .helpers import FrameContext
from .procedural.inventory import get_inventory_value, set_inventory_value


class ConsoleDispatcher:
    _dispatch_select = {}
    _dispatch_messages = {}

    @classmethod
    def clear(cls):
        """Drop all registered console routes (fresh mission / in-process recompile)."""
        cls._dispatch_select = {}
        cls._dispatch_messages = {}
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
            ConsoleDispatcher._dispatch_select.pop((an_id, console),None)
        else:
            collection = ConsoleDispatcher._dispatch_select.get(key, set())
            collection.discard(cb)
            if len(collection) == 0:
                ConsoleDispatcher._dispatch_select.pop((an_id, console), None)
            else:
                ConsoleDispatcher._dispatch_select[key] = collection

    def remove_select_pair(an_id: int, another_id:int, console: str):
        """ remove a target for console selection
        
        :param an_id: A ships ID player or non-player
        :type an_id: int
        :param console: The consoles unique ID
        :type console: string
        """
        ConsoleDispatcher._dispatch_select.pop((an_id, another_id, console), None)

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
            ConsoleDispatcher._dispatch_messages.pop((an_id, console), None)
        else:
            collection = ConsoleDispatcher._dispatch_messages.get(key, set())
            collection.discard(cb)
            if len(collection) == 0:
                ConsoleDispatcher._dispatch_messages.pop((an_id, console), None)
            else:
                ConsoleDispatcher._dispatch_messages[key] = collection

    def remove_message_pair(an_id: int, another_id:int, console: str):
        """ remove a target for console messages
        
        :param an_id: A ships ID player or non-player
        :type an_id: int
        :param console: The consoles unique ID
        :type console: string
        """
        ConsoleDispatcher._dispatch_messages.pop((an_id, another_id, console), None)

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
        
        cb_set = ConsoleDispatcher._dispatch_select.get((event.origin_id, console))
        if cb_set is not None:
            for cb in cb_set:
                cb(event)
            return True

        # TODO: These were for old python assumptions that are no longer valid.
        # Next time you read this assuming there are no bugs delete them
        #             
        # Allow to route to the selected ship too
        # cb = ConsoleDispatcher._dispatch_select.get((event.selected_id, event.origin_id, console))
        # if cb is not None:
        #     cb(event)
        #     return True
            
        # Allow to route to the selected ship too
        # cb_set = ConsoleDispatcher._dispatch_select.get((event.selected_id, console))
        # if cb_set is not None:
        #     for cb in cb_set:
        #         cb(event)
        #     return True
        
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
        #
        # sub_tag is the console
        # Value_tag has the widget
        # Extra_tag will now have the blob 
        # Extra_extra_tag may have data e.g. tab selection has some data
        #
        # science_data
        #
        # normal_target_UID
        #
        if "science_sorted_list" in event.value_tag or event.extra_tag == "science_target_UID":
            return "science_target_UID"
        if "comms_sorted_list" == event.value_tag or event.extra_tag == "comms_target_UID":
            return "comms_target_UID"
        if "grid_object_list" == event.value_tag or event.extra_tag == "grid_selected_UID":
            return "grid_selected_UID"
        
        if event.tag.startswith("hold"):
            return f"{event.sub_tag}_popup"
        
        # Catch the 2dview
        if "weap" in event.sub_tag or event.extra_tag == "weapon_target_UID":
            return "weapon_target_UID"
        if "sci" in event.sub_tag or event.extra_tag == "science_target_UID":
            return "science_target_UID"

        #
        # may not be needed after v0.3.29
        #   
        if "admiral" in event.sub_tag or event.extra_tag == "science_target_UID":
            return "science_target_UID"
        if "admiral" in event.sub_tag or event.value_tag == "science_2d_view":
            return "science_target_UID"
        if "admiral" in event.sub_tag and event.value_tag == "2dview":
            return "science_target_UID"
        
        #
        # This is for give orders
        #
        if "comm" in event.sub_tag and event.value_tag == "2dview":
            return "comms_2d_target_UID"
            

        # A basic 2d view
        if event.extra_tag == "normal_target_UID":
            return "normal_target_UID"
        
        return None


    def do_select(event, console):
        #
        # This was from a follow route, don't select
        #
        if event.extra_tag=="__init__":
            return
        
        ship_id = event.origin_id
        main_ship = FrameContext.context.sim.get_space_object(ship_id)

        #alt_ship = get_inventory_value(event.client_id, f"{event.value_tag}_alt_ship", 0)
        #if alt_ship is not None and alt_ship != 0:
        #    ship_id = alt_ship
        #    alt_ship = FrameContext.context.sim.get_space_object(ship_id)

        blob = None
        if main_ship is None:
            return
        
        blob = main_ship.data_set
        target = event.selected_id
        

        # A console that is a DISPLAY takes no part in selection.
        #
        # It has to RESTORE, not refuse, and that is measured rather than assumed: the
        # ENGINE writes the ship's selection into the blob itself, before the event ever
        # reaches the script. Instrumenting do_select in a real run showed the blob
        # already holding the new value on entry (`sel == before` on every click), so by
        # the time anything here can object, the selection has changed. Returning early
        # leaves the engine's write standing - which is exactly the bug this is for.
        #
        # Hence `approved_<console>`: the last selection the library actually allowed.
        # A disabled console's click puts that back. It is a separate check from the
        # ship-level one below because that one is per-SHIP - all-or-nothing for every
        # console looking at the ship - and when it fires it still WRITES `target = 0`,
        # clearing the selection everyone else can see.
        if get_inventory_value(event.client_id, f"disable_{console}", 0) > 0:
            approved = get_inventory_value(ship_id, f"approved_{console}", 0)
            # Never restore a dead handle - a grid object can be deleted while it is
            # selected (grid.py clears the blob when that happens) and resurrecting the
            # id here would hand every reader a stale selection.
            if approved and Agent.get(approved) is None:
                approved = 0
            blob.set(console, approved, 0)
            return

        disabled_count = get_inventory_value(ship_id, console, 0)
        # if the console selection is disable don't allow selection
        if disabled_count > 0:
            target = 0

        # Previous selection.
        #
        # NOT `blob.get(console)`: the engine has already written the NEW selection into
        # the blob before this event arrives, so reading it back here recorded the new
        # value as the "previous" one - `prev_selection` was equal to the current
        # selection on every click. `approved_<console>` is the last value the library
        # actually allowed, which is what "previous" meant. (Nothing in any repo reads
        # `prev_selection` - LegendaryMissions keeps its own `gamemaster_prev_selection`
        # - so this corrects a write-only value rather than changing behavior.)
        prev = get_inventory_value(ship_id, f"approved_{console}", 0)
        set_inventory_value(event.origin_id, f"prev_selection", prev)

        blob.set(console, target,0)
        # What a display-only console's click must be rolled back to.
        set_inventory_value(ship_id, f"approved_{console}", target)

            
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


