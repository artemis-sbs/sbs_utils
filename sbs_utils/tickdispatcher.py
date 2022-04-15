class TickDispatcher:
	_dispatch_tick = set()
	_new_this_tick = set()
	# ticks per second
	tps = 30
	
	def __init__(self, sim, cb, delay, count):
		self.cb = cb
		self.delay = delay
		# capture the start time
		self.start = sim.time_tick_counter
		self.count = count

	def _update(self, sim):
		if (sim.time_tick_counter - self.start)/TickDispatcher.tps >= self.delay:
			# one could not supply a callback
			if self.cb is not None:
				self.cb(sim, self)
			if self.count is not None:
				self.count = self.count -1
			if self.count is None or  self.count > 0:
				# reschedule
				self.start = sim.time_tick_counter
				return False
			else:
				return True
		return False

	def stop(self):
		TickDispatcher.completed.add(self)

	@property
	def done(self):
		return self.count <= 0

	def dispatch_tick(sim):
		# Adding it as static allow stop to be called cleanly
		TickDispatcher.completed = set()
		for a in TickDispatcher._new_this_tick:
			TickDispatcher._dispatch_tick.add(a)

		TickDispatcher._new_this_tick = set()
		for t in TickDispatcher._dispatch_tick:
			if t._update(sim):
				TickDispatcher.completed.add(t)
		for c in TickDispatcher.completed:
			TickDispatcher._dispatch_tick.remove(c)


	def do_once(sim:any, cb:callable, delay:int):
		t = TickDispatcher(sim, cb, delay, 1)
		TickDispatcher._new_this_tick.add(t)
		return t

	def do_interval(sim:any, cb:callable, delay:int, count:int=None):
		t = TickDispatcher(sim, cb, delay, count)
		TickDispatcher._new_this_tick.add(t)
		return t
