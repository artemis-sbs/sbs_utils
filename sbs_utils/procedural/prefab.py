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
    """Spawn a prefab label as an independent task and return it.

    Positional keys ``START_X``, ``START_Y``, ``START_Z`` inside ``data``
    set the spawn origin (default 0). The ``OFFSET_*`` params shift that
    origin without modifying the original ``data`` dict. If ``data`` contains
    a ``NAME`` key with a ``#`` placeholder, ``prefab_autoname`` is applied
    to generate a unique name.

    Args:
        label (str | Label): The label to spawn.
        data (dict, optional): Variables passed into the prefab task. May
            include ``START_X``, ``START_Y``, ``START_Z``, and ``NAME``.
            Defaults to None.
        OFFSET_X (float, optional): X offset added to ``START_X``. Defaults
            to None (no offset).
        OFFSET_Y (float, optional): Y offset added to ``START_Y``. Defaults
            to None (no offset).
        OFFSET_Z (float, optional): Z offset added to ``START_Z``. Defaults
            to None (no offset).

    Returns:
        MastAsyncTask: The running prefab task, or ``None`` if the label is
            invalid.
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
    """Return ``name`` with the ``#`` placeholder replaced by an auto-incrementing number.

    If ``name`` contains ``#``, the prefix before ``#`` is used as a counter
    key and the ``#`` (plus any trailing characters) is replaced with a
    zero-padded incrementing integer. Names without ``#`` are returned
    unchanged.

    Args:
        name (str): Name template, optionally containing ``#``.

    Returns:
        str: The name with ``#`` replaced by a unique number, or the original
            name if no ``#`` was found.
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
    """Run a prefab label as a sub-task of the current task.

    Unlike ``prefab_spawn``, which creates an independent task, this attaches
    the prefab as a child of the calling task and sets ``self``/``prefab``
    variables so the sub-task can refer back to its parent.

    Args:
        label (str | Label): The label to run as a sub-task.
        data (dict, optional): Variables passed into the sub-task. Defaults to
            None.

    Returns:
        MastAsyncTask: The running sub-task.
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