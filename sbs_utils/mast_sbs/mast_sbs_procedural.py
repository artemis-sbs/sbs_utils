from ..mast.mast import Mast
from ..mast.mastscheduler import MastAsyncTask
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
MastGlobals.globals["script"] = sys.modules['script']

import sbs
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
from ..procedural import objective
from ..procedural import upgrades
from ..procedural import docking
from ..procedural import extra_scan_sources
from ..cards import card


MastGlobals.import_python_module('sbs_utils.procedural.query')
MastGlobals.import_python_module('sbs_utils.procedural.spawn')
MastGlobals.import_python_module('sbs_utils.procedural.timers')
MastGlobals.import_python_module('sbs_utils.procedural.grid')
MastGlobals.import_python_module('sbs_utils.procedural.internal_damage')
MastGlobals.import_python_module('sbs_utils.procedural.space_objects')
MastGlobals.import_python_module('sbs_utils.procedural.roles')
MastGlobals.import_python_module('sbs_utils.procedural.inventory')
MastGlobals.import_python_module('sbs_utils.procedural.links')
MastGlobals.import_python_module('sbs_utils.procedural.gui')
MastGlobals.import_python_module('sbs_utils.procedural.comms')
MastGlobals.import_python_module('sbs_utils.procedural.science')
MastGlobals.import_python_module('sbs_utils.procedural.cosmos')
MastGlobals.import_python_module('sbs_utils.procedural.routes')
MastGlobals.import_python_module('sbs_utils.procedural.execution')
MastGlobals.import_python_module('sbs_utils.procedural.behavior')
MastGlobals.import_python_module('sbs_utils.procedural.signal')
MastGlobals.import_python_module('sbs_utils.procedural.maps')
MastGlobals.import_python_module('sbs_utils.procedural.mission')
MastGlobals.import_python_module('sbs_utils.procedural.media')
MastGlobals.import_python_module('sbs_utils.procedural.objective')
MastGlobals.import_python_module('sbs_utils.procedural.upgrades')
MastGlobals.import_python_module('sbs_utils.procedural.docking')
MastGlobals.import_python_module('sbs_utils.procedural.extra_scan_sources')
MastGlobals.import_python_module('sbs_utils.cards.card')
MastGlobals.import_python_module('sbs_utils.faces')
MastGlobals.import_python_module('sbs_utils.fs')
MastGlobals.import_python_module('sbs_utils.vec')
#
# These are exposed with a prepended module name
#
MastGlobals.import_python_module('sbs_utils.scatter', 'scatter')
MastGlobals.import_python_module('sbs_utils.names', 'names')
MastGlobals.import_python_module('sbs_utils.procedural.ship_data', 'ship_data')
MastGlobals.import_python_module('sbs', 'sbs')

#
# These are needed so the import later works, domn't remove
#
from sbs_utils.pages.widgets.listbox import Listbox
from sbs_utils.pages.widgets.layout_listbox import layout_list_box_control
from sbs_utils.pages.widgets.shippicker import ShipPicker

######################
## Mast extensions
MastGlobals.import_python_module('sbs_utils.pages.widgets.shippicker')
MastGlobals.import_python_module('sbs_utils.pages.widgets.listbox')
MastGlobals.import_python_module('sbs_utils.pages.widgets.layout_listbox')
