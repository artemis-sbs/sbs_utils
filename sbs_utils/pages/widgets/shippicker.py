
from ..layout import layout as layout
from ...helpers import FrameContext
from ... import fs
from ...procedural import ship_data
from .control import Control


class ShipPicker(Control):
    """ A widget to select a ship"""

    def __init__(self, left, top, tag_prefix, title_prefix="Ship:", cur=None, ship_keys=None, roles=None, sides=None, show_desc=True) -> None:
        """ Ship Picker widget

        A widget the combines a title, ship viewer, next and previous buttons for selecting ships
     
        Args:
            left (float): left coordinate
            top (float): top coordinate
            tag_prefix (str): Prefix to use in message tags to make this component unique
            title_prefix (str): Prefix to use in the title. Optional, default 'Ship'.
            cur (int): The current selected index. Optional, default is None.
            ship_keys (list[str]): The list of ship keys with which the ShipPicker is populated. Optional, default is None.
            roles (list[str]): The roles by which ship keys are filtered. Optional, default is None.
            sides (list[str]): The sides by which ship keys are filtered. Optional, default is None.
            show_desc (bool): Should the ShipPicker include the description of the ship? Optional, default is True.
        """
        super().__init__(left,top,33,44)

        self.gui_state = "blank"
        self.tag = tag_prefix
        self.title_prefix = title_prefix
        self.cur = 0
        self.test = fs.get_artemis_data_dir()
        self.bottom = top+50
        self.right = left+33
        self._read_only = False
        
        data = ship_data.get_ship_data()
        #data = None
        if roles is not None:
            roles = roles.strip().lower()
            roles=set(roles.split(","))

        if sides is not None:
            sides = sides.strip().lower()
            sides=set(sides.split(","))
        
        self.ships = None
        self.show_desc = show_desc
        if data is None:
            self.ships = None
        else:
            self.test = data
            self.ships = []
            i = 0
            for a in data["#ship-list"]:
                if ship_keys is not None:
                    if a["key"] not in ship_keys:
                        continue
                if sides:
                    side = a.get("side")
                    if side is not None and side.lower() not in sides:
                        continue
                #
                # Check to see if the role filter is present
                #
                if roles is not None:
                    ship_roles = a.get("roles")
                    if ship_roles is not None:
                        ship_roles = ship_roles.lower()
                        ship_roles = ship_roles.split(",")
                    else:
                        ship_roles = []
                    # use side as a role
                    side = a.get("side")
                    if side:
                        ship_roles.append(side.strip().lower())
                    ship_roles=set(ship_roles)
                    common_roles = roles & ship_roles
                    if len(common_roles)==0:
                        continue

                self.ships.append(a)
                if cur and a == cur:
                    self.cur = i
                elif cur and a["key"] == cur:
                    self.cur = i
                i+=1

            if self.ships is None:
                self.ships = None

    @property
    def read_only(self):
        return self._read_only
    
    @read_only.setter
    def read_only(self, value):
        self._read_only = value
        self.gui_state = "notpresenting"
        self.mark_visual_dirty()


    def _present(self, event):
        """ present

        builds/manages the content of the widget
     
        Args:
            event (event): The event that triggered the gui to update.
        """
        CID = event.client_id
        SBS = FrameContext.context.sbs

        the_bounds = layout.Bounds(0,0,100,100)

        if self.gui_state == "presenting":
            return
        self.gui_state == "presenting"
        if self.ships is None:
            SBS.send_gui_text(
                    CID,  self.local_region_tag, f"{self.tag}error", f"$text:Error {self.test}",the_bounds.left, the_bounds.top, the_bounds.right, the_bounds.top+5)
            return

        ship = self.ships[self.cur]
        top = the_bounds.top

        SBS.send_gui_text(
                    CID, self.local_region_tag, f"{self.tag}title", f"$text: {self.title_prefix} {ship['side']} {ship['name']}",  the_bounds.left, top, the_bounds.right, top+5)
        top += 5
        if self.show_desc:
            desc = ship.get('long_desc',None)
            if desc is not None:
                SBS.send_gui_text(
                        CID, self.local_region_tag, f"{self.tag}desc", f"$text: {desc}",  the_bounds.left, top, the_bounds.right, top+15)
            # Keep spacing?
            top += 15
        
        #l1 = layout.wrap(self.left, self.bottom, , 4,col=2)
        half = (the_bounds.right-the_bounds.left)/2
        
        if not self._read_only:
            SBS.send_gui_button(CID,self.local_region_tag, f"{self.tag}prev", "$text:prev", the_bounds.left, the_bounds.bottom-5, the_bounds.left+half, the_bounds.bottom)
            SBS.send_gui_button(CID,self.local_region_tag, f"{self.tag}next", "$text:next", the_bounds.right-half, the_bounds.bottom-5, the_bounds.right, the_bounds.bottom)
        SBS.send_gui_3dship(CID,self.local_region_tag, f"{self.tag}ship", f"hull_tag:{ship['key']};",
            the_bounds.left, top,
            the_bounds.right, the_bounds.bottom-5 )
     
        self.gui_state = "notpresenting"


    def on_message(self, event):
        """ on_message

        handles messages this will look for components owned by this control and react accordingly
        components owned will have the tag_prefix

        Args:
            event (event): The event that triggered the update
        """
        message_tag = event.sub_tag
        client_id = event.client_id

        if not message_tag.startswith(self.tag):
            return False

        message_tag = message_tag[len(self.tag):] 
        match message_tag:
            case "prev":
                if self.cur >= 0:
                    self.cur -= 1
                    self.gui_state = "redraw"
                    if self.cur <0:
                        self.cur = len(self.ships)-1
                    self.present(event)
                    return True
                
            case "next":
                if self.cur < len(self.ships):
                    self.cur += 1
                    self.gui_state = "redraw"
                    if self.cur >= len(self.ships):
                        self.cur = 0
                    self.present(event)
                    return True
        return False
                
    def get_value(self):
        return self.get_selected()
    
    def set_value(self, value):
        self.set_selected(value)

    def get_selected(self):
        """ Get the key of the selected ship.

        Returns:
            str|None: The selected ship key.
        """

        ship = self.ships[self.cur]
        if "key" in ship:
            return ship["key"]
        return None
    def get_selected_name(self):
        """ Get the name of the selected ship.

        Returns:
            str|None: The name of the selected ship as defined in the shipData.
        """
        ship = self.ships[self.cur]
        if "name" in ship:
            return ship["name"]
        return None
    def set_selected(self, key):
        """ Set the selected ship by key as defined in the shipData.
        Args:
            key (str): The key of the ship which should be selected.
        """
        cur = 0
        for k in self.ships:
            ship = self.ships[cur]
            if "key" in ship and ship["key"] == key:
                break
            cur += 1
        if cur != self.cur:
            self.gui_state = "redraw"
        if cur < len(self.ships):
            self.cur = cur
        

    
    def update(self, props):
        self.set_selected(props)

def ship_picker_control(title_prefix="Ship:", cur=None, ship_keys=None, roles=None, sides=None, show_desc=True):
    """
    Build a ShipPicker widget, which allows players to choose what ship they wish to crew.
    Args:
        tag_prefix (str): Prefix to use in message tags to make this component unique
        title_prefix (str): Prefix to use in the title. Optional, default 'Ship'.
        cur (int): The current selected index. Optional, default is None.
        ship_keys (list[str]): The list of ship keys with which the ShipPicker is populated. Optional, default is None.
        roles (list[str]): The roles by which ship keys are filtered. Optional, default is None.
        sides (list[str]): The sides by which ship keys are filtered. Optional, default is None.
        show_desc (bool): Should the ShipPicker include the description of the ship? Optional, default is True.
    """
    return ShipPicker(0, 0, "mast", title_prefix, cur, ship_keys, roles, sides, show_desc)
