import unittest
import sys
sys.path.append("..")
from mock import sbs as sbs
from sbs_utils import names
import sys
from sbs_utils.pymast.pymaststory import PyMastStory
from sbs_utils.helpers import FrameContext, Context
from sbs_utils.tickdispatcher import TickDispatcher



    
class FakeSim:
    def __init__(self) -> None:
        self.time_tick_counter = 0
    def tick(self):
        self.time_tick_counter +=30


class TestDispatcher(unittest.TestCase):

    def test_init(self):
        pass

    def inc_count(self, t):
        self.count += 1

    def test_something(self):
        ctx = Context(FakeSim(), sbs)
        FrameContext.context = ctx
        self.count = 0
        TickDispatcher.do_once(self.inc_count, 0)
        TickDispatcher.do_interval(self.inc_count, 0, 5)


        for x in range(1000):
            TickDispatcher.dispatch_tick()
            ctx.sim.tick()

        assert(self.count == 6)
   


