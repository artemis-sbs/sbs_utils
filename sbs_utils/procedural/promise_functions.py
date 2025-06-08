from ..futures import Promise, awaitable
from ..mast.pollresults import PollResults
from ..helpers import FrameContext
from .query import to_set, to_object
from ..vec import Vec3


class TestPromise(Promise):
    def __init__(self, test_func) -> None:
        super().__init__()
        self.test = test_func
    
    def poll(self):
        if self.test():
            self.set_result(True)
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
