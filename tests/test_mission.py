import sys
sys.modules['script'] = "This is a"
from sbs_utils.mast.mast import Mast
from sbs_utils.mast.maststory import MastStory
from sbs_utils.mast_sbs.maststoryscheduler import StoryScheduler
from sbs_utils.mast_sbs.mastmission import MissionLabel, StateMachineLabel
from sbs_utils.procedural.mission import mission_run, mission_runner
from mock import sbs as sbs
from sbs_utils.helpers import FrameContext, Context, FakeEvent
import unittest
from sbs_utils.agent import clear_shared

Mast.enable_logging()


def mast_story_compile(code=None):
    mast = MastStory()
    clear_shared()
    errors = mast.compile(code, "test", mast)
    return (errors, mast)

class TMastScheduler(StoryScheduler):
    def __init__(self, mast, overrides=None):
        super().__init__(mast, overrides)
        self.client_id = self.get_id()

    def runtime_error(self, message):
        print(f"RUNTIME ERROR: {message}")
        assert(False)


#FrameContext.sim= sbs.simulation()
class FakeSim:
    def __init__(self) -> None:
        self.time_tick_counter = 0
    def tick(self):
        self.time_tick_counter +=30

def mast_story_run(code=None, label=None):
    mast = MastStory()
    clear_shared()
    errors = []
    if code:
        errors = mast.compile(code, "test2", mast)
    else:
        mast.clear("test_code")
    
    if label is None:
        label = "main"
    FrameContext.context  = Context(FakeSim(), sbs, FakeEvent())
    runner = TMastScheduler(mast)
    task = None
    if len(errors)==0:
        task = runner.start_task(label)
    return (errors,runner, mast, task)


    

class TestMastMission(unittest.TestCase):


    def test_mission(self):
        (errors, runner, mast, task)= mast_story_run( code = """
logger(var="output")

# keep task alive for use
await delay_test(2)

//mission/test "Test"
                                                     
                                                     
#yield success

&&& init " w"
x = 0
log("Init")

# Dedent should return succcess

&&& start
log("Start")
# Dedent should return succcess

&&& abort
log("Abort")
# yield success
#dedent should fail i.e. not abort

&&& objective/test "Test"
log("Objective")
x +=1 
# dedent should yield success

&&& complete

if x <2:                                                     
    log("Complete no")
    yield fail
else:
    log("Complete yes")
# dedent should yield success

""")
        if len(errors)>0:
            for err in errors:
                print(err)
        assert(len(errors) == 0)
        i = 0
        mission = None
        for label in mast.labels:
            if label.startswith("mission"):
                i += 1
                mission = mast.labels.get(label)
        assert(i==1)
        assert(mission is not None)

        FrameContext.task = task
        m_task = mission_runner(mission)
        task.set_variable("__START__", True)
        for _ in m_task:
            pass
        output = runner.get_value("output", None)
        assert(output is not None)
        st = output[0]
        value = st.getvalue()
        #assert(value=="Init\nStart\nAbort\nObjective\nComplete no\nAbort\nObjective\nComplete yes\n")


