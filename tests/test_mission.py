from sbs_utils.mast.mast import Mast
from sbs_utils.mast.maststory import MastStory
import unittest
from sbs_utils.agent import clear_shared

Mast.enable_logging()


def mast_story_compile(code=None):
    mast = MastStory()
    clear_shared()
    errors = mast.compile(code, "test", mast)
    return (errors, mast)

def mast_story_compile_file(code=None):
    mast = MastStory()
    clear_shared()
    errors = mast.from_file(code, None)
    return (errors, mast)




    
    

class TestMastMission(unittest.TestCase):


    def test_mission(self):
        (errors, mast)= mast_story_compile( code = """
logger(var="output")    

//mission/test "Test"

init:
    log("Init")

start:
    log("Start")

abort:
    log("Fail")

objective/test "Test":
    log("Objective")

complete:
    log("complete")
""")
        if len(errors)>0:
            for err in errors:
                print(err)
        assert(len(errors) == 0)

