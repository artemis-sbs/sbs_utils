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
from sbs_utils.widgets.listbox import Listbox
from sbs_utils.pages.start import ClientSelectPage
from sbs_utils.pages.layout import LayoutPage, Layout, Row, Text, Face, Ship
#import sbs_utils
from sbs_utils.mast.mast import Mast
from sbs_utils.mast.mastsbs import MastSbs
from sbs_utils.mast.mastsbsscheduler import MastSbsScheduler

from sbs_utils.mast.maststory import MastStory
from sbs_utils.mast.maststoryscheduler import StoryPage, StoryScheduler
from sbs_utils import fs, query
import os
from sbs_utils.gridobject import GridObject
from random import randrange, choice
# Need this for StubGen to work????
from sbs_utils.pymast.pymaststory import PyMastStory
from sbs_utils.pymast.pymaststorypage import PyMastStoryPage


Mast.enable_logging()



class ShipListDemo(Page):
    
    def __init__(self, ships) -> None:
        self.gui_state = "blank"
        self.picker1 = Listbox(5,5, "pick1:", ships, 
                               text=lambda item: item.comms_id,
                               face=lambda item: faces.get_face(item.id), 
                               ship=lambda item: item.art_id, 
                               item_height=5,
                               select=True)
        self.picker1.bottom = 45
        self.picker1.right = 45
        self.picker4 = Listbox(5,50, "pick4:", ships, 
                               text=lambda item: item.comms_id,
                               #face=lambda item: faces.get_face(item.id), 
                               #ship=lambda item: item.art_id, 
                               item_height=5,
                               multi=True)
        self.picker4.bottom = 95
        self.picker4.right = 45
        self.picker2 = Listbox(50,5, "pick2:", ships, 
                               text=lambda item: item.comms_id,
                               face=lambda item: faces.get_face(item.id), 
                               #ship=lambda item: item.art_id, 
                               item_height=5,
                               select=False)
        self.picker2.bottom = 95
        self.picker2.right = 65
        self.picker3 = Listbox(75,5, "pick3:", ships, 
                               text=lambda item: item.comms_id,
                               #face=lambda item: faces.get_face(item.id), 
                               ship=lambda item: item.art_id, 
                               item_height=5,
                               select=False)
        self.picker3.bottom = 95
        self.picker3.right = 95


    def present(self, ctx, event):
        CID = event.client_id
        if self.gui_state == "presenting":
            return

        sbs.send_gui_clear(CID)
        self.picker1.present(ctx, event)
        self.picker2.present(ctx, event)
        self.picker3.present(ctx, event)
        self.picker4.present(ctx, event)
        sbs.send_gui_button(CID, "back", "text: back", 85,95, 99,99)

        self.gui_state = "presenting"


    def on_message(self, ctx, event):
        if event.sub_tag == 'back':
            Gui.pop(ctx, event.client_id)
        else:
            self.picker1.on_message(ctx,event)
            self.picker2.on_message(ctx,event)
            self.picker3.on_message(ctx,event)
            self.picker4.on_message(ctx,event)

 


class GuiPage(Page):
    count = 0
    def __init__(self) -> None:
        self.gui_state = 'options'
        self.pageid = GuiPage.count 
        GuiPage.count += 1

    def present(self, ctx, event):
        sbs.send_gui_clear(event.client_id)
        sbs.send_gui_text(
                    event.client_id, "text", f"text:Page: {self.pageid}",25, 30, 99, 90)
        w = layout.wrap(99,99, 19, 4,col=1, v_dir=-1, h_dir=-1)
        
        sbs.send_gui_button(event.client_id, "back", "text: Back", *next(w))
        sbs.send_gui_button(event.client_id, "again", "text: Another", *next(w))
        

    def on_message(self, ctx, event):
        if event.sub_tag == 'back':
            Gui.pop(ctx,event.client_id)
        if event.sub_tag == 'again':
            Gui.push(ctx,event.client_id, GuiPage())


class TestLayoutPage(LayoutPage):
    def __init__(self) -> None:
        super().__init__()
        self.layout.left = 30
        self.layout.top = 20
        self.layout.width = 70
        self.layout.height = 70

        text = "  jhkj  kjhhkjh kjhh jkh k kjh jh  jljlk j lk j kj lkj kjlk lkjlk jllk  kjkjl  jhjhkh kh k iojiopipi rrrwqrrq"
        self.layout.add(
            Row()
                .add(Face("tag_two", faces.random_terran()))
                .add(Text("tag_one",text))
        )
        self.layout.add(
            Row()
                #.add(Ship("Battle Cruiser",
                #    "tag_three"))
                .add(Text("tag_four", text))
                .add( Face("tag_five", faces.random_terran()))
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

    def present(self, ctx, event):
        sbs.send_gui_clear(event.client_id)
        sbs.send_gui_text(
            event.client_id, "text", "text: Mission: SBS_Utils unit test.^^This is a unit test for the SBS_Utils library", 25, 30, 99, 90)


        w = layout.wrap(99,99, 19, 4,col=1, v_dir=-1, h_dir=-1)
        

        sbs.send_gui_button(event.client_id, "start", "text: Start Mission", *next(w))
        sbs.send_gui_button(event.client_id, "smoke", "text: smoke test", *next(w))
        sbs.send_gui_button(event.client_id, "vec_unit", "text: Vec3 tests", *next(w))
        sbs.send_gui_button(event.client_id, "face", "text: face test", *next(w))
        sbs.send_gui_button(event.client_id, "face_gen", "text: face gen", *next(w))
        sbs.send_gui_button(event.client_id, "again", "text: Gui Pages", *next(w))
        sbs.send_gui_button(event.client_id, "avatar", "text: Avatar Editor", *next(w))
        sbs.send_gui_button(event.client_id, "ship", "text: Ship Picker", *next(w))
        sbs.send_gui_button(event.client_id, "shiplist", "text: Ship Lists", *next(w))
        sbs.send_gui_button(event.client_id, "stub", "text: StubGen", *next(w))
        sbs.send_gui_button(event.client_id, "layout", "text: Layout", *next(w))
        sbs.send_gui_button(event.client_id, "story", "text: Mast bar", *next(w))
        sbs.send_gui_button(event.client_id, "story_ttt", "text: Mast ttt", *next(w))
        sbs.send_gui_button(event.client_id, "grid", "text: GridItems", *next(w))
        sbs.send_gui_button(event.client_id, "siege", "text: Mast Siege", *next(w))
        sbs.send_gui_complete(event.client_id)

    def on_message(self, ctx, event):
        Gui.client_start_page_class(ClientSelectPage)
        match event.sub_tag:
            case 'again':
                # reset state here?
                Gui.push(ctx,event.client_id, GuiPage())

            case 'avatar':
                # reset state here?
                Gui.push(ctx,event.client_id, AvatarEditor())

            case 'stub':
                self.stub_gen()

            case 'ship':
                # reset state here?
                Gui.push(ctx,event.client_id, ShipPicker())

            case 'shiplist':
                # reset state here?
                sbs.create_new_sim()
                enemy_ships = ["skaraan_defiler", "skaraan_enforcer","kralien_battleship", "kralien_cruiser", "torgoth_goliath", "torgoth_leviathan", "torgoth_behemoth"]
                ships = []
                markers = "QKWR"

                for ship in range(20):
                    marker = f"{choice(markers)}_{randrange(99)}"
                    ship_art = choice(enemy_ships)

                    npc = Npc()
                    npc.spawn(ctx.sim, 500+ship*200,0,500,marker, "raider", ship_art, "behav_npcship")
                    face = faces.random_terran()
                    faces.set_face(npc.id, face)
                    ships.append(npc)
                Gui.push(ctx,event.client_id, ShipListDemo(ships))
                Gui.client_start_page_class(lambda: ShipListDemo(ships))

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
                Mission.face_test(ctx.sim)

            case "layout":
                Gui.push(ctx,event.client_id, TestLayoutPage())

            case "story":
                page = GuiStory()
                #page.run(sim , story_script)        
                Gui.client_start_page_class(GuiStory)        
                Gui.push(ctx,event.client_id, page)

            case "siege":
                page = SiegeStory()
                #page.run(sim , story_script)        
                Gui.client_start_page_class(SiegeStory)        
                Gui.push(ctx,event.client_id, page)
                
            case "story_ttt":
                page = TttStory()
                #page.run(sim , story_script)                
                Gui.push(ctx,event.client_id, page)

            case "face_gen":
                sbs.create_new_sim()
                sbs.resume_sim()
                Mission.face_gen(ctx.sim)

            case "start":
                sbs.create_new_sim()
                sbs.resume_sim()
                Mission.start(ctx)

            case "grid":
                sbs.create_new_sim()
                sbs.resume_sim()
                Mission.start_grid(ctx.sim)

            case "mast":
                sbs.create_new_sim()
                sbs.resume_sim()
                Mission.mast(ctx.sim)

            case "target":
                sbs.create_new_sim()
                sbs.resume_sim()
                Mission.target_bug(ctx.sim)


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

    def start(ctx):
        TickDispatcher.do_once(ctx, Mission.once, 5)
        TickDispatcher.do_interval(ctx, Mission.many, 5, 4)
        TickDispatcher.do_once(ctx, Mission.test, 30)

    def face_test(sim):
        t = TickDispatcher.do_interval(sim, Mission.new_face,0)
        t.player = PlayerShip()
        t.player.spawn(sim, 0,0,0, "Artemis", "tsn", "tsn_battle_cruiser")
        
        t.race = 0

    def face_gen(sim):
        PlayerShip().spawn(sim, 0,0,0, "Artemis", "tsn", "tsn_battle_cruiser")
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

        player_id = sim.make_new_player("behav_playership", "tsn_battle_cruiser")
        sbs.assign_player_ship(player_id)
        player = sim.get_space_object(player_id)
        player.side = "TSN";
        blob = player.data_set
        blob.set("name_tag", "Artemis", 0)
        sim.reposition_space_object(player, 0, 0, 10)

        other_id = sim.make_new_active("behav_npcship", "tsn_battle_cruiser")
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
        sd_player = player.spawn(sim, 0,0,0, "Artemis", "tsn", "tsn_battle_cruiser")
        sbs.assign_client_to_ship(0, sd_player.id)
        go1 = GridObject()
        go1.spawn(sim, sd_player.id, "fred", "fred", 9,4, 3, "blue", "flint")
        go2 = GridObject()
        go2.spawn(sim, sd_player.id, "barney", "barney", 8,4, 3, "green", "rubble")
        go2.update_blob(sim, speed=0.01, icon_scale=1.3)
        query.grid_target_pos(go2, sim, 9,12)
        #GridDispatcher.add_object(go2.id, lambda sim, event: print("Barney Arrived"))
        
        




class Spacedock(SpaceObject, MSpawnActive, MCommunications):
    ds_id = 0

    def __init__(self):
        super().__init__()

        Spacedock.ds_id += 1
        self.ds_id = Spacedock.ds_id
        
    
    def spawn(self, sim, x,y,z, side):
        use_name =  f"DS {self.ds_id}"
        super().spawn(sim,x,y,z,use_name, side, "starbase_command", "behav_station")
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
Gui.client_start_page_class(ClientSelectPage)




