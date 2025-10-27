from .execution import task_schedule, sub_task_schedule
from ..futures import PromiseAllAny, awaitable
from ..helpers import FrameContext
import re

class PrefabAll(PromiseAllAny):
    def __init__(self, proms) -> None:
        super().__init__(proms, True)
        self.set_built = False

    def result(self):
        """
        Get a set of the results of all of the promises.
        Returns:
            set[Promise]: The set of promise results
        """
        #
        # Return just the results in order they finished
        #
        if len(self.promises) >0:
            return None
        if self.set_built:
            return self._results

        results = set()
        
        for p in self._result:
            if p is None:
                continue
            r = p.result()
            if isinstance(r, int):
                results.add(r)
            else:
                results.update(r)
        self.set_built = True
        self._result = results
        return self._result



@awaitable
def prefab_spawn(label, data=None, OFFSET_X=None, OFFSET_Y= None, OFFSET_Z= None):
    """
    Spawn a prefab and return its task.
    Args:
        label (str | Label): The label to run to spawn the prefab.
        data (dict, optional): Data associated with the prefab.
        * Positional data may be optionally included in `data`: `START_X`, `START_Y`, and `START_Z`. The default for these all is 0.
        OFFSET_X (int, optional): The X offset relative to the positional data. Default is None.
        OFFSET_Y (int, optional): The Y offset relative to the positional data. Default is None.
        OFFSET_Z (int, optional): The Z offset relative to the positional data. Default is None.
    Returns:
        MastAsyncTask: The task of the prefab.
    """
    name = ""
    sx = 0
    sy = 0
    sz = 0
    if data is not None:
        name = data.get("NAME")
        sx = data.get("START_X", sx)
        sy = data.get("START_Y", sy)
        sz = data.get("START_Z", sz)
        if name is not None:
            data["NAME"] = prefab_autoname(name)
    else:
        data = {}

    # If an offset used, apply it
    
    if OFFSET_X is not None:
        if sx is None:
            data["START_X"] = OFFSET_X
        else:
            data["START_X"] = sx + OFFSET_X

    if OFFSET_Y is not None:
        if sy is not None:
            data["START_Y"] = sy + OFFSET_Y
        else:
            data["START_Y"] = OFFSET_Y
    
    if OFFSET_Z is not None:
        if sz is not None:
            data["START_Z"] = sz + OFFSET_Z
        else:
            data["START_Z"] = OFFSET_Z

    t = task_schedule(label, data=data, defer=True, inherit=False)
    if t is None:
        print(f"Invalid prefab label: {label}")
        return None
    t.set_variable("self", t)
    t.set_variable("prefab", t)
    t.tick_in_context()
    return t

__auto_name_counts = {}
def prefab_autoname(name):
    """
    Apply a number to the given name if a `#` is included. Numbers are unique.
    Args:
        name (str): The name.
    Returns:
        str: The name with the number applied.
    """
    match = re.search(r'#|%', name)

    if match:
        first = match.start()
        start = name[:first]
        end = name[first:].strip()
        if end.startswith('#'):
            key = start.strip()
            count = __auto_name_counts.get(key, 1)
            __auto_name_counts[key] = count +1
            l = str(count).zfill(len(end))

            return start+l
        else:
            # get psuedo random 
            pass

    
    return name


@awaitable
def prefab_extends(label, data=None):
    """
    Add the label as a subtask of the current task.
    Args:
        label (str | Label): The label to run
        data (dict): The data associated with the prefab.
    Returns:
        MastAsyncTask: The prefab
    """
    prefab = FrameContext.task
    if data is None:
        data = {}
# Need to set the self and prefab properly
    data["self"] = prefab
    data["prefab"] = prefab
    t = sub_task_schedule(label, data=data)
    t.tick_in_context()
    return t