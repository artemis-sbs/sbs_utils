import unittest
import sys
sys.path.append("..")
from mock import sbs
import sys
from sbs_utils.pymast.pymaststory import PyMastStory
from sbs_utils.pymast.pollresults import PollResults
from io import StringIO
import logging


def example_loose(self):
    print("Loose label")
    yield self.pop()

log_stream = StringIO()    
logging.basicConfig(stream=log_stream, format=("%(message)s"), level=logging.INFO)    
    
class FakeSim:
    def __init__(self) -> None:
        self.time_tick_counter = 0
    def tick(self):
        self.time_tick_counter +=30


class TestPymast(unittest.TestCase):

    def setUp(self):
        """ 
        Run on each test. This clears the logger for fresh use.
        note: Making a logger each time was inconsistant 
        """
        global log_stream
        log_stream.truncate(0)
        log_stream.seek(0)



    def test_simple(self):
        class ExampleStory(PyMastStory):

            def start(self):
                self.count = 0
                logging.info("start")
                yield self.jump(self.one)
                
            
            def one(self):
                logging.info('one')
                yield self.delay(5)
                yield self.push("two")
                logging.info("end")
                

            def two(self):
                logging.info(f"two {self.count}")
                self.count += 1
                if self.count < 4:
                    yield self.delay(5)
                    yield self.jump("two")
                yield self.pop()

        sim = FakeSim()
        story = ExampleStory()
        story.enable(sim)
        story.add_scheduler(sim, story.start)


        for x in range(1000):
            story(sim)
            sim.tick()
        v = log_stream.getvalue()
        t = """start
one
two 0
two 1
two 2
two 3
end
"""
        assert(v == t)

    def test_behave(self):
        class ExampleStory(PyMastStory):

            def start(self):
                self.count = 0
                self.count = 0
                logging.info("Before")
                
                #yield self.task.behave_until_success(lambda: self.task.behave_seq(self.one, self.two, self.three))
                yield self.task.behave_seq(self.one, self.two, self.three)

                logging.info("After")
                    
            
            def one(self):
                
                for i in range(5):
                    logging.info(f'one {self.count}')
                    self.count += 1
                    if self.count==0:
                        yield PollResults.FAIL_END
                    yield self.delay(5)

                yield PollResults.OK_END
            
            def two(self):
                logging.info('two')
                yield self.delay(5)
                yield PollResults.OK_END

            def three(self):
                logging.info('three')
                yield self.delay(5)
                yield PollResults.OK_END

        sim = FakeSim()
        story = ExampleStory()
        story.enable(sim)
        story.add_scheduler(sim, story.start)


        for x in range(1000):
            story(sim)
            sim.tick()
        v = log_stream.getvalue()
        t = """Before
one 0
one 1
one 2
one 3
one 4
two
three
After
"""
        assert(v == t)

    def test_behave_invert(self):
        class ExampleStory(PyMastStory):

            def start(self):
                self.count = 0
                self.count = 0
                logging.info("Before")
                
                #yield self.task.behave_until_success(lambda: self.task.behave_seq(self.one, self.two, self.three))
                yield self.task.behave_invert(self.one)
                assert(self.task.last_popped_poll_result == PollResults.FAIL_END)
                yield self.task.behave_invert(self.two)
                assert(self.task.last_popped_poll_result == PollResults.OK_END)
                logging.info("After")
                    
            
            def one(self):
                yield PollResults.OK_END

            def two(self):
                yield PollResults.FAIL_END


        sim = FakeSim()
        story = ExampleStory()
        story.enable(sim)
        story.add_scheduler(sim, story.start)


        for x in range(1000):
            story(sim)
            sim.tick()
        v = log_stream.getvalue()
        t = """Before
After
"""
        assert(v == t)
   
    def test_behave_until(self):
        class ExampleStory(PyMastStory):

            def start(self):
                self.count = 0
                logging.info("Before")
                yield self.task.behave_until(PollResults.OK_END, self.one)
                # Make sure it returns to the original flow
                logging.info("After")
                    
            
            def one(self):
                for i in range(5):
                    logging.info(f"one {i}")
                    yield PollResults.FAIL_END
                yield PollResults.OK_RUN_AGAIN
                yield PollResults.OK_ADVANCE_TRUE
                yield PollResults.OK_ADVANCE_FALSE
                logging.info(f"yep")
                yield PollResults.OK_END
                logging.info(f"nope")


        sim = FakeSim()
        story = ExampleStory()
        story.enable(sim)
        story.add_scheduler(sim, story.start)


        for x in range(1000):
            story(sim)
            sim.tick()
        v = log_stream.getvalue()
        t = """Before
one 0
one 1
one 2
one 3
one 4
yep
After
"""
        print(v)
        assert(v == t)
   
    def test_behave_logic(self):
        class ExampleStory(PyMastStory):

            def start(self):
                self.have_apple = False
                self.count = 0
                logging.info("Before")
                
                self.schedule_task(self.find_food)
                self.schedule_task(self.behave)
                
                # Make sure it returns to the original flow
                logging.info("After")
                

            def behave(self):
                yield self.behave_until(PollResults.OK_END, self.not_hungry)
            
            def not_hungry(self):
                yield self.behave_seq(self.have_food, self.eat_food)

            def have_food(self):
                if self.have_apple:
                    yield PollResults.OK_END
                yield PollResults.FAIL_END

            def eat_food(self):
                if self.have_apple:
                    self.have_apple = False
                    yield PollResults.OK_END
                    return
                yield PollResults.FAIL_END
            def find_food(self):
                for i in range(3):
                    logging.info(f"find {i}")
                    yield self.delay(5)
                    #yield PollResults.OK_RUN_AGAIN
                logging.info("Found Apple")
                self.have_apple = True
                

        sim = FakeSim()
        story = ExampleStory()
        story.enable(sim)
        story.add_scheduler(sim, story.start)


        for x in range(1000):
            story(sim)
            sim.tick()
        v = log_stream.getvalue()
        t = """Before
After
find 0
find 1
find 2
Found Apple
"""
        assert(v == t)
   
    




class ExampleStory(PyMastStory):
    def start(self):
        self.have_apple = False
        yield self.schedule_task(self.simulate_find_food)
        yield self.schedule_task(self.behavior)
        # This task ends

    def behavior(self):
        # Keep Running the goal until it is successful
        yield self.behave_until(PollResults.OK_END, self.not_hungry)
    
    # Goal to not be hungry by first having food, then eating it
    def not_hungry(self):
        yield self.behave_seq(self.have_food, self.eat_food)

    def have_food(self):
        # Succeed only when you have the apple or banana
        yield self.behave_sel(self.check_apple, self.check_banana)

    def check_apple(self):
        # Succeed only when you have the apple
        yield PollResults.OK_END if self.have_apple else PollResults.FAIL_END
    def check_banana(self):
        # Succeed only when you have the apple
        yield PollResults.OK_END if self.have_apple else PollResults.FAIL_END

    def eat_food(self):
        if self.have_apple:
            self.have_apple = False
            yield PollResults.OK_END
            return
        if self.have_banana:
            self.have_banana = False
            yield PollResults.OK_END
            return
        yield PollResults.FAIL_END

    # After 15 seconds find an apple
    def simulate_find_food(self):
        yield self.delay(15)
        self.have_apple = True
    
def behavoir_simple(self):
    # Keep Running the goal until it is successful
    if self.have_apple:
        # eat
        self.have_apple = False
        yield PollResults.OK_END
    elif self.have_banana:
        #eat
        self.have_banana = False
        yield PollResults.OK_END
    yield PollResults.FAIL_END



