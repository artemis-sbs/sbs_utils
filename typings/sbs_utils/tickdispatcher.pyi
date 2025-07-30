from sbs_utils.agent import Agent
from sbs_utils.helpers import FrameContext
def get_task_id ():
    ...
class TickDispatcher(object):
    """The Tick Dispatcher is used to manager timed items via the HandleSimulationTick"""
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
