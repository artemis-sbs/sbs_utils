import sbs


class SpaceObject:
	ids = {}
	debug = True

	def add(id, obj):
		SpaceObject.ids[id] = obj

	def remove(id):
		return SpaceObject.ids[id]

	def get(id):
		o = SpaceObject.ids.get(id)
		if o is None:
			return None
		return o

	def get_as(id, cls):
		o = SpaceObject.ids.get(id)
		if o is None:
			return None
		if o.__class__ != cls:
			return None
		return o

	def py_class():
		return __class__

	def add_id(self):
		SpaceObject.add(self.id, self)

	def make_new_player(self, sim, behave, data_id):
		self.id = sim.make_new_player(behave, data_id)
		self.add_id()
		sbs.assign_player_ship(self.id)
		return sim.get_space_object(self.id)

	def make_new_active(self, sim,  behave, data_id):
		self.id = sim.make_new_active(behave, data_id)
		self.add_id()
		return self.get_space_object(sim)

	def get_space_object(self, sim):
		return sim.get_space_object(self.id)

	def make_new_passive(self, sim, behave, data_id):
		self.id = sim.make_new_passive(behave, data_id)
		self.add_id()
		return sim.get_space_object(self.id)

	def debug_mark_loc(sim,  x: float, y: float, z: float, name: str, color: str):
		if SpaceObject.debug:
			return sim.add_navpoint(x, y, z, name, color)
		return None

	def debug_remove_mark_loc(sim, name: str):
		if SpaceObject.debug:
			return sim.delete_navpoint_by_name(name)
		return None

	def log(s: str):
		if SpaceObject.debug:
			print(s)
