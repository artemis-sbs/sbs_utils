from ..mast.mast import Mast
from ..mast.mastscheduler import MastAsyncTask
from ..mast.mast_globals import MastGlobals


from ..lifetimedispatcher import LifetimeDispatcher
import sys
from ..gui import Gui
#
#
#
def handle_purge_tasks(so, event=None):
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
# Art lives once now, in a folder named for the pack VERSION, so MAST asks for the
# logical path (`media_shared("casino")`) and never writes the version itself.
MastGlobals.import_python_module('sbs_utils.procedural.media_paths')
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
MastGlobals.import_python_module('sbs_utils.procedural.standby')
MastGlobals.import_python_module('sbs_utils.procedural.prefab')
MastGlobals.import_python_module('sbs_utils.procedural.quest')
MastGlobals.import_python_module('sbs_utils.procedural.quest_driver')
MastGlobals.import_python_module('sbs_utils.procedural.amd')
MastGlobals.import_python_module('sbs_utils.procedural.amd_quest')
MastGlobals.import_python_module('sbs_utils.procedural.amd_science')
MastGlobals.import_python_module('sbs_utils.procedural.amd_doc')
MastGlobals.import_python_module('sbs_utils.procedural.reputation')
MastGlobals.import_python_module('sbs_utils.procedural.amd_dialogue')
MastGlobals.import_python_module('sbs_utils.procedural.amd_landmarks')
MastGlobals.import_python_module('sbs_utils.procedural.amd_sides')
MastGlobals.import_python_module('sbs_utils.procedural.amd_images')
MastGlobals.import_python_module('sbs_utils.procedural.amd_lifeforms')
MastGlobals.import_python_module('sbs_utils.procedural.amd_chatter')
MastGlobals.import_python_module('sbs_utils.procedural.amd_items')
MastGlobals.import_python_module('sbs_utils.procedural.amd_mission')
MastGlobals.import_python_module('sbs_utils.procedural.amd_overlay')
# Declarative cinematics. Registered HERE because that is the only thing that makes
# a function callable from MAST - importing it in a mission's own .py does NOT (the
# mission's imports are not merged into the global namespace, only the functions it
# DEFINES are). Without this line the whole AMD cinematics front door was Python-only,
# which for a layer whose entire audience writes MAST means it did not exist.
MastGlobals.import_python_module('sbs_utils.procedural.amd_cutscene')
MastGlobals.import_python_module('sbs_utils.procedural.announce')
MastGlobals.import_python_module('sbs_utils.procedural.persistence')
MastGlobals.import_python_module('sbs_utils.procedural.settings')
MastGlobals.import_python_module('sbs_utils.procedural.extra_scan_sources')
MastGlobals.import_python_module('sbs_utils.procedural.ship_data', 'ship_data')
MastGlobals.import_python_module('sbs_utils.procedural.sides')
MastGlobals.import_python_module('sbs_utils.procedural.lifeform')
MastGlobals.import_python_module('sbs_utils.procedural.terrain')
MastGlobals.import_python_module('sbs_utils.procedural.items')
MastGlobals.import_python_module('sbs_utils.procedural.promise_functions')
MastGlobals.import_python_module('sbs_utils.procedural.dmx')
MastGlobals.import_python_module('sbs_utils.procedural.torpedoes')
MastGlobals.import_python_module('sbs_utils.procedural.modifiers')
MastGlobals.import_python_module('sbs_utils.procedural.web')
MastGlobals.import_python_module('sbs_utils.procedural.grav_tether')

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
# Artemis 2.x (2.8) porting-comfort layer -> a2x_ prefixed MAST globals (e.g. a2x_pos)
MastGlobals.import_python_module('sbs_utils.procedural.a2x', 'a2x')

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