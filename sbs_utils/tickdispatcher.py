from .helpers import FrameContext
from .engineobject import EngineObject, get_task_id

class TickTask(EngineObject):
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
            TickDispatcher._dispatch_tick.remove(c)
