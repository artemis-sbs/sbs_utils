from email import message
from ..gui import Page, Gui
from .. import layout as layout
import sbs
from .. import faces as faces

import ctypes
MessageBox = ctypes.windll.user32.MessageBoxW



class AvatarEditor(Page):
    widgets = {
        "arv": [
            {"label": "Eyes", "min": 0, "max":4}, 
            {"label": "Mouth", "min": 0, "max":4}, 
            {"label": "Crown", "min": 0, "max":4, "optional": True}, 
            {"label": "Collar", "min": 0, "max":4, "optional": True}], 
        "kra": [
            {"label": "Eyes", "min": 0, "max":4}, 
            {"label": "Mouth", "min": 0, "max":4}, 
            {"label": "Scalp", "min": 0, "max":4, "optional": True}, 
            {"label": "Extra", "min": 0, "max":4, "optional": True}
            ], 

        "ska": [
            {"label": "Eyes", "min": 0, "max":4}, 
            {"label": "Mouth", "min": 0, "max":4}, 
            {"label": "Horn", "min": 0, "max":4, "optional": True}, 
            {"label": "Hat", "min": 0, "max":4, "optional": True}
            ], 

        "tor": [
            {"label": "Eyes", "min": 0, "max":4}, 
            {"label": "Mouth", "min": 0, "max":4}, 
            {"label": "Hair", "min": 0, "max":4, "optional": True}, 
            {"label": "Extra", "min": 0, "max":4, "optional": True},
            {"label": "Hat", "min": 0, "max":4, "optional": True}
            ], 

        
        "xim": [
            {"label": "Eyes", "min": 0, "max":4}, 
            {"label": "Mouth", "min": 0, "max":4}, 
            {"label": "Horns", "min": 0, "max":4, "optional": True}, 
            {"label": "Mask", "min": 0, "max":4, "optional": True},
            {"label": "Collar", "min": 0, "max":4, "optional": True}
            ], 

        "ter": [
            {"label": "Body", "min": 0, "max":1}, 
            {"label": "Eyes", "min": 0, "max":9}, 
            {"label": "Mouth", "min": 0, "max":9}, 
            {"label": "Hair", "min": 0, "max":4, "optional": True}, 
            {"label": "Long Hair", "min": 0, "max": 7, "optional": True},
            {"label": "Facial Hair", "min": 0, "max":4, "optional": True},
            {"label": "Extra", "min": 0, "max":4, "optional": True},
            {"label": "Uniform", "min": 0, "max":9, "optional": True},
            {"label": "Skin Tone", "min": 0, "max": len(faces.skin_tones)-1},
            {"label": "Hair Tone", "min": 0, "max":len(faces.hair_tones)-1}
            ], 
        


    }

    def __init__(self) -> None:
        self.gui_state = 'arv'
        self.race = "arv"
        self.face = faces.Characters.URSULA
        self.cur = [0,0,0,0,0,0, 0,0,0,0,0,0]

    def present(self, sim, CID):
        if self.gui_state == "presenting":
            return
        sbs.send_gui_clear(CID)
        sbs.send_gui_text(
                    0, f"Avatar Editor", "title", 25, 5, 99, 9)
        sbs.send_gui_face(CID, self.face, "face", 35, 0, 65, 1)
        l1 = layout.wrap(25, 50, 19, 4,col=3)
        
        sbs.send_gui_button(CID, "Arvonian", "arv", *next(l1))
        sbs.send_gui_button(CID, "Kralien", "kra", *next(l1))
        sbs.send_gui_button(CID, "Skaraan", "ska", *next(l1))
        sbs.send_gui_button(CID, "Terran", "ter", *next(l1))
        sbs.send_gui_button(CID, "Torgoth", "tor", *next(l1))
        sbs.send_gui_button(CID, "Ximni", "xim", *next(l1))

        w = layout.wrap(99, 99, 19, 4,col=1, v_dir=-1, h_dir=-1)
        sbs.send_gui_button(CID, "Back", "back", *next(w))
        
        # Get bottom of the race buttons
        (l,t,r,b) = next(l1)
        widgets = AvatarEditor.widgets.get(self.gui_state)
        if widgets is not None:
            l2 = layout.wrap(25, b, 15, 4,col=4, h_gutter = 1)
            #l3 = layout.wrap(41, b, 10, 4,col=2, h_gutter = 10+10+1)
            v = 0
            for widget in widgets:
                label = widget["label"]
                loc = next(l2)
                
                if "optional" in widget:
                    enable = 1 if widget["optional"] == True else 0
                    #enable = 0
                    sbs.send_gui_checkbox(CID, label, f"op:{v}", enable, *loc)
                    if enable:
                        sbs.send_gui_slider(CID, f"{v}",  widget["min"],widget["max"],self.cur[v], *next(l2))
                    else:
                        next(l2)

                else:
                    sbs.send_gui_text(CID, label, f"lab:{label}", *loc)
                    sbs.send_gui_slider(CID, f"{v}",  widget["min"],widget["max"],self.cur[v], *next(l2))

                
                v+=1

        self.gui_state = "presenting"

    def reset_values(self):
        widgets = AvatarEditor.widgets.get(self.race)
        v = 0
        for w in widgets:
            if "optional" in w and w["optional"] == False:
               self.cur[v] = None
            elif self.cur[v] is None:
                self.cur[v] = 0
            elif self.cur[v] > w["max"]:
                self.cur[v] = w["max"]
            v += 1


    def on_message(self, sim, message_tag, clientID, data):
        v = self.cur
        if message_tag == 'back':
            Gui.pop(sim,clientID)

        if message_tag.startswith("op:"):
            
            try:
                val = int(message_tag[3:])
                widgets = AvatarEditor.widgets.get(self.race)
                if widgets is not None:
                    enable = not widgets[val]["optional"]
                    widgets[val]["optional"] = enable
                    if not enable:
                        self.cur[val] = None
                    else:
                        self.cur[val] = 0
            finally:
                pass
        else:
            try:
                val = int(message_tag)
                self.cur[val] = round(data)
            except:
                self.race = message_tag

        match self.race:
            case "arv":
                self.reset_values()
                self.face = faces.arvonian(0, v[0], v[1], v[2], v[3])
            case "kra":
                self.reset_values()
                self.face = faces.kralien(0, v[0], v[1], v[2], v[3])
            case "ska":
                self.reset_values()
                # self.face = faces.arvonian(0,1,2,3,4)
                self.face = faces.skaraan(0, v[0], v[1], v[2], v[3])
            case "tor":
                # self.face = faces.arvonian(0,1,2,3,4)
                self.reset_values()
                self.face = faces.torgoth(0, v[0], v[1], v[2], v[3],v[4])
            case "xim":
                self.reset_values()
                # self.face = faces.arvonian(0,1,2,3,4)
                self.face = faces.ximni(0, v[1], v[2], v[3],v[4], v[5])
            case "ter":
                self.reset_values()
                self.face = faces.terran(v[0], v[1], v[2], v[3],v[4], v[5], v[6],v[7], v[8], v[9])
            
            # catch all for switching race
            case _:
                pass

        self.gui_state = self.race
        self.present(sim, clientID)
