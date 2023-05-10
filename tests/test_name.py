import unittest
import sys
sys.path.append("..")
from mock import sbs as sbs
from sbs_utils import names
import sys
from sbs_utils.pymast.pymaststory import PyMastStory


def example_loose(self):
    print("Loose label")
    yield self.pop()


class ExampleStory(PyMastStory):

    def start(self):
        self.count = 0
        print("start")
        # yield self.delay(3)
        # print("start 2")
        # yield self.push("one")
        # yield self.push(example_loose)
        # print("END")


    
    def one(self):
        print("one")
        yield self.delay(5)
        yield self.jump("two")
        

    def two(self):
        print(f"two {self.count}")
        self.count += 1
        if self.count < 4:
            yield self.delay(5)
            yield self.jump("two")
        yield self.pop()
        
    
class FakeSim:
    def __init__(self) -> None:
        self.time_tick_counter = 0
    def tick(self):
        self.time_tick_counter +=30


class TestNames(unittest.TestCase):

    def test_init(self):
        for i in range(1296):
            sys.stdout.write(names.random_canonical_kralien_comms_id(i,"kralien_cruiser") +"   ")
            if i%6 == 5:
                sys.stdout.write('\n')
        self.assertEqual(3, 3)

    def test_something(self):
        sim = FakeSim()
        story = ExampleStory()
        story.enable(sim)


        for x in range(1000):
            story(sim)
            sim.tick()
        print()
   


    def test_filter_ship_data(self):
        ast = names.asteroid_keys()
        self.assertEqual(len(ast), 11)
        cast = names.crystal_asteroid_keys()
        self.assertEqual(len(cast), 5)
        past = names.plain_asteroid_keys()
        self.assertEqual(len(past), 6)

