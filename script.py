from sbs_utils.handlerhooks import *
import unittest
import sbs
from sbs_utils.tickdispatcher import TickDispatcher
from sbs_utils.objects import PlayerShip, Npc
import sbs_utils.faces as faces
from sbs_utils.consoledispatcher import MCommunications
from sbs_utils.spaceobject import SpaceObject, MSpawnActive
import sbs_utils.layout as layout
from sbs_utils.gui import Page, Gui
from sbs_utils.pages.avatar import AvatarEditor
from sbs_utils.pages.shippicker import ShipPicker
import sbs_utils
from sbs_utils.quest import Quest
from sbs_utils.questrunner import SbsQuestRunner


class QuestShip(Npc):
    def spawn(self, sim, x, y, z, name, side, art_id):
        super().spawn(sim, x, y, z, name, side, art_id, "behav_npcship")

    def compile(self, sim, ins, script):
        self.quest = Quest()
        self.quest.compile(script)
        inputs = {
            "self": self
        } | ins
        
        self.runner = SbsQuestRunner(
            self.quest, inputs)
        
        TickDispatcher.do_interval(sim, self.tick_quest, 0)

    def start(self, sim, label="main"):
        self.runner.start(sim, label)

    def tick_quest(self, sim, t):
        self.runner.tick(sim)




class GuiPage(Page):
    count = 0
    def __init__(self) -> None:
        self.gui_state = 'options'
        self.pageid = GuiPage.count 
        GuiPage.count += 1

    def present(self, sim, event):
        sbs.send_gui_clear(event.client_id)
        sbs.send_gui_text(
                    event.client_id, f"Page: {self.pageid}", "text", 25, 30, 99, 90)
        w = layout.wrap(99,99, 19, 4,col=1, v_dir=-1, h_dir=-1)
        
        sbs.send_gui_button(event.client_id, "Back", "back", *next(w))
        sbs.send_gui_button(event.client_id, "Another", "again", *next(w))
        

    def on_message(self, sim, event):
        if event.sub_tag == 'back':
            Gui.pop(sim,event.client_id)
        if event.sub_tag == 'again':
            Gui.push(sim,event.client_id, GuiPage())



############################
# Test for sbs_utils
class GuiMain(Page):
    def __init__(self) -> None:
        self.gui_state = 'options'

    def present(self, sim, event):
        sbs.send_gui_clear(event.client_id)
        sbs.send_gui_text(
            event.client_id, "Mission: SBS_Utils unit test.^^This is a unit test for the SBS_Utils library", "text", 25, 30, 99, 90)


        w = layout.wrap(99,99, 19, 4,col=1, v_dir=-1, h_dir=-1)
        

        sbs.send_gui_button(event.client_id, "Start Mission", "start", *next(w))
        sbs.send_gui_button(event.client_id, "smoke test", "smoke", *next(w))
        sbs.send_gui_button(event.client_id, "Vec3 tests", "vec_unit", *next(w))
        sbs.send_gui_button(event.client_id, "face test", "face", *next(w))
        sbs.send_gui_button(event.client_id, "face gen", "face_gen", *next(w))
        sbs.send_gui_button(event.client_id, "Gui Pages", "again", *next(w))
        sbs.send_gui_button(event.client_id, "Avatar Editor", "avatar", *next(w))
        sbs.send_gui_button(event.client_id, "Ship Picker", "ship", *next(w))
        sbs.send_gui_button(event.client_id, "StubGen", "stub", *next(w))
        sbs.send_gui_button(event.client_id, "Quest", "quest", *next(w))

    def on_message(self, sim, event):
        match event.sub_tag:
            case 'again':
                # reset state here?
                Gui.push(sim,event.client_id, GuiPage())

            case 'avatar':
                # reset state here?
                Gui.push(sim,event.client_id, AvatarEditor())

            case 'stub':
                self.stub_gen()

            case 'ship':
                # reset state here?
                Gui.push(sim,event.client_id, ShipPicker())

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

            case "quest":
                sbs.create_new_sim()
                sbs.resume_sim()
                Mission.quest(sim)


    def stub_gen(self):
        import stub
        gen = stub.GenStubs()
        gen.stub_module("sbs")
        gen.stub_module("sbs_utils")



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
                face = faces.random_ximni()
                race = "Ximni"

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

    def quest(sim):

        player = PlayerShip()
        player.spawn(sim, 0,0,-1400, "Artemis", "tsn", "Battle Cruiser")
        q = QuestShip()
        q.spawn(sim, 0,0,0, "Quest", "tsn", "Battle Cruiser" )
        ds = Spacedock()
        ds.spawn(sim, 500,0,2500,"tsn")
        inputs = {
            "player": player,
            "station": ds,
            "ship": q
        }

        q.compile(sim, inputs, 
"""
comms player self
    button "Say Hello" -> Hello
    button "Say Hi" -> Hi


== skip ==
tell player self "Come to pick the princess"
near player self 300
tell player ship "You have the princess goto ds1"
near player station 700
tell player station "the princess is on ds1"

== Hello ==
tell player self "HELLO"
comms player self
    button "Say Blue" -> Blue
    button "Say Yellow" -> Yellow
    button "Say Cyan" -> Cyan


== Hi ==
tell player self "Hi"
delay 10s
-> main

== Chat ==
tell player self "Blah, Blah"
delay 10s
-> Chat

== Blue ==
tell player self "Blue"
delay 10s
-> main

== Yellow ==
tell player self "Yellow"
delay 10s
-> main

== Cyan ==
tell player self "Cyan"
comms player self timeout 5s -> TooSlow
    button "Say main" -> main

== TooSlow ==
tell player self "Woh too slow"
delay 10s
-> main

""")
        q.start(sim)
        # Demo threads
        q.start(sim,"Chat")


        
  
        



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
    
    

    def comms_selected(self, sim, player_id, _):
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
        sbs.send_comms_button_info(player_id, "blue", "Ximni", "xim")
        
    def to_clipboard(self):
        import subprocess
    
        cmd=f'echo {self.face_desc}|clip'
        return subprocess.check_call(cmd, shell=True)

    def comms_message(self, sim, message, player_id, e):
        
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
            case "xim":
                self.face_desc = faces.random_ximni()


        self.comms_selected(sim, player_id, e)
        #sbs.send_comms_selection_info(player_id, self.face_desc, "green", self.comms_id)
        sbs.send_comms_message_to_player_ship(player_id, self.id, "green", self.face_desc,  "Face Gen", self.face_desc, "face")


# Present the main GUI
# Gui.push(None,0, GuiMain())

Gui.server_start_page_class(GuiMain)
Gui.client_start_page_class(GuiMain)




