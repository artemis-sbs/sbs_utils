
import typing


class ConsoleDispatcher:
    _dispatch_select = {}
    _dispatch_messages = {}
    # tick dispatch
    convert_to_console_id = None
    
    def add_select(an_id: int, console: str, cb: typing.Callable):
        """ add a target for console selection
        
        :param an_id: A ships ID player or non-player
        :type an_id: int
        :param console: The consoles unique ID
        :type console: string
        :param cb: call back function
        :type cb:  should have arguments of other sim and object's id
        """
        ConsoleDispatcher._dispatch_select[(an_id, console)] = cb

    def add_select_pair(an_id: int, another_id: int, console: str, cb: typing.Callable):
        """ add a target for console selection
        
        :param an_id: A ships ID player or non-player
        :type an_id: int
        :param console: The consoles unique ID
        :type console: string
        :param cb: call back function
        :type cb:  should have arguments of other sim and object's id
        """
        ConsoleDispatcher._dispatch_select[(an_id, another_id, console)] = cb

    def add_message(an_id: int, console: str, cb: typing.Callable):
        """ add a target for console message
        
        :param an_id: A ships ID player or non-player
        :type an_id: int
        :param console: The consoles unique ID
        :type console: string
        :param cb: call back function
        :type cb:  should have arguments of other sim, message and object's id
        """
        ConsoleDispatcher._dispatch_messages[(an_id, console)] = cb

    def add_message_pair(an_id: int, another, console: str, cb: typing.Callable):
        """ add a target for console message
        
        :param an_id: A ships ID player or non-player
        :type an_id: int
        :param console: The consoles unique ID
        :type console: string
        :param cb: call back function
        :type cb:  should have arguments of other sim, message and object's id
        """
        ConsoleDispatcher._dispatch_messages[(an_id, another, console)] = cb


    def remove_select(an_id: int, console: str):
        """ remove a target for console selection
        
        :param an_id: A ships ID player or non-player
        :type an_id: int
        :param console: The consoles unique ID
        :type console: string
        """
        ConsoleDispatcher._dispatch_select.pop((an_id, console))

    def remove_select_pair(an_id: int, another_id:int, console: str):
        """ remove a target for console selection
        
        :param an_id: A ships ID player or non-player
        :type an_id: int
        :param console: The consoles unique ID
        :type console: string
        """
        ConsoleDispatcher._dispatch_select.pop((an_id, another_id, console))

    def remove_message(an_id: int, console: str):
        """ remove a target for console messages
        
        :param an_id: A ships ID player or non-player
        :type an_id: int
        :param console: The consoles unique ID
        :type console: string
        """
        ConsoleDispatcher._dispatch_messages.pop((an_id, console))

    def remove_message_pair(an_id: int, another_id:int, console: str):
        """ remove a target for console messages
        
        :param an_id: A ships ID player or non-player
        :type an_id: int
        :param console: The consoles unique ID
        :type console: string
        """
        ConsoleDispatcher._dispatch_messages.pop((an_id, another_id, console))

    def dispatch_select(sim, event):
        """ dispatches a console selection
        
        :param sim: The simulation
        :type sim: Artemis Simulation
        :param player_id: A player ship ID
        :type player_id: int
        :param console: The consoles unique ID
        :type console: string
        :param other_id: A non player ship ID player
        :type other_id: int
        """
        console = ConsoleDispatcher.convert_to_console_id(sim,event)
        ConsoleDispatcher.do_select(sim, event, console)
        print(f"con select{console}")


        cb = ConsoleDispatcher._dispatch_select.get((event.origin_id, console))
        if cb is not None:
            cb(sim, event.selected_id, event)
            
        # Allow to route to the selected ship too
        cb = ConsoleDispatcher._dispatch_select.get((event.selected_id, console))
        if cb is not None:
            cb(sim, event.origin_id, event)

        cb = ConsoleDispatcher._dispatch_select.get((event.origin_id, event.selected_id, console))
        if cb is not None:
            cb(sim, event.selected_id, event)
            
        # Allow to route to the selected ship too
        cb = ConsoleDispatcher._dispatch_select.get((event.selected_id, event.origin_id, console))
        if cb is not None:
            cb(sim, event.origin_id, event)

    def dispatch_message(sim, event, console):
        """ dispatches a console message
        
        :param sim: The simulation
        :type sim: Artemis Simulation
        :param message_tag: The message
        :type message_tag: string
        :param player_id: A player ship ID
        :type player_id: int
        :param console: The consoles unique ID
        :type console: string
        :param other_id: A non player ship ID player
        :type other_id: int
        """

        cb = ConsoleDispatcher._dispatch_messages.get((event.origin_id, console))
        if cb is not None:
            cb(sim, event.sub_tag, event.selected_id, event)

        cb = ConsoleDispatcher._dispatch_messages.get((event.selected_id, console))
        # Allow the target to process
        if cb is not None:
            cb(sim, event.sub_tag, event.origin_id, event)

        cb = ConsoleDispatcher._dispatch_messages.get((event.origin_id, event.selected_id, console))
        if cb is not None:
            cb(sim, event.sub_tag, event.selected_id, event)

        cb = ConsoleDispatcher._dispatch_messages.get((event.selected_id, event.origin_id, console))
        # Allow the target to process
        if cb is not None:
            cb(sim, event.sub_tag, event.origin_id, event)

    def convert(sim, event):
        if "weap" in event.sub_tag:
            return "weapon_target_UID"
        if "sci" in event.sub_tag:
            return "science_target_UID"
        if "comm" in event.sub_tag:
            return "comms_target_UID"


    def do_select(sim, event, console):
        my_ship  = sim.get_space_object(event.origin_id)
        blob = my_ship.data_set
        blob.set(console, event.selected_id,0)

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

    def comms_selected(self, sim, an_id, event):
        """ handle a comms selection
        
        :param sim: The simulation
        :type sim: Artemis Simulation
        :param an_id: The other ship involved
        :type an_id: int
        """
        pass

    def comms_message(self, sim, message, an_id, event):
        """ handle a comms message
        
        :param sim: The simulation
        :type sim: Artemis Simulation
        :param message_tag: The message
        :type message_tag: string
        :param an_id: The other ship involved
        :type an_id: int
        """
        pass
