from ..futures import Promise, awaitable
from ..mast.pollresults import PollResults
from ..helpers import FrameContext
from .query import to_set, to_object, to_data_set, to_id
from ..vec import Vec3
from .grid import grid_pos_data
from .roles import has_role


class TestPromise(Promise):
    def __init__(self, test_func) -> None:
        super().__init__()
        self.test = test_func
    
    def poll(self):
        t = self.test()
        if t:
            self.set_result(True)
            return PollResults.OK_ADVANCE_TRUE
        elif t is None:
            self.cancel("Promise no longer valid")
            return PollResults.OK_ADVANCE_TRUE
        return super().poll()
    
@awaitable
def distance_less(id1, id2, distance):
    """
    Build a Promise that waits until the distance between the two objects is less than the specified value.
    Args:
        id1 (int): The ID of the first space object.
        id2 (int): The ID of the second space object.
        distance (int): The distance between the two objects.
    Returns:
        Promise: The promise
    """
    def test():
        return FrameContext.context.sbs.distance_id(id1, id2) < distance
    return TestPromise(test)

@awaitable    
def distance_greater(id1, id2, distance):
    """
    Build a Promise that waits until the distance between the two objects is greater than the specified value.
    Args:
        id1 (int): The ID of the first space object.
        id2 (int): The ID of the second space object.
        distance (int): The distance between the two objects.
    Returns:
        Promise: The promise
    """
    def test():
        return FrameContext.context.sbs.distance_id(id1, id2) > distance
    return TestPromise(test)

@awaitable
def distance_point_less(id1, point, distance):
    """
    Build a Promise that waits until the distance between the object and the point is less than the specified value.
    Args:
        id1 (int): The ID of the first space object.
        point (Vec3): The point.
        distance (int): The distance between the object and the point.
    Returns:
        Promise: The promise
    """
    def test():
        obj = to_object(id1)
        if obj is None:
            return False
        diff = Vec3(obj.pos) - point
        return diff.length() < distance
    return TestPromise(test)

@awaitable   
def distance_point_greater(id1, point, distance):
    """
    Build a Promise that waits until the distance between the object and the point is less than the specified value.
    Args:
        id1 (int): The ID of the first space object.
        point (Vec3): The point.
        distance (int): The distance between the object and the point.
    Returns:
        Promise: The promise
    """
    def test():
        obj = to_object(id1)
        if obj is None:
            return False
        diff = Vec3(obj.pos) - point
        return diff.length() > distance

    return TestPromise(test)

@awaitable
def destroyed_any(the_set, snapshot=False):
    """
    Build a Promise that waits until any objects in the set are destroyed.
    Args:
        the_set (set[id])
        snapshot (bool, optional): If True, the set checked will not change if the original set changes.
    Returns:
        TestPromise: The promise.
    """
    the_set = to_set(the_set)
    if snapshot:
        the_set = set(the_set)
    def test():
        for id in the_set:
            if not FrameContext.context.sim.space_object_exists(id):
                return True
        return False
    return TestPromise(test)

@awaitable
def destroyed_all(the_set, snapshot=False):
    """
    Build a Promise that waits until all objects in the set are destroyed.
    Args:
        the_set (set[id])
        snapshot (bool, optional): If True, the set checked will not change if the original set changes.
    Returns:
        TestPromise: The promise.
    """
    the_set = to_set(the_set)
    if snapshot:
        the_set = set(the_set)
    def test():
        for id in the_set:
            if FrameContext.context.sim.space_object_exists(id):
                return False
        return True
    return TestPromise(test)



@awaitable
def grid_arrive_location(the_set, x=0, y=0, snapshot=False):
    """
    Build a Promise that waits until the grid object agents have completed their movement.
    Args:
        the_set (Agent | int | set[Agent | int]): The grid object or id or set to check
        x (int, optional): Not used
        y (int, optional): Not used
        snapshot (bool, optional): If True, the set checked will not change if the original set changes.
    Returns:
        TestPromise: The promise.
    """
    # TODO: Update this function? x and y not used.
    the_set = to_set(the_set)
    if snapshot:
        the_set = set(the_set)
    def test():
        for id in the_set:
            return not has_role(id, "_moving_")
        return True
    return TestPromise(test)

@awaitable
def grid_arrive_id(the_set, target_id, snapshot=False):
    """
    Build a Promise that waits until the grid object agents have completed their movement.
    Args:
        the_set (Agent | int | set[Agent | int]): The grid object or id or set to check
        target_id (int): The target grid object ID
        snapshot (bool, optional): If True, the set checked will not change if the original set changes.
    """
    # TODO: Update this function? grid_arrive_location doesn't use curx and cury
    curx, cury, _ = grid_pos_data(target_id)
    if curx is None:
        p = Promise()
        p.cancel("Promise no longer valid")
        return p
    return grid_arrive_location(the_set, curx, cury, snapshot)
    
    

