
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
		else:
			print("Got here but failed")

	def dispatch_message(sim, message_tag: str, player_id: int, console: str, other_id):
		cb = ConsoleDispatcher._dispatch_messages.get((player_id, console))
		if cb is not None:
			cb(sim, message_tag, other_id)

	def dispatch_comms_message(sim, message_tag: str, player_id: int,  other_id):
		return ConsoleDispatcher.dispatch_message(sim, message_tag, player_id, 'comms_targetUID', other_id)
