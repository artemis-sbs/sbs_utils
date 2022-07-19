from ..gui import Page, Gui
from .. import layout as layout
import sbs
from .. import faces as faces


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
        self.face = faces.Characters.URSULA

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

            for widget in widgets:
                label = widget["label"]
                sbs.send_gui_text(0, label, f"lab:{label}", *next(l2))
                sbs.send_gui_slider(CID, label,  widget["min"],widget["max"],0, *next(l2))

        self.gui_state = "presenting"


    def on_message(self, sim, message_tag, clientID):
        if message_tag == 'back':
            Gui.pop(sim,clientID)
        match message_tag:
            case "arv":
                # self.face = faces.arvonian(0,1,2,3,4)
                self.face = faces.random_arvonian()
                self.gui_state = message_tag
                self.present(sim, clientID)
            case "kra":
                # self.face = faces.arvonian(0,1,2,3,4)
                self.face = faces.random_kralien()
                self.gui_state = message_tag
                self.present(sim, clientID)
            case "ska":
                # self.face = faces.arvonian(0,1,2,3,4)
                self.face = faces.random_skaraan()
                self.gui_state = message_tag
                self.present(sim, clientID)
            case "tor":
                # self.face = faces.arvonian(0,1,2,3,4)
                self.face = faces.random_torgoth()
                self.gui_state = message_tag
                self.present(sim, clientID)
            case "xim":
                # self.face = faces.arvonian(0,1,2,3,4)
                self.face = faces.random_ximni()
                self.gui_state = message_tag
                self.present(sim, clientID)
            case "ter":
                # self.face = faces.arvonian(0,1,2,3,4)
                self.face = faces.random_terran()
                self.gui_state = message_tag
                self.present(sim, clientID)
            
            # catch all for switching race
            case _:
                self.gui_state = message_tag
                self.present(sim, clientID)
