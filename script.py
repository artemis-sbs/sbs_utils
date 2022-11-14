from sbs_utils.handlerhooks import *
import unittest
import sbs

from sbs_utils.tickdispatcher import TickDispatcher
from sbs_utils.objects import PlayerShip, Npc, Terrain
import sbs_utils.faces as faces
from sbs_utils.consoledispatcher import MCommunications
from sbs_utils.spaceobject import SpaceObject, MSpawnActive
import sbs_utils.layout as layout
from sbs_utils.gui import Page, Gui
from sbs_utils.pages.avatar import AvatarEditor
from sbs_utils.pages.shippicker import ShipPicker
from sbs_utils.pages.start import ClientSelectPage
from sbs_utils.pages.layout import LayoutPage, Layout, Row, Text, Face, Ship
#import sbs_utils
from sbs_utils.mast.mast import Mast
from sbs_utils.mast.mastsbs import MastSbs
from sbs_utils.mast.mastsbsscheduler import MastSbsScheduler

from sbs_utils.mast.maststory import MastStory
from sbs_utils.mast.maststoryscheduler import StoryPage, StoryScheduler
from sbs_utils import fs
import os
from sbs_utils.gridobject import GridObject


Mast.enable_logging()



class MastShip(Npc):
    def spawn(self, sim, x, y, z, name, side, art_id):
        super().spawn(sim, x, y, z, name, side, art_id, "behav_npcship")

    def compile(sim, script):
        MastShip.mast = MastSbs()
        MastShip.mast.compile(script)
        MastShip.runner = MastSbsScheduler(
            MastShip.mast)
        TickDispatcher.do_interval(sim, MastShip.tick_mast, 0)

    def run(self, sim, label="main", inputs=None):
        inputs = {
            "self": self,
            "PlayerShip": PlayerShip,
            "Npc": Npc
        } | inputs
        MastShip.runner.run(sim, label, inputs)

    def tick_mast(sim, t):
        MastShip.runner.sbs_tick_threads(sim)




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


class TestLayoutPage(LayoutPage):
    def __init__(self) -> None:
        super().__init__()
        self.layout.left = 30
        self.layout.top = 20
        self.layout.width = 70
        self.layout.height = 70

        text = " l;k;lk; k;lk ;lk;k;k; jhkj  kjhhkjh kjhh jkh k kjh jh  jljlk j lk j kj lkj kjlk lkjlk jllk  kjkjl  jhjhkh kh k iojiopipi rrrwqrrq"
        self.layout.add(
            Row()
                .add(Face(faces.random_terran(),
                    "tag_two"))
                .add(Text(text,
                    "tag_one"))
        )
        self.layout.add(
            Row()
                #.add(Ship("Battle Cruiser",
                #    "tag_three"))
                .add(Text(text,
                    "tag_four"))
                .add(Face(faces.random_terran(),
                    "tag_five"))
        )
        
        self.layout.calc()



class GuiStory(StoryPage):
    story_file = "tests/mast/story_gui.mast"
    # inputs = {
    #         "PlayerShip": PlayerShip,
    #         "Npc": Npc,
    #         "Terrain": Terrain
    #         }
    
class SiegeStory(StoryPage):
    story_file = "tests/mast/siege.mast"
    # inputs = {
    #         "PlayerShip": PlayerShip,
    #         "Npc": Npc,
    #         "Terrain": Terrain
    #         }

class TttStory(StoryPage):
    story_file = "tests/mast/ttt.mast"
    inputs = None




############################
# Test for sbs_utils
class GuiMain(Page):
    def __init__(self) -> None:
        self.gui_state = 'options'

    def on_pop(self, sim):
        return super().on_pop(sim)

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
        sbs.send_gui_button(event.client_id, "Mast", "mast", *next(w))
        sbs.send_gui_button(event.client_id, "Layout", "layout", *next(w))
        sbs.send_gui_button(event.client_id, "Mast bar", "story", *next(w))
        sbs.send_gui_button(event.client_id, "Mast ttt", "story_ttt", *next(w))
        sbs.send_gui_button(event.client_id, "GridItems", "grid", *next(w))
        sbs.send_gui_button(event.client_id, "Mast Siege", "siege", *next(w))

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

            case "layout":
                Gui.push(sim,event.client_id, TestLayoutPage())

            case "story":
                page = GuiStory()
                #page.run(sim , story_script)        
                Gui.client_start_page_class(GuiStory)        
                Gui.push(sim,event.client_id, page)

            case "siege":
                page = SiegeStory()
                #page.run(sim , story_script)        
                Gui.client_start_page_class(SiegeStory)        
                Gui.push(sim,event.client_id, page)
                
            case "story_ttt":
                page = TttStory()
                #page.run(sim , story_script)                
                Gui.push(sim,event.client_id, page)

            case "face_gen":
                sbs.create_new_sim()
                sbs.resume_sim()
                Mission.face_gen(sim)

            case "start":
                sbs.create_new_sim()
                sbs.resume_sim()
                Mission.start(sim)

            case "grid":
                sbs.create_new_sim()
                sbs.resume_sim()
                Mission.start_grid(sim)

            case "mast":
                sbs.create_new_sim()
                sbs.resume_sim()
                Mission.mast(sim)

            case "target":
                sbs.create_new_sim()
                sbs.resume_sim()
                Mission.target_bug(sim)


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

    def target_bug(sim: sbs.simulation):

        #player = PlayerShip()
        #player.spawn(sim, 0,0,0, "Artemis", "tsn", "Battle Cruiser")
        #bad = Npc()
        #bad.spawn(sim,0,0, 1400, "BadGuy", "baddy", "Battle Cruiser", "behav_npcship")
        #bad.target_closest(sim, "PlayerShip")

        player_id = sim.make_new_player("behav_playership", "Battle Cruiser")
        sbs.assign_player_ship(player_id)
        player = sim.get_space_object(player_id)
        player.side = "TSN";
        blob = player.data_set
        blob.set("name_tag", "Artemis", 0)
        sim.reposition_space_object(player, 0, 0, 10)

        other_id = sim.make_new_active("behav_npcship", "Battle Cruiser")
        other = sim.get_space_object(other_id)
        other.side = "baddy"
        sim.reposition_space_object(other, 0,0,1400)

        blob = other.data_set
        blob.set("target_pos_x", player.pos.x)
        blob.set("target_pos_y", player.pos.y)
        blob.set("target_pos_z", player.pos.z)
        blob.set("target_id", player.unique_ID)

    def start_grid(sim: sbs.simulation):
        Gui.client_start_page_class(ClientSelectPage)
        player = PlayerShip()
        sd_player = player.spawn(sim, 0,0,0, "Artemis", "tsn", "Battle Cruiser")
        go1 = GridObject()
        go1.spawn(sim, sd_player.id, "fred", "fred", 9,4, 3, "blue", "flint")
        go2 = GridObject()
        go2.spawn(sim, sd_player.id, "barney", "fred", 8,4, 3, "green", "rubble")
        go2.update_blob(sim, speed=0.01, icon_scale=1.3)
        go2.target_pos(sim,9,12)
        GridDispatcher.add_object(go2.id, lambda sim, event: print("Barney Arrived"))
        
        

    def mast(sim):

        player = PlayerShip()
        player.spawn(sim, 0,0,0, "Artemis", "tsn", "Battle Cruiser")

        
        ds1 = Spacedock()
        ds1.spawn(sim, 1000,0,2500,"tsn")
        ds2 = Spacedock()
        ds2.spawn(sim, -1000,0,2500,"tsn")
     
        MastShip.compile(sim, 
"""
# Set the comms buttons to start the 'quest'

await self comms player
+ "Start at DS1"
 -> One
+ "Start at DS2"
 -> Two
+ "Taunt"
 -> Taunt
+ "Menu"
 -> Start
 end_await


== Taunt ==
x = 52
await self comms player
    * "Your mother"  color "red"
        -> Taunt
    + "Kiss my Engine"  color "green"
        -> Taunt
    + "Skip me" color "white" if x > 54
        -> Taunt 
    * "Don't Skip me" color "white" if x < 54
     -> Taunt 
    + "Taunt" 
        -> Taunt
end_await


== One ==
await=>HeadToDS1
await=>HeadToDS2
->One

== Two ==
await=>HeadToDS2
await=>HeadToDS1
->Two

== HeadToDS1 ==
have self approach ds1                           # Goto DS1
await self near  ds1 700
    have self tell player  "I have arrived at ds1"   # tell the player
end_await

== HeadToDS2 ==
have self approach ds2                           # goto DS2
await self near ds2 700                           # wait until near D2
    have self tell player "I have arrived at ds2"    # tell the player
end_await


== Start ==

await self comms player
+ "Say Hello" 
-> Hello
+ "Say Hi"
 -> Hi
+ "Shutup"
 -> Shutup
end_await


== skip ==
have self tell player "Come to pick the princess"
await self near player 300
    have self tell player "You have the princess goto ds1"
end_await
await player near  station 700
    have station tell player "the princess is on ds1"
end_await

== Hello ==
have self tell player "HELLO"

await self comms player
+ "Say Blue"
-> Blue
+ "Say Yellow"
-> Yellow
+ "Say Cyan"
-> Cyan
end_await


== Hi ==
have self tell player  "Hi"
delay 10s
-> Start

== Chat ==
have self tell player "Blah, Blah"
delay 2s
-> Chat

== Shutup ==
cancel chat

== Blue ==
have self tell player "Blue"
delay 10s
-> Start

== Yellow ==
have self tell player "Yellow"
delay 10s
-> Start

== Cyan ==
have self tell player "Cyan"
await self comms player timeout 5s
+ "Say main" -> main
timeout
-> TooSlow
end_await


== TooSlow ==
have self tell player "Woh too slow"
delay 10s
-> Start

""")

        # Run multiple ships using the same Quest
        for i in range(3):
            q = MastShip()
            q.spawn(sim, -500+i*500,0,400, f"TSN {i}", "tsn", "Battle Cruiser" )

            inputs = {
                "player": player,
                "ds1": ds1,
                "ds2": ds2,
                "ship": q,
                "self": q
            }
            q.run(sim, inputs=inputs)
        # Demo threads
        # q.start(sim,"Chat", inputs)


        
  
        



class Spacedock(SpaceObject, MSpawnActive, MCommunications):
    ds_id = 0

    def __init__(self):
        super().__init__()

        Spacedock.ds_id += 1
        self.ds_id = Spacedock.ds_id
        self.comms_id =  f"DS {self.ds_id}"
    
    def spawn(self, sim, x,y,z, side):
        super().spawn(sim,x,y,z,self.comms_id, side, "Starbase", "behav_station")
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




