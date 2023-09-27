from ..gui import Widget
from .. import layout as layout
import sbs
from .. import fs


class ShipPicker(Widget):
    """ A widget to select a ship"""

    def __init__(self, left, top, tag_prefix, title_prefix="Ship:", cur=None, ship_keys=None, roles=None, sides=None) -> None:
        """ Ship Picker widget

        A widget the combines a title, ship viewer, next and previous buttons for selecting ships
     
        :param left: left coordinate
        :type left: float
        :param top: top coordinate
        :type top: float
        :param tag_prefix: Prefix to use in message tags to mak this component unique
        :type tag_prefix: str
        """
        super().__init__(left,top,tag_prefix)
        self.gui_state = "blank"
        self.title_prefix = title_prefix
        self.cur = 0
        self.test = fs.get_artemis_data_dir()
        self.bottom = top+40
        self.right = left+33
        
        data = fs.get_ship_data()
        #data = None
        if roles is not None:
            roles = roles.strip().lower()
            roles=set(roles.split(","))

        if sides is not None:
            sides = sides.strip().lower()
            sides=set(sides.split(","))
        
        self.ships = None
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


    def present(self, event):
        """ present

        builds/manages the content of the widget
     
        :param sim: simulation
        :type sim: Artemis Cosmos simulation
        :param CID: Client ID
        :type CID: int
        """
        CID = event.client_id

        if self.gui_state == "presenting":
            return
        if self.ships is None:
            sbs.send_gui_text(
                    CID,  f"{self.tag_prefix}error", f"text:Error {self.test}", self.left, self.top, self.right, self.top+5)
            return

        ship = self.ships[self.cur]

        sbs.send_gui_text(
                    CID, f"{self.tag_prefix}title", f"text: {self.title_prefix} {ship['name']}",  self.left, self.top, self.right, self.top+5)
        #l1 = layout.wrap(self.left, self.bottom, , 4,col=2)
        half = (self.right-self.left)/2
        
        sbs.send_gui_button(CID,f"{self.tag_prefix}prev", "text:prev", self.left, self.bottom-5, self.left+half, self.bottom)
        sbs.send_gui_button(CID, f"{self.tag_prefix}next", "text:next", self.right-half, self.bottom-5, self.right, self.bottom)
        sbs.send_gui_3dship(CID,  f"{self.tag_prefix}ship", f"hull_tag:{ship['key']}",
            self.left+5, self.top+5,
            self.right-5, self.bottom-5 )
     
        self.gui_state = "presenting"


    def on_message(self, event):
        """ on_message

        handles messages this will look for components owned by this control and react accordingly
        components owned will have the tag_prefix
     
        :param sim: simulation
        :type sim: Artemis Cosmos simulation
        :param message_tag: Tag of the component
        :type message_tag: str
        :param CID: Client ID
        :type CID: int
        :param data: unused no component use data
        :type data: any
        """
        message_tag = event.sub_tag
        client_id = event.client_id

        if not message_tag.startswith(self.tag_prefix):
            return False

        message_tag = message_tag[len(self.tag_prefix):] 
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

    def get_selected(self):
        """ get selected

        :return: None or string of ship selected
        :rtype: None or string of ship selected
        """

        ship = self.ships[self.cur]
        if "key" in ship:
            return ship["key"]
        return None
    def get_selected_name(self):
        """ get selected

        :return: None or string of ship selected
        :rtype: None or string of ship selected
        """
        ship = self.ships[self.cur]
        if "name" in ship:
            return ship["name"]
        return None


def ship_picker_control(title_prefix="Ship:", cur=None, ship_keys=None, roles=None, sides=None):
    return ShipPicker(0, 0, "mast", title_prefix, cur, ship_keys, roles, sides)
