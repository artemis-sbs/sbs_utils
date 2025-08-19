

import sys

from sbs_utils.helpers import FrameContext

class JustEnoughSim:
    def __init__(self):
        self.start = FrameContext.app_seconds
    @property
    def time_tick_counter(self):
        return int(FrameContext.app_seconds-self.start) * 30
    
class JustEnoughSbs:
    pass

def mast_run(filename):
    # script = sys.modules.get('script')
    # if script is None:
    #     sys.modules['script'] = sys.modules.get('__main__')

    from sbs_utils.mast.mast import Mast
    from sbs_utils.mast.mastscheduler import MastScheduler
    from sbs_utils.helpers import FrameContext, Context, FakeEvent
    

    from sbs_utils.mast.mast_globals import MastGlobals
    MastGlobals.import_python_module('sbs_utils.procedural.behavior') # Obsolete?
    MastGlobals.import_python_module('sbs_utils.procedural.brain')
    MastGlobals.import_python_module('sbs_utils.procedural.execution')
    MastGlobals.import_python_module('sbs_utils.procedural.inventory')
    MastGlobals.import_python_module('sbs_utils.procedural.lifeform')
    MastGlobals.import_python_module('sbs_utils.procedural.links')
    MastGlobals.import_python_module('sbs_utils.procedural.maps')
    MastGlobals.import_python_module('sbs_utils.procedural.objective')
    MastGlobals.import_python_module('sbs_utils.procedural.prefab')
    MastGlobals.import_python_module('sbs_utils.procedural.roles')
    MastGlobals.import_python_module('sbs_utils.procedural.signal')
    MastGlobals.import_python_module('sbs_utils.procedural.settings') #??
    MastGlobals.import_python_module('sbs_utils.procedural.timers') # Needs sim? Abstract it?
    from ..procedural.execution import mast_log
    Mast.make_global_var("log", mast_log)
    #
    # Uncomment this out to have Mast show the mast code in 
    # runtime errors.
    # Comment it out will reduce memory used.
    #
    Mast.include_code = True
    story = Mast()
    errors =  story.from_file(filename, None)
    if len(errors)>0:
        return errors


    class TMastScheduler(MastScheduler):
        def runtime_error(self, message):
            raise Exception(message)

    label = "main"
    FrameContext.context  = Context(JustEnoughSim(), JustEnoughSbs(), FakeEvent())
    FrameContext.mast = story
    runner = TMastScheduler(story)
    t = runner.start_task(label)
    while runner.tick():
        pass

