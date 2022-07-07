from sbs_utils.handlerhooks import *
import unittest
import sbs
from sbs_utils.tickdispatcher import TickDispatcher
from sbs_utils.playership import PlayerShip
import sbs_utils.faces as faces




############################
# Test for sbs_utils
class GuiMain:
    def __init__(self) -> None:
        self.gui_state = 'options'

    def present(self, sim):
        match self.gui_state:
            case  "sim_on":
                self.gui_state = "blank"
                sbs.send_gui_clear(0)

            case  "options":
                sbs.send_gui_clear(0)
                # Setting this to a state we don't process
                # keeps the existing GUI displayed
                self.gui_state = "presenting"
                sbs.send_gui_text(
                    0, "Mission: SBS_Utils unit test.^^This is a unit test for the SBS_Utils library", "text", 25, 30, 99, 90)
                sbs.send_gui_button(0, "smoke test", "smoke", 80, 80, 99, 85)
                sbs.send_gui_button(0, "face test", "face", 80, 85, 99, 90)
                sbs.send_gui_button(0, "Vec3 tests", "vec_unit", 80, 90, 99, 94)
                sbs.send_gui_button(0, "Start Mission", "start", 80, 95, 99, 99)

    def on_message(self, sim, message_tag, clientID):
        match message_tag:
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

            case "start":
                sbs.create_new_sim()
                sbs.resume_sim()
                Mission.start(sim)




class Mission:
    main = GuiMain()
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

        

        
  
        

def HandlePresentGUI(sim):
    Mission.main.present(sim)

def HandlePresentGUIMessage(sim, message_tag, clientID):
    Mission.main.on_message(sim, message_tag, clientID)



