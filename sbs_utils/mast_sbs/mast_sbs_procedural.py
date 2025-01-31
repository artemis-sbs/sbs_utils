from ..mast.mast import Mast
from ..mast.mastscheduler import MastAsyncTask
import sbs
from .mastobjects import  MastSpaceObject
from ..mast.mast_globals import MastGlobals


from ..lifetimedispatcher import LifetimeDispatcher
from ..gui import Gui
from .. import faces
import sys

import re
from ..procedural import query
from ..procedural import links
from ..procedural import inventory

from .. import vec

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

MastGlobals.globals["SpaceObject"] =MastSpaceObject
MastGlobals.globals["script"] = sys.modules['script']
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
from ..procedural import spawn
from ..procedural import timers
from ..procedural import grid
from ..procedural import internal_damage
from ..procedural import space_objects
from ..procedural import ship_data
from ..procedural import roles
from ..procedural import inventory
from ..procedural import links
from ..procedural import gui
from ..procedural import comms
from ..procedural import science
from ..procedural import cosmos
from ..procedural import routes
from ..procedural import execution
from ..procedural import behavior
from ..procedural import signal
from ..procedural import maps
from ..procedural import mission
from ..procedural import media
from ..cards import card


Mast.import_python_module('sbs_utils.procedural.query')
Mast.import_python_module('sbs_utils.procedural.spawn')
Mast.import_python_module('sbs_utils.procedural.timers')
Mast.import_python_module('sbs_utils.procedural.grid')
Mast.import_python_module('sbs_utils.procedural.internal_damage')
Mast.import_python_module('sbs_utils.procedural.space_objects')
Mast.import_python_module('sbs_utils.procedural.roles')
Mast.import_python_module('sbs_utils.procedural.inventory')
Mast.import_python_module('sbs_utils.procedural.links')
Mast.import_python_module('sbs_utils.procedural.gui')
Mast.import_python_module('sbs_utils.procedural.comms')
Mast.import_python_module('sbs_utils.procedural.science')
Mast.import_python_module('sbs_utils.procedural.cosmos')
Mast.import_python_module('sbs_utils.procedural.routes')
Mast.import_python_module('sbs_utils.procedural.execution')
Mast.import_python_module('sbs_utils.procedural.behavior')
Mast.import_python_module('sbs_utils.procedural.signal')
Mast.import_python_module('sbs_utils.procedural.maps')
Mast.import_python_module('sbs_utils.procedural.mission')
Mast.import_python_module('sbs_utils.procedural.media')
Mast.import_python_module('sbs_utils.cards.card')
Mast.import_python_module('sbs_utils.faces')
Mast.import_python_module('sbs_utils.fs')
Mast.import_python_module('sbs_utils.vec')
#
# These are exposed with a prepended module name
#
Mast.import_python_module('sbs_utils.scatter', 'scatter')
Mast.import_python_module('sbs_utils.names', 'names')
Mast.import_python_module('sbs_utils.procedural.ship_data', 'ship_data')
Mast.import_python_module('sbs', 'sbs')

#
# These are needed so the import later works, domn't remove
#
from sbs_utils.pages.widgets.listbox import Listbox
from sbs_utils.pages.widgets.layout_listbox import layout_list_box_control
from sbs_utils.pages.widgets.shippicker import ShipPicker

######################
## Mast extensions
Mast.import_python_module('sbs_utils.pages.widgets.shippicker')
Mast.import_python_module('sbs_utils.pages.widgets.listbox')
Mast.import_python_module('sbs_utils.pages.widgets.layout_listbox')
