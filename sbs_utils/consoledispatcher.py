
import typing


class ConsoleDispatcher:
    _dispatch_select = {}
    _dispatch_messages = {}
    # tick dispatch

    
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

    def add_message(player_id: int, console: str, cb: typing.Callable):
        """ add a target for console message
        
        :param an_id: A ships ID player or non-player
        :type an_id: int
        :param console: The consoles unique ID
        :type console: string
        :param cb: call back function
        :type cb:  should have arguments of other sim, message and object's id
        """
        ConsoleDispatcher._dispatch_messages[(player_id, console)] = cb

    def remove_select(player_id: int, console: str):
        """ remove a target for console selection
        
        :param an_id: A ships ID player or non-player
        :type an_id: int
        :param console: The consoles unique ID
        :type console: string
        """
        ConsoleDispatcher._dispatch_select.pop((player_id, console))

    def remove_message(player_id: int, console: str):
        """ remove a target for console messages
        
        :param an_id: A ships ID player or non-player
        :type an_id: int
        :param console: The consoles unique ID
        :type console: string
        """
        ConsoleDispatcher._dispatch_messages.pop((player_id, console))

    def dispatch_select(sim, player_id: int, console: str, other_id):
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

        cb = ConsoleDispatcher._dispatch_select.get((player_id, console))
        if cb is not None:
            cb(sim, other_id)
            return
        # Allow to route to the selected ship too
        cb = ConsoleDispatcher._dispatch_select.get((other_id, console))
        if cb is not None:
            cb(sim, player_id)

    def dispatch_message(sim, message_tag: str, player_id: int, console: str, other_id):
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
        cb = ConsoleDispatcher._dispatch_messages.get((player_id, console))
        if cb is not None:
            cb(sim, message_tag, other_id)

        cb = ConsoleDispatcher._dispatch_messages.get((other_id, console))
        # Allow the target to process
        if cb is not None:
            cb(sim, message_tag, player_id)

    def dispatch_comms_message(sim, message_tag: str, player_id: int,  other_id):
        """ dispatches a comms console message
        
        :param sim: The simulation
        :type sim: Artemis Simulation
        :param message_tag: The message
        :type message_tag: string
        :param player_id: A player ship ID
        :type player_id: int
        :param other_id: A non player ship ID player
        :type other_id: int
        """
        return ConsoleDispatcher.dispatch_message(sim, message_tag, player_id, 'comms_targetUID', other_id)


class MCommunications:
    def enable_comms(self, face_desc=None):
        """ includes in ConsoleDispatch system
        
        :param face_desc: Face Description
        :type face_desc: string
        """
        self.face_desc = face_desc if face_desc is not None \
            else f"ter #964b00 8 1;ter #968b00 3 0;ter #968b00 4 0;ter #968b00 5 2;ter #fff 3 5;ter #964b00 8 4;"

        ConsoleDispatcher.add_select(self.id, 'comms_targetUID', self.comms_selected)
        ConsoleDispatcher.add_message(self.id, 'comms_targetUID', self.comms_message)

    def comms_selected(self, sim, an_id):
        """ handle a comms selection
        
        :param sim: The simulation
        :type sim: Artemis Simulation
        :param an_id: The other ship involved
        :type an_id: int
        """
        pass

    def comms_message(self, sim, message, an_id):
        """ handle a comms message
        
        :param sim: The simulation
        :type sim: Artemis Simulation
        :param message_tag: The message
        :type message_tag: string
        :param an_id: The other ship involved
        :type an_id: int
        """
        pass
