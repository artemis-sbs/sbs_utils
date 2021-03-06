from sbs_utils.handlerhooks import *
import unittest
import sbs
from sbs_utils.tickdispatcher import TickDispatcher
from sbs_utils.playership import PlayerShip
import sbs_utils.faces as faces
from sbs_utils.consoledispatcher import MCommunications
from sbs_utils.spaceobject import SpaceObject, MSpawnActive
import sbs_utils.layout as layout
from sbs_utils.gui import Page, Gui
from sbs_utils.pages.avatar import AvatarEditor
from sbs_utils.pages.shippicker import ShipPicker



class GuiPage(Page):
    count = 0
    def __init__(self) -> None:
        self.gui_state = 'options'
        self.pageid = GuiPage.count 
        GuiPage.count += 1

    def present(self, sim, CID):
        sbs.send_gui_clear(CID)
        sbs.send_gui_text(
                    CID, f"Page: {self.pageid}", "text", 25, 30, 99, 90)
        w = layout.wrap(99,99, 19, 4,col=1, v_dir=-1, h_dir=-1)
        
        sbs.send_gui_button(CID, "Back", "back", *next(w))
        sbs.send_gui_button(CID, "Another", "again", *next(w))
        

    def on_message(self, sim, message_tag, clientID, _):
        if message_tag == 'back':
            Gui.pop(sim,clientID)
        if message_tag == 'again':
            Gui.push(sim,clientID, GuiPage())



############################
# Test for sbs_utils
class GuiMain(Page):
    def __init__(self) -> None:
        self.gui_state = 'options'

    def present(self, sim, CID):
        sbs.send_gui_clear(CID)
        sbs.send_gui_text(
            CID, "Mission: SBS_Utils unit test.^^This is a unit test for the SBS_Utils library", "text", 25, 30, 99, 90)


        w = layout.wrap(99,99, 19, 4,col=1, v_dir=-1, h_dir=-1)
        
        sbs.send_gui_button(CID, "Start Mission", "start", *next(w))
        sbs.send_gui_button(CID, "smoke test", "smoke", *next(w))
        sbs.send_gui_button(CID, "Vec3 tests", "vec_unit", *next(w))
        sbs.send_gui_button(CID, "face test", "face", *next(w))
        sbs.send_gui_button(CID, "face gen", "face_gen", *next(w))
        sbs.send_gui_button(CID, "Gui Pages", "again", *next(w))
        sbs.send_gui_button(CID, "Avatar Editor", "avatar", *next(w))
        sbs.send_gui_button(CID, "Ship Picker", "ship", *next(w))

    def on_message(self, sim, message_tag, clientID, _):
        match message_tag:
            case 'again':
                # reset state here?
                Gui.push(sim,clientID, GuiPage())

            case 'avatar':
                # reset state here?
                Gui.push(sim,clientID, AvatarEditor())

            case 'ship':
                # reset state here?
                Gui.push(sim,clientID, ShipPicker())

            case "continue":
                self.gui_state = "blank"

            case "smoke":
                self.gui_state = "blank"
                unittest.main(module='tests.test_example', exit=False)
            
            case "vec_unit":
                self.gui_state = "blank"
                unittest.main(module='tests.test_vec', exit=False)

            case "face":
                sbs.create_new_sim()
                sbs.resume_sim()
                Mission.face_test(sim)

            case "face_gen":
                sbs.create_new_sim()
                sbs.resume_sim()
                Mission.face_gen(sim)

            case "start":
                sbs.create_new_sim()
                sbs.resume_sim()
                Mission.start(sim)




class Mission:
    many_count = 0

    def once(sim,t):
        print("timer once")
        Mission.once_ex = True

    def many(sim,t):
        Mission.many_count += 1
        print(f"timer many {Mission.many_count}")

    def test(sim,t):
        if Mission.once_ex and Mission.many_count == 4:
            print("timer test passed")
        else:
            print("timer test failed")

    def start(sim):
        TickDispatcher.do_once(sim, Mission.once, 5)
        TickDispatcher.do_interval(sim, Mission.many, 5, 4)
        TickDispatcher.do_once(sim, Mission.test, 30)

    def face_test(sim):
        t = TickDispatcher.do_interval(sim, Mission.new_face,0)
        t.player = PlayerShip()
        t.player.spawn(sim, 0,0,0, "Artemis", "tsn", "Battle Cruiser")
        
        t.race = 0

    def face_gen(sim):
        PlayerShip().spawn(sim, 0,0,0, "Artemis", "tsn", "Battle Cruiser")
        Spacedock().spawn(sim, 500,0,500,"tsn")
    

    def new_face(sim, t):
        player_id = t.player.id

        face = ""
        race = ""
        match t.race:
            case 0:
                face = faces.random_skaraan()
                race = "Skaraan"
            case 1:
                face = faces.random_torgoth()
                race = "Torgath"

            case 2:
                face = faces.random_arvonian()
                race = "Arvovian"

            case 3:
                face = faces.random_kralien()
                race = "Kralien"

            case 4:
                face = faces.random_zimni()
                race = "Zimni"

            case 5:
                face = faces.random_terran()
                race = "Terran"

            case 6:
                face = faces.random_terran_male()
                race = "Terran Male"

            case 7:
                face = faces.random_terran_female()
                race = "Terran Female"

            case 8:
                face = faces.random_terran_fluid()
                race = "Terran Fluid"
        
        sbs.send_comms_message_to_player_ship( 0, player_id, "green", face,  "Face Test", f"{race} {face}", "face")
        t.race += 1
        if t.race >= 9:
            t.race = 0

        

        
  
        



class Spacedock(SpaceObject, MSpawnActive, MCommunications):
    ds_id = 0

    def __init__(self):
        super().__init__()

        Spacedock.ds_id += 1
        self.ds_id = Spacedock.ds_id
        self.comms_id =  f"DS {self.ds_id}"
    
    def spawn(self, sim, x,y,z, side):
        super().spawn(sim,x,y,z,self.comms_id, side, "Starbase", "behav_station",)
        self.enable_comms()
    
    

    def comms_selected(self, sim, player_id):
        # if Empty it is waiting for what to harvest
        sbs.send_comms_selection_info(player_id, self.face_desc, "green", self.comms_id)

        sbs.send_comms_button_info(player_id, "blue", "Copy to clipboard", "copy")
        sbs.send_comms_button_info(player_id, "blue", "TSN Male", "t:m")
        sbs.send_comms_button_info(player_id, "blue", "TSN Female", "t:f")
        sbs.send_comms_button_info(player_id, "blue", "TSN Fluid", "t:fl")
        sbs.send_comms_button_info(player_id, "blue", "Civilian Male", "c:m")
        sbs.send_comms_button_info(player_id, "blue", "Civilian Female", "c:f")
        sbs.send_comms_button_info(player_id, "blue", "Civilian Fluid", "c:fl")
        sbs.send_comms_button_info(player_id, "blue", "Arvonian", "arv")
        sbs.send_comms_button_info(player_id, "blue", "kralien", "kra")
        sbs.send_comms_button_info(player_id, "blue", "Skaraan", "ska")
        sbs.send_comms_button_info(player_id, "blue", "Torgoth", "tor")
        sbs.send_comms_button_info(player_id, "blue", "Zimni", "zim")
        
    def to_clipboard(self):
        import subprocess
    
        cmd=f'echo {self.face_desc}|clip'
        return subprocess.check_call(cmd, shell=True)

    def comms_message(self, sim, message, player_id):
        
        match message:
            case "copy":
                self.to_clipboard()

            case "t:m":
                self.face_desc = faces.random_terran_male(False)
            case "t:f":
                self.face_desc = faces.random_terran_female(False)
            case "t:fl":
                self.face_desc = faces.random_terran_fluid(False)
            case "c:m":
                self.face_desc = faces.random_terran_male(True)
            case "c:f":
                self.face_desc = faces.random_terran_female(True)
            case "c:fl":
                self.face_desc = faces.random_terran_fluid(True)
            case "arv":
                self.face_desc = faces.random_arvonian()
            case "kra":
                self.face_desc = faces.random_kralien()
            case "ska":
                self.face_desc = faces.random_skaraan()
            case "tor":
                self.face_desc = faces.random_torgoth()
            case "zim":
                self.face_desc = faces.random_zimni()


        self.comms_selected(sim, player_id)
        #sbs.send_comms_selection_info(player_id, self.face_desc, "green", self.comms_id)
        sbs.send_comms_message_to_player_ship(player_id, self.id, "green", self.face_desc,  "Face Gen", self.face_desc, "face")


# Present the main GUI
# Gui.push(None,0, GuiMain())

Gui.server_start_page_class(GuiMain)
Gui.client_start_page_class(GuiMain)





