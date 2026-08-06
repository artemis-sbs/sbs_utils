import random

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


def _xyz(p):
    """Accept a Vec3, an (x, y, z) tuple, or None."""
    if p is None:
        return (0.0, 0.0, 0.0)
    x = getattr(p, "x", None)
    if x is not None:
        return (x, getattr(p, "y", 0.0), getattr(p, "z", 0.0))
    return (p[0], p[1], p[2])


class DripQueue:
    """Drain a FINITE work list over a few seconds instead of in one frame.

    ``RollingSlicer``'s sibling. That one paces *recurring* work over a live set
    (brains, objectives, urges); this paces *one-shot creation*, so a burst -- a
    map's whole terrain field, a fleet, a prefab scatter -- becomes a drip. The
    engine measurement behind this: LM's terrain block is ~280 ms of work in a
    single frame, a ~5x hitch, with no sync tail afterwards. The cost is all in the
    frame that creates the objects, so spreading that frame out is the whole fix.

    Two properties make a queued call equivalent to the inline one it replaced:

    * each item captures ``random.getstate()`` when queued and runs under that
      state, so it creates exactly what it would have created inline -- whenever
      it runs, in whatever order (the same trick ``terrain_spawn_field_keyed``
      already uses per cell);
    * items run NEAREST-FIRST from a focus point, so the space around the focus is
      correct first and the fill-in lands where nobody is looking.

    That equivalence is PER ITEM. Deferring still moves when the caller's own RNG
    stream is consumed, so a sequence of queued calls whose plans read that stream
    (terrain's cluster loops do) produces a deterministic but different result from
    running them inline. Queue whole units of work, not halves of one.

    Draining is deadline-driven: everything queued has run by ``over`` sim-seconds
    after it was queued, and items added mid-drain push the deadline out rather
    than crowding the remaining ticks.

    Usage:
        q = DripQueue(over=6, focus=Vec3(0, 0, 0), name="terrain")
        q.add(spawn_a_cluster, (points, height), pos=points[0])
        ...
        q.flush()          # or let it drain itself, a slice per tick
    """

    def __init__(self, over=6.0, focus=None, name="drip"):
        self.over = over
        self.focus = _xyz(focus)
        self.name = name
        self.items = []
        self.errors = 0
        self.accum = 0.0
        self.deadline = None
        self.task = None
        self._seq = 0
        self._unsorted = False

    def add(self, fn, args=(), kwargs=None, pos=None):
        """Queue one unit of work, with the RNG state it would have run under."""
        self._seq += 1
        # Store the position, not a distance: the focus can move, and a baked
        # distance would silently keep ordering by where the focus used to be.
        self.items.append((self._seq, fn, tuple(args), dict(kwargs or {}),
                           random.getstate(),
                           _xyz(pos) if pos is not None else self.focus))
        self._unsorted = True
        self.deadline = self._now() + max(1, int(self.over * TickDispatcher.tps))
        if self.task is None:
            self.task = TickDispatcher.do_interval(self._on_tick, 0)
        return self

    def set_focus(self, focus):
        """Move the point work is ordered nearest-first from."""
        self.focus = _xyz(focus)
        self._unsorted = True

    def _sort(self):
        """Nearest-first from the CURRENT focus; enqueue order breaks ties, so the
        drain order is stable and reproducible."""
        if not self._unsorted:
            return
        fx, fy, fz = self.focus

        def key(it):
            p = it[5]
            dx = p[0] - fx
            dy = p[1] - fy
            dz = p[2] - fz
            return (dx * dx + dy * dy + dz * dz, it[0])

        self.items.sort(key=key)
        self._unsorted = False

    def pending(self):
        return len(self.items)

    @staticmethod
    def _now():
        # The sim's counter, not TickDispatcher.current: `current` is only
        # refreshed inside dispatch_tick, so work queued before the first dispatch
        # of a mission would measure its deadline against the PREVIOUS mission's
        # clock and then drain at a crawl.
        try:
            return FrameContext.context.sim.time_tick_counter
        except Exception:
            return TickDispatcher.current

    def run_slice(self):
        """Run this tick's share. Returns how many items ran."""
        if not self.items:
            return 0
        self._sort()
        ticks_left = max(1, (self.deadline or 0) - self._now())
        self.accum += len(self.items) / ticks_left
        n = min(len(self.items), int(self.accum))
        if n <= 0:
            return 0
        self.accum -= n
        return self._run(n)

    def flush(self):
        """Run everything still queued, right now. Returns how many ran."""
        self._sort()
        n = self._run(len(self.items))
        self._stop()
        return n

    def clear(self):
        """Drop queued work without running it (mission reset)."""
        self.items = []
        self._stop()

    def _run(self, n):
        if n <= 0:
            return 0
        # Restore the caller's stream afterwards: the queue borrows the global RNG
        # per item, it does not consume the caller's sequence.
        state = random.getstate()
        try:
            for _ in range(n):
                _seq, fn, args, kwargs, rng, _pos = self.items.pop(0)
                random.setstate(rng)
                try:
                    fn(*args, **kwargs)
                except Exception as ex:
                    # One bad item must not take down the tick loop or the rest of
                    # the queue -- but it must not be silent either.
                    self.errors += 1
                    try:
                        from .procedural.execution import log
                        log(f"{self.name} drip item failed: {ex}", self.name, "error")
                    except Exception:
                        pass
        finally:
            random.setstate(state)
        return n

    def _on_tick(self, t=None):
        self.run_slice()
        if not self.items:
            self._stop()

    def _stop(self):
        if self.task is not None:
            try:
                self.task.stop()
            except Exception:
                pass
            self.task = None
        self.accum = 0.0
        self.deadline = None


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
