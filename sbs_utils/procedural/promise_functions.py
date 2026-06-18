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
def distance_less(obj_or_id1, obj_or_id2, distance):
    """Build a promise that resolves when two objects are closer than a distance.

    Args:
        obj_or_id1 (Agent | int): First space object or ID.
        obj_or_id2 (Agent | int): Second space object or ID.
        distance (float): Threshold distance in simulation units.

    Returns:
        TestPromise: Resolves when ``dist(obj1, obj2) < distance``.

    Example:
        await distance_less(SHIP_ID, ENEMY_ID, 500)
        "Enemy in range!"
    """
    def test():
        id1 = to_id(obj_or_id1)
        id2 = to_id(obj_or_id2)
        return FrameContext.context.sbs.distance_id(id1, id2) < distance
    return TestPromise(test)

@awaitable
def distance_greater(obj_or_id1, obj_or_id2, distance):
    """Build a promise that resolves when two objects are farther than a distance.

    Args:
        obj_or_id1 (Agent | int): First space object or ID.
        obj_or_id2 (Agent | int): Second space object or ID.
        distance (float): Threshold distance in simulation units.

    Returns:
        TestPromise: Resolves when ``dist(obj1, obj2) > distance``.

    Example:
        await distance_greater(SHIP_ID, ENEMY_ID, 2000)
        "Enemy out of range."
    """
    def test():
        id1 = to_id(obj_or_id1)
        id2 = to_id(obj_or_id2)
        return FrameContext.context.sbs.distance_id(id1, id2) > distance
    return TestPromise(test)

@awaitable
def distance_point_less(obj_or_id, point, distance):
    """Build a promise that resolves when an object is closer than a distance to a point.

    Args:
        obj_or_id (Agent | int): Space object or ID.
        point (Vec3): Reference point in simulation space.
        distance (float): Threshold distance in simulation units.

    Returns:
        TestPromise: Resolves when ``dist(obj, point) < distance``.

    Example:
        await distance_point_less(SHIP_ID, waypoint, 300)
        "Arrived at waypoint."
    """
    def test():
        obj = to_object(obj_or_id)
        if obj is None:
            return False
        diff = Vec3(obj.pos) - point
        return diff.length() < distance
    return TestPromise(test)

@awaitable
def distance_point_greater(obj_or_id, point, distance):
    """Build a promise that resolves when an object is farther than a distance from a point.

    Args:
        obj_or_id (Agent | int): Space object or ID.
        point (Vec3): Reference point in simulation space.
        distance (float): Threshold distance in simulation units.

    Returns:
        TestPromise: Resolves when ``dist(obj, point) > distance``.

    Example:
        await distance_point_greater(SHIP_ID, base_pos, 1000)
        "Ship has left the area."
    """
    def test():
        obj = to_object(obj_or_id)
        if obj is None:
            return False
        diff = Vec3(obj.pos) - point
        return diff.length() > distance

    return TestPromise(test)

@awaitable
def destroyed_any(the_set, snapshot=False):
    """Build a promise that resolves when any object in a set is destroyed.

    Args:
        the_set (Agent | int | set[Agent | int]): Object(s) to watch.
        snapshot (bool, optional): If True, take a copy of the set so later
            changes to the original do not affect what is watched. Defaults to
            False.

    Returns:
        TestPromise: Resolves as soon as any object in the set no longer exists.

    Example:
        await destroyed_any(enemies)
        "First kill achieved."
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
    """Build a promise that resolves when every object in a set is destroyed.

    Args:
        the_set (Agent | int | set[Agent | int]): Object(s) to watch.
        snapshot (bool, optional): If True, take a copy of the set so later
            changes to the original do not affect what is watched. Defaults to
            False.

    Returns:
        TestPromise: Resolves once no object in the set remains in the sim.

    Example:
        await destroyed_all(enemies)
        "All enemies eliminated!"
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
    """Build a promise that resolves when grid objects finish moving.

    Checks whether the first object in the set no longer has the ``_moving_``
    role. The ``x`` and ``y`` parameters are accepted for API compatibility but
    are not used.

    Args:
        the_set (Agent | int | set[Agent | int]): Grid object(s) to watch.
        x (int, optional): Unused target column. Defaults to 0.
        y (int, optional): Unused target row. Defaults to 0.
        snapshot (bool, optional): If True, copy the set so later changes don't
            affect what is watched. Defaults to False.

    Returns:
        TestPromise: Resolves when the first object in the set is no longer
            moving.
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
    """Build a promise that resolves when grid objects arrive at a target cell.

    Resolves the target cell position from ``target_id`` and delegates to
    ``grid_arrive_location``.

    Args:
        the_set (Agent | int | set[Agent | int]): Grid object(s) to watch.
        target_id (int): ID of the grid object whose current position is used as
            the target cell.
        snapshot (bool, optional): If True, copy the set so later changes don't
            affect what is watched. Defaults to False.

    Returns:
        TestPromise: Resolves when movement is complete, or a cancelled promise
            if ``target_id`` has no grid position.
    """
    # TODO: Update this function? grid_arrive_location doesn't use curx and cury
    curx, cury, _ = grid_pos_data(target_id)
    if curx is None:
        p = Promise()
        p.cancel("Promise no longer valid")
        return p
    return grid_arrive_location(the_set, curx, cury, snapshot)
    
    

