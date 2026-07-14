from .helpers import FrameContext
from .agent import Agent, get_task_id

class TickTask(Agent):
    """
    A task that is managed by the TickDispatcher
    """

    def __init__(self, cb, delay, count):
        """ new TickTask
        
        :param sim: The Artemis Cosmos simulation
        :param cb: call back function
        :param delay: the time in seconds for the task to delay
        :type delay: int
        :param count: The number of times to run None mean infinite
        :type count: int or None
        """
        super().__init__()
        self.cb = cb
        self.delay = delay
        self.id = get_task_id()
        self.add()

        # capture the start time
        
        self.start = FrameContext.context.sim.time_tick_counter
        
        self.count = count
        

    def stop(self):
        """ Stop a tasks
        The task is removed
        """
        TickDispatcher.completed.add(self)

    def _update(self):
        if (FrameContext.context.sim.time_tick_counter - self.start)/TickDispatcher.tps >= self.delay:
            # one could not supply a callback
            if self.cb is not None:
                # call the function
                self.cb(self)
            else:
                # this does nothing so remove it
                self.stop()

            if self.count is not None:
                self.count = self.count - 1
            if self.count is None or self.count > 0:
                # reschedule
                self.start = FrameContext.context.sim.time_tick_counter
                return False
            else:
                return True
        return False

    @property
    def done(self)->bool:
        """ returns if this is the task will not run in the future
        """
        return self.count <= 0


class RollingSlicer:
    """Spread per-tick work over a set of ids across ticks (anti-spike).

    A large per-tick batch (e.g. running every brain or objective in one frame)
    causes a periodic hitch. A RollingSlicer instead hands back a small slice
    each tick, sized by a fractional accumulator so a full pass over every id
    completes in exactly ``pass_seconds`` of sim time -- regardless of set size
    or tick rate (no over-run on small sets, no spike on large ones). The set's
    sorted order is cached and only rebuilt when membership changes, so the
    cursor advances predictably as ids are added/removed.

    Usage:
        _slicer = RollingSlicer()
        for id in _slicer.slice(id_set, pass_seconds=3):
            ...work one item...
    """
    def __init__(self):
        self.cursor = 0
        self.accum = 0.0
        self._sorted = []
        self._sig = None

    def slice(self, ids, pass_seconds):
        sig = frozenset(ids)
        if sig != self._sig:
            self._sorted = sorted(ids)
            self._sig = sig
        items = self._sorted
        n = len(items)
        if n == 0:
            return ()
        # run n / (pass_seconds * tps) items per call on average; carry the
        # fraction so the full-pass period is exact for any n / tick rate.
        self.accum += n / (pass_seconds * TickDispatcher.tps)
        budget = min(n, int(self.accum))
        if budget <= 0:
            return ()
        self.accum -= budget
        start = self.cursor % n
        seq = [items[(start + k) % n] for k in range(budget)]
        self.cursor = (start + budget) % n
        return seq


class TickDispatcher:
    """
    The Tick Dispatcher is used to manager timed items via the HandleSimulationTick
    """
    _dispatch_tick = set()
    _new_this_tick = set()
    completed = set()
    current = 0
    # ticks per second
    tps = 30

    @classmethod
    def clear(cls):
        """Drop all scheduled ticks (fresh mission / in-process recompile)."""
        cls._dispatch_tick = set()
        cls._new_this_tick = set()
        cls.completed = set()

    def do_once(cb: callable, delay: int):
        """ Create and return a task that executes once

        :param delay: the time in seconds for the task to delay
        :type delay: int
        :return: The task is returned and can be used to attach data for future use.
        :rtype: TickTask

        example:
            def some_use():
                t = TickDispatcher.do_once(the_callback, 5)
                t.data = some_data

            def the_callback(t):
                print(t.some_data)
        """
        t = TickTask(cb, delay, 1)
        TickDispatcher._new_this_tick.add(t)
        return t

    def do_interval(cb: callable, delay: int, count: int = None):
        """ Create and return a task that executes more than once

        :param ctx: The Artemis Cosmos simulation
        :param cb: call back function
        :param delay: the time in seconds for the task to delay
        :type delay: int
        :param count: The number of times to run None mean infinite
        :type count: int or None
        :return: The task is returned and can be used to attach data for future use.
        :rtype: TickFTask

        example:
        
        .. code-block:: python

            def some_use():
                t = TickDispatcher.do_interval(the_callback, 5)
                t.data = some_data

            def the_callback(t):
                print(t.some_data)
                if t.some_data.some_condition:
                    t.stop()
        """
        t = TickTask(cb, delay, count)
        TickDispatcher._new_this_tick.add(t)
        return t

    def dispatch_tick():
        """ Process all the tasks
        The task is updated to see if it should be triggered, 
        and if it is completed
        """
        TickDispatcher.current = FrameContext.context.sim.time_tick_counter
        # Remove tasks are completed
        # script could have stopped it
        for c in TickDispatcher.completed:
            TickDispatcher._dispatch_tick.discard(c)

        TickDispatcher.completed = set()
        # Before running add items that are new
        # these would have been added last time
        # this was run
        for a in TickDispatcher._new_this_tick:
            TickDispatcher._dispatch_tick.add(a)

        TickDispatcher._new_this_tick = set()
        # process all the tasks
        for t in TickDispatcher._dispatch_tick:
            if t._update():
                TickDispatcher.completed.add(t)


        # Remove tasks are completed
        for c in TickDispatcher.completed:
            TickDispatcher._dispatch_tick.discard(c)
