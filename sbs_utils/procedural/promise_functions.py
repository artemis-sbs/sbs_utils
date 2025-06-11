from ..futures import Promise, awaitable
from ..mast.pollresults import PollResults
from ..helpers import FrameContext
from .query import to_set, to_object, to_data_set, to_id
from ..vec import Vec3
from .grid import grid_pos_data


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
    def test():
        return FrameContext.context.sbs.distance_id(id1, id2) < distance
    return TestPromise(test)

@awaitable    
def distance_greater(id1, id2, distance):
    def test():
        return FrameContext.context.sbs.distance_id(id1, id2) > distance
    return TestPromise(test)

@awaitable
def distance_point_less(id1, point, distance):
    def test():
        obj = to_object(id1)
        if obj is None:
            return False
        diff = Vec3(obj.pos) - point
        return diff.length() < distance
    return TestPromise(test)

@awaitable   
def distance_point_greater(id1, point, distance):
    def test():
        obj = to_object(id1)
        if obj is None:
            return False
        diff = Vec3(obj.pos) - point
        return diff.length() > distance

    return TestPromise(test)

@awaitable
def destroyed_any(the_set, snapshot=False):
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
def grid_arrive_location(the_set, x, y, snapshot=False):
    the_set = to_set(the_set)
    if snapshot:
        the_set = set(the_set)
    def test():
        for id in the_set:
            curx, cury, path_length = grid_pos_data(id)
            if curx is None:
                return None
            if path_length is not None:
                if path_length > 0.001:
                    return False
            return curx == x and cury ==y
        return True
    return TestPromise(test)

@awaitable
def grid_arrive_id(the_set, target_id, snapshot=False):
    curx, cury, _ = grid_pos_data(target_id)
    if curx is None:
        p = Promise()
        p.cancel("Promise no longer valid")
        return p
    return grid_arrive_location(the_set, curx, cury, snapshot)
    
    

