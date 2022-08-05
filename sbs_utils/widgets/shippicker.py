from ..gui import Widget
from .. import layout as layout
import sbs
from .. import fs

def filter_ship(ship):
    if "hullpoints" in ship:
        return True
    else:
        return False

class ShipPicker(Widget):
    """ A widget to select a ship"""

    def __init__(self, left, top, tag_prefix) -> None:
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
        self.cur = 0
        self.test = fs.get_artemis_data_dir()

        data = fs.get_ship_data()
        #data = None
        
        self.ships = None
        if data is None:
            self.ships = None
        else:
            self.test = data
            self.ships = [ a for a in filter(filter_ship, data["#ship-list"] )]

            if self.ships is None:
                self.ships = None


    def present(self, sim, CID):
        """ present

        builds/manages the content of the widget
     
        :param sim: simulation
        :type sim: Artemis Cosmos simulation
        :param CID: Client ID
        :type CID: int
        """
        if self.gui_state == "presenting":
            return
        if self.ships is None:
            sbs.send_gui_text(
                    CID, f"Error {self.test}", f"{self.tag_prefix}error", self.left, self.top, self.left+40, self.top+5)
            return

        ship = self.ships[self.cur]

        sbs.send_gui_text(
                    CID, f"Ship: {ship['name']}", f"{self.tag_prefix}title", self.left, self.top, self.left+40, self.top+5)
        l1 = layout.wrap(self.left, self.top+40, 19, 4,col=3)
        
        sbs.send_gui_button(CID, "prev", f"{self.tag_prefix}prev", *next(l1))
        sbs.send_gui_button(CID, "next", f"{self.tag_prefix}next", *next(l1))
        sbs.send_gui_3dship(CID, ship['name'], f"{self.tag_prefix}ship", 
            self.left+5, self.top+5,
            self.left+33, self.top+33 )
     
        self.gui_state = "presenting"


    def on_message(self, sim, message_tag, clientID, _):
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
                    self.present(sim, clientID)
                    return True
                
            case "next":
                if self.cur < len(self.ships):
                    self.cur += 1
                    self.gui_state = "redraw"
                    if self.cur >= len(self.ships):
                        self.cur = 0
                    self.present(sim, clientID)
                    return True
        return False
                

    def get_selected(self):
        """ get selected

        :return: None or string of ship selected
        :rtype: None or string of ship selected
        """

        ship = self.ships[self.cur]
        if "name" in ship:
            return ship["name"]
        return None
