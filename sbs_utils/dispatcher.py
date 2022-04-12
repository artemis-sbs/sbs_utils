class Dispatcher:
    # set should be faster with removes
    all = set()
    # ticks per second
    tps = 30

    def __init__(self, sim, cb, delay, count):
        self.cb = cb
        self.delay = delay
        # capture the start time
        self.start = sim.time_tick_counter
        self.count = count

    def _update(self, sim):
        if (sim.time_tick_counter - self.start)/Dispatcher.tps >= self.delay:
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
        Dispatcher.completed.add(self)

    @property
    def done(self):
        return self.count <= 0


    def tick(sim):
        # Adding it as static allow stop to be called cleanly
        Dispatcher.completed = set()
        for t in Dispatcher.all:
            if t._update(sim):
                Dispatcher.completed.add(t)
        for c in Dispatcher.completed:
            Dispatcher.all.remove(c)


    def schedule_once(sim, cb, delay):
        t = Dispatcher(sim, cb, delay, 1)
        Dispatcher.all.add(t)
        return t

    def schedule_interval(sim, cb, delay, count=None):
        t = Dispatcher(sim, cb, delay, count)
        Dispatcher.all.add(t)
        return t


def schedule_once(sim, cb, delay):
    return Dispatcher.schedule_once(sim,cb,delay)

def schedule_interval(sim, cb, delay, count=None):
    return Dispatcher.schedule_interval(sim, cb, delay, count)

def tick(sim):
    return Dispatcher.tick(sim)
