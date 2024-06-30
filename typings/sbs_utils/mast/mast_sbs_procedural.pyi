from sbs_utils.helpers import FrameContext
from sbs_utils.gui import Gui
from sbs_utils.lifetimedispatcher import LifetimeDispatcher
from sbs_utils.pages.widgets.listbox import Listbox
from sbs_utils.mast.mast import Mast
from sbs_utils.mast.mastscheduler import MastAsyncTask
from sbs_utils.mast.mastscheduler import MastScheduler
from sbs_utils.mast.mastobjects import MastSpaceObject
from sbs_utils.pages.widgets.shippicker import ShipPicker
def func(*argv):
    """assign_client_to_alt_ship(clientComputerID: int, controlledShipID: int) -> None
    
    Tells a client computer that the 2d radar should focus on controlledShipID, instead of its assigned ship.  Turn this code off by providing zero as the second argument."""
def handle_purge_tasks (so):
    """This will clear out all tasks related to the destroyed item"""
def layout_list_box_control (items, template_func=None, title_template=None, section_style=None, title_section_style=None, select=False, multi=False, carousel=False):
    ...
def mast_assert (cond):
    ...
def mast_format_string (s):
    ...
