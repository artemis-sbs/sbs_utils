from ..mast.mast import Mast
from ..mast.mastscheduler import MastAsyncTask
from ..mast.mast_globals import MastGlobals


from ..lifetimedispatcher import LifetimeDispatcher
import sys
from ..gui import Gui
#
#
#
def handle_purge_tasks(so):
    """
    This will clear out all tasks related to the destroyed item
    """
    MastAsyncTask.stop_for_dependency(so.id)

LifetimeDispatcher.add_destroy(handle_purge_tasks)


from ..helpers import FrameContext
def mast_format_string(s):
    if FrameContext.task is not None:
        return FrameContext.task.compile_and_format_string(s)

MastGlobals.globals["mast_format_string"] = mast_format_string
MastGlobals.globals["script"] = sys.modules.get('script')

import sbs
from .. import vec
MastGlobals.globals["sbs"] = sbs
MastGlobals.globals['Vec3'] = vec.Vec3
for func in [
        ############################
        ## sbs
        sbs.distance_id,
        sbs.assign_client_to_ship,
        sbs.assign_client_to_alt_ship,
    ]:
    MastGlobals.globals[func.__name__] = func

def mast_assert(cond):
      assert(cond)

Mast.make_global_var("ASSERT", mast_assert)

#
# Expose procedural methods to script
#

MastGlobals.import_python_module('sbs_utils.procedural.timers')
MastGlobals.import_python_module('sbs_utils.procedural.query')
MastGlobals.import_python_module('sbs_utils.procedural.execution')
MastGlobals.import_python_module('sbs_utils.procedural.spawn')


MastGlobals.import_python_module('sbs_utils.procedural.grid')
MastGlobals.import_python_module('sbs_utils.procedural.internal_damage')
MastGlobals.import_python_module('sbs_utils.procedural.space_objects')
MastGlobals.import_python_module('sbs_utils.procedural.roles')
MastGlobals.import_python_module('sbs_utils.procedural.inventory')
MastGlobals.import_python_module('sbs_utils.procedural.links')
MastGlobals.import_python_module('sbs_utils.procedural.gui', allow_mismatch=True)
MastGlobals.import_python_module('sbs_utils.procedural.comms')
MastGlobals.import_python_module('sbs_utils.procedural.science')
MastGlobals.import_python_module('sbs_utils.procedural.cosmos')
MastGlobals.import_python_module('sbs_utils.procedural.routes')

MastGlobals.import_python_module('sbs_utils.procedural.behavior')
MastGlobals.import_python_module('sbs_utils.procedural.signal')
MastGlobals.import_python_module('sbs_utils.procedural.maps')
MastGlobals.import_python_module('sbs_utils.procedural.mission')
MastGlobals.import_python_module('sbs_utils.procedural.media')
MastGlobals.import_python_module('sbs_utils.procedural.objective')
MastGlobals.import_python_module('sbs_utils.procedural.upgrades')
MastGlobals.import_python_module('sbs_utils.procedural.docking')
MastGlobals.import_python_module('sbs_utils.procedural.brain')
MastGlobals.import_python_module('sbs_utils.procedural.prefab')
MastGlobals.import_python_module('sbs_utils.procedural.quest')
MastGlobals.import_python_module('sbs_utils.procedural.settings')
MastGlobals.import_python_module('sbs_utils.procedural.extra_scan_sources')
MastGlobals.import_python_module('sbs_utils.procedural.ship_data', 'ship_data')
MastGlobals.import_python_module('sbs_utils.procedural.sides')
MastGlobals.import_python_module('sbs_utils.procedural.lifeform')
MastGlobals.import_python_module('sbs_utils.procedural.terrain')
MastGlobals.import_python_module('sbs_utils.procedural.promise_functions')
MastGlobals.import_python_module('sbs_utils.procedural.dmx')
MastGlobals.import_python_module('sbs_utils.procedural.torpedoes')
MastGlobals.import_python_module('sbs_utils.procedural.modifiers')

# Load, but so far no functions to export
from ..procedural import popup
MastGlobals.import_python_module('sbs_utils.cards.card')
MastGlobals.import_python_module('sbs_utils.faces')
MastGlobals.import_python_module('sbs_utils.fs')
MastGlobals.import_python_module('sbs_utils.vec')


#
# These are exposed with a prepended module name
#
MastGlobals.import_python_module('sbs_utils.scatter', 'scatter')
MastGlobals.import_python_module('sbs_utils.names')
MastGlobals.import_python_module('sbs', 'sbs')

#
# These are needed so the import later works, domn't remove
#

######################
## Mast extensions
MastGlobals.import_python_module('sbs_utils.pages.widgets.shippicker')
MastGlobals.import_python_module('sbs_utils.pages.widgets.layout_listbox')

# Override named function

from ..procedural.execution import mast_log
Mast.make_global_var("log", mast_log)