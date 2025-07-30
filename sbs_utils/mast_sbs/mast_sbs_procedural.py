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

from ..procedural import query
MastGlobals.import_python_module('sbs_utils.procedural.query')
from ..procedural import spawn
MastGlobals.import_python_module('sbs_utils.procedural.spawn')
from ..procedural import timers
MastGlobals.import_python_module('sbs_utils.procedural.timers')
from ..procedural import grid
MastGlobals.import_python_module('sbs_utils.procedural.grid')
from ..procedural import internal_damage
MastGlobals.import_python_module('sbs_utils.procedural.internal_damage')
from ..procedural import space_objects
MastGlobals.import_python_module('sbs_utils.procedural.space_objects')
from ..procedural import roles
MastGlobals.import_python_module('sbs_utils.procedural.roles')
from ..procedural import inventory
MastGlobals.import_python_module('sbs_utils.procedural.inventory')
from ..procedural import links
MastGlobals.import_python_module('sbs_utils.procedural.links')
from ..procedural import gui
MastGlobals.import_python_module('sbs_utils.procedural.gui')
from ..procedural import comms
MastGlobals.import_python_module('sbs_utils.procedural.comms')
from ..procedural import science
MastGlobals.import_python_module('sbs_utils.procedural.science')
from ..procedural import cosmos
MastGlobals.import_python_module('sbs_utils.procedural.cosmos')
from ..procedural import routes
MastGlobals.import_python_module('sbs_utils.procedural.routes')
from ..procedural import execution
MastGlobals.import_python_module('sbs_utils.procedural.execution')
from ..procedural import behavior
MastGlobals.import_python_module('sbs_utils.procedural.behavior')
from ..procedural import signal
MastGlobals.import_python_module('sbs_utils.procedural.signal')
from ..procedural import maps
MastGlobals.import_python_module('sbs_utils.procedural.maps')
from ..procedural import mission
MastGlobals.import_python_module('sbs_utils.procedural.mission')
from ..procedural import media
MastGlobals.import_python_module('sbs_utils.procedural.media')
from ..procedural import objective
MastGlobals.import_python_module('sbs_utils.procedural.objective')
from ..procedural import upgrades
MastGlobals.import_python_module('sbs_utils.procedural.upgrades')
from ..procedural import docking
MastGlobals.import_python_module('sbs_utils.procedural.docking')
from ..procedural import brain
MastGlobals.import_python_module('sbs_utils.procedural.brain')
from ..procedural import prefab
MastGlobals.import_python_module('sbs_utils.procedural.prefab')
from ..procedural import settings
MastGlobals.import_python_module('sbs_utils.procedural.settings')
from ..procedural import extra_scan_sources
MastGlobals.import_python_module('sbs_utils.procedural.extra_scan_sources')
from ..procedural import ship_data
MastGlobals.import_python_module('sbs_utils.procedural.ship_data', 'ship_data')
from ..procedural import lifeform
MastGlobals.import_python_module('sbs_utils.procedural.lifeform')
from ..procedural import terrain
MastGlobals.import_python_module('sbs_utils.procedural.terrain')
from ..procedural import promise_functions
MastGlobals.import_python_module('sbs_utils.procedural.promise_functions')

# Load, but so far no functions to export
from ..procedural import popup


from ..cards import card
MastGlobals.import_python_module('sbs_utils.cards.card')
from .. import faces
MastGlobals.import_python_module('sbs_utils.faces')
MastGlobals.import_python_module('sbs_utils.fs')
from .. import vec
MastGlobals.import_python_module('sbs_utils.vec')


#
# These are exposed with a prepended module name
#
from .. import scatter
MastGlobals.import_python_module('sbs_utils.scatter', 'scatter')
from .. import names
MastGlobals.import_python_module('sbs_utils.names')


MastGlobals.import_python_module('sbs', 'sbs')

#
# These are needed so the import later works, domn't remove
#

######################
## Mast extensions
from sbs_utils.pages.widgets.shippicker import ShipPicker
MastGlobals.import_python_module('sbs_utils.pages.widgets.shippicker')
from sbs_utils.pages.widgets.layout_listbox import layout_list_box_control
MastGlobals.import_python_module('sbs_utils.pages.widgets.layout_listbox')
