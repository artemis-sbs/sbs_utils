from sbs_utils.agent import Agent
from sbs_utils.helpers import FrameContext
def _xyz (p):
    """Accept a Vec3, an (x, y, z) tuple, or None."""
def get_task_id ():
    ...
class DripQueue(object):
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
        q.flush()          # or let it drain itself, a slice per tick"""
    def __init__ (self, over=6.0, focus=None, name='drip'):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def _now ():
        ...
    def _on_tick (self, t=None):
        ...
    def _run (self, n):
        ...
    def _sort (self):
        """Nearest-first from the CURRENT focus; enqueue order breaks ties, so the
        drain order is stable and reproducible."""
    def _stop (self):
        ...
    def add (self, fn, args=(), kwargs=None, pos=None):
        """Queue one unit of work, with the RNG state it would have run under."""
    def clear (self):
        """Drop queued work without running it (mission reset)."""
    def flush (self):
        """Run everything still queued, right now. Returns how many ran."""
    def pending (self):
        ...
    def run_slice (self):
        """Run this tick's share. Returns how many items ran."""
    def set_focus (self, focus):
        """Move the point work is ordered nearest-first from."""
class RollingSlicer(object):
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
            ...work one item..."""
    def __init__ (self):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def slice (self, ids, pass_seconds):
        ...
class TickDispatcher(object):
    """The Tick Dispatcher is used to manager timed items via the HandleSimulationTick"""
    def clear ():
        """Drop all scheduled ticks (fresh mission / in-process recompile)."""
    def dispatch_tick ():
        """Process all the tasks
        The task is updated to see if it should be triggered,
        and if it is completed"""
    def do_interval (cb: callable, delay: int, count: int = None):
        """Create and return a task that executes more than once
        
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
                    t.stop()"""
    def do_once (cb: callable, delay: int):
        """Create and return a task that executes once
        
        :param delay: the time in seconds for the task to delay
        :type delay: int
        :return: The task is returned and can be used to attach data for future use.
        :rtype: TickTask
        
        example:
            def some_use():
                t = TickDispatcher.do_once(the_callback, 5)
                t.data = some_data
        
            def the_callback(t):
                print(t.some_data)"""
class TickTask(Agent):
    """A task that is managed by the TickDispatcher"""
    def __init__ (self, cb, delay, count):
        """new TickTask
        
        :param sim: The Artemis Cosmos simulation
        :param cb: call back function
        :param delay: the time in seconds for the task to delay
        :type delay: int
        :param count: The number of times to run None mean infinite
        :type count: int or None"""
    def _add (id, obj):
        ...
    def _remove (id):
        ...
    def _update (self):
        ...
    def clear ():
        ...
    @property
    def done (self) -> bool:
        """returns if this is the task will not run in the future
                """
    def get (id):
        ...
    def get_as (id, as_cls):
        ...
    def get_objects_from_set (the_set):
        ...
    def get_role_object (link_name):
        ...
    def get_role_objects (role):
        ...
    def get_role_set (role):
        ...
    def has_inventory_list (collection_name):
        ...
    def has_inventory_set (collection_name):
        ...
    def has_links_list (collection_name):
        ...
    def has_links_set (collection_name):
        ...
    def remove_id (id):
        ...
    def resolve_id (other: 'Agent | CloseData | int'):
        ...
    def resolve_py_object (other: 'Agent | CloseData | int'):
        ...
    def stop (self):
        """Stop a tasks
        The task is removed"""
