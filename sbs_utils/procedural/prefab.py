from .execution import task_schedule
from ..futures import PromiseAllAny, awaitable
import re

class PrefabAll(PromiseAllAny):
    def __init__(self, proms) -> None:
        super().__init__(proms, True)
        self.set_built = False

    def result(self):
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


    return task_schedule(label, data=data, inherit=False)

__auto_name_counts = {}
def prefab_autoname(name):
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
