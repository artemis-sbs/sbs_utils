

import sys

def mast_run(filename):
    script = sys.modules.get('script')
    if script is None:
        sys.modules['script'] = sys.modules.get('__main__')

    from sbs_utils.mast.mast import Mast
    from sbs_utils.mast.mastscheduler import MastScheduler, PollResults
    from sbs_utils.helpers import FrameContext, Context, FakeEvent
    
    import sbs_utils.procedural.execution as ex
    import sbs_utils.procedural.timers as timers
    import sbs_utils.procedural.behavior as behavior
    import sbs_utils.procedural.gui as gui
    import sbs_utils.procedural.signal as signal
    import sbs_utils.procedural.prefab as prefab
    from sbs_utils.mast.mast_globals import MastGlobals
    MastGlobals.import_python_module('sbs_utils.procedural.execution')
    MastGlobals.import_python_module('sbs_utils.procedural.behavior')
    MastGlobals.import_python_module('sbs_utils.procedural.timers')
    MastGlobals.import_python_module('sbs_utils.procedural.gui')
    MastGlobals.import_python_module('sbs_utils.procedural.signal')
    MastGlobals.import_python_module('sbs_utils.procedural.prefab')
   
    
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
    # FrameContext.context  = Context(FakeSim(), sbs, FakeEvent())
    FrameContext.mast = story
    runner = TMastScheduler(story)
    runner.start_task(label)
