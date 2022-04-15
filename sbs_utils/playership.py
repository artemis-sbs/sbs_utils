
from .consoledispatcher import ConsoleDispatcher
from .spaceobject import SpaceObject


class PlayerShip(SpaceObject):
	def on_console_message(self, console, cb):
		ConsoleDispatcher.add_message(self.id, console, cb)

	def on_comms_message(self, cb):
		ConsoleDispatcher.add_message(self.id, 'comms_targetUID', cb)

	def on_console_select(self, console, cb):
		ConsoleDispatcher.add_select(self.id, console, cb)

	def on_comms_select(self, cb):
		ConsoleDispatcher.add_select(self.id, 'comms_targetUID', cb)