
import typing


class ConsoleDispatcher:
    _dispatch_select = {}
    _dispatch_messages = {}
    # tick dispatch

    def add_select(player_id: int, console: str, cb: typing.Callable):
        # Callback should have arguments of other object's id, message
        ConsoleDispatcher._dispatch_select[(player_id, console)] = cb

    def add_message(player_id: int, console: str, cb: typing.Callable):
        ConsoleDispatcher._dispatch_messages[(player_id, console)] = cb

    def remove_select(player_id: int, console: str):
        # Callback should have arguments of other object's id, message
        ConsoleDispatcher._dispatch_select.pop((player_id, console))

    def remove_message(player_id: int, console: str):
        # Callback should have arguments of other object's id, message
        ConsoleDispatcher._dispatch_messages.pop((player_id, console))

    def dispatch_select(sim, player_id: int, console: str, other_id):
        cb = ConsoleDispatcher._dispatch_select.get((player_id, console))
        if cb is not None:
            cb(sim, other_id)
            return
        # Allow to route to the selected ship too
        cb = ConsoleDispatcher._dispatch_select.get((other_id, console))
        if cb is not None:
            cb(sim, player_id)

    def dispatch_message(sim, message_tag: str, player_id: int, console: str, other_id):
        cb = ConsoleDispatcher._dispatch_messages.get((player_id, console))
        if cb is not None:
            cb(sim, message_tag, other_id)

        cb = ConsoleDispatcher._dispatch_messages.get((other_id, console))
        # Allow the target to process
        if cb is not None:
            cb(sim, message_tag, player_id)

    def dispatch_comms_message(sim, message_tag: str, player_id: int,  other_id):
        return ConsoleDispatcher.dispatch_message(sim, message_tag, player_id, 'comms_targetUID', other_id)


class MCommunications:
    def enable_comms(self, face_desc=None):
        self.face_desc = face_desc if face_desc is not None \
            else f"ter #964b00 8 1;ter #968b00 3 0;ter #968b00 4 0;ter #968b00 5 2;ter #fff 3 5;ter #964b00 8 4;"

        ConsoleDispatcher.add_select(self.id, 'comms_targetUID', self.comms_selected)
        ConsoleDispatcher.add_message(self.id, 'comms_targetUID', self.comms_message)

    def comms_selected(self, sim, player_id):
        pass

    def comms_message(self, sim, message, player_id):
        pass
