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
                # call the function
                self.cb(sim, self)
            else:
                # this does nothing so remove it
                self.stop()

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
        """ Stop a tasks
        The task is removed
        """
        TickDispatcher.completed.add(self)

    @property
    def done(self):
        """ returns if this is the task will not run in the future
        """
        return self.count <= 0


    def do_once(sim:any, cb:callable, delay:int):
        """ Create and return a task that executes once

        Keyword Arguments:
        sim - The Artemis Cosmos simulation
        cb - the function to call when the delay is reached
        delay - the number of seconds
        """
        t = TickDispatcher(sim, cb, delay, 1)
        TickDispatcher._new_this_tick.add(t)
        return t

    def do_interval(sim:any, cb:callable, delay:int, count:int=None):
        """ Create and return a task that executes more than once

        Keyword Arguments:
        sim - The Artemis Cosmos simulation
        cb - the function to call when the delay is reached
        delay - the number of seconds
        count - the number of times to execute if None it executes continuously
        """
        t = TickDispatcher(sim, cb, delay, count)
        TickDispatcher._new_this_tick.add(t)
        return t

    def dispatch_tick(sim):
        """ Process all the tasks
        The task is updated to see if it should be triggered, 
        and if it is completed
        """

        TickDispatcher.completed = set()
        # Before running add items that are new
        # these would have been added last time 
        # this was run
        for a in TickDispatcher._new_this_tick:
            TickDispatcher._dispatch_tick.add(a)

        TickDispatcher._new_this_tick = set()
        # process all the tasks
        for t in TickDispatcher._dispatch_tick:
            if t._update(sim):
                TickDispatcher.completed.add(t)
                
        # Remove tasks are completed
        for c in TickDispatcher.completed:
            TickDispatcher._dispatch_tick.remove(c)
