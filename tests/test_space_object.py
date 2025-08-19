
from mock import sbs as sbs # not sure why I need this
import unittest

from sbs_utils.spaceobject import SpaceObject, TickType
from sbs_utils.procedural.query import to_py_object_list
from sbs_utils.procedural.links import linked_to
from sbs_utils.procedural.inventory import has_inventory_value
from sbs_utils.procedural.space_objects import closest_list, closest, broad_test
from sbs_utils.procedural.roles import role, get_role_list, get_role_string
from sbs_utils.fs import test_set_exe_dir, get_script_dir
from sbs_utils.objects import Npc, Terrain, PlayerShip
from sbs_utils.gridobject import GridObject
from sbs_utils.helpers import FrameContext, Context, FakeEvent
import os


def get_sim():
    """ Function in case I change how to get the sim"""
    return sbs.sim


class TestSpaceObject(unittest.TestCase):
    def setUp(self) -> None:
        ### This clears all the role info
        SpaceObject.clear()


        test_set_exe_dir()
        
        return super().setUp()
    
    def test_space_object(self):
        """ Test for the basic creation of SpaceObjects"""
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent()) 


        artemis = PlayerShip().spawn(0,0,0, "Artemis", "tsn", "Battle Cruiser")
        assert(artemis is not None)
        assert(artemis.py_object is not None)
        assert(artemis.py_object.is_player)
        assert(not artemis.py_object.is_passive)
        assert(not artemis.py_object.is_terrain)
        assert(not artemis.py_object.is_npc)
        assert(not artemis.py_object.is_active)
        assert(artemis.py_object.has_role("__PLAYER__"))
        assert(artemis.py_object.has_role("PlayerShip"))
        assert(artemis.py_object.has_role("tsn"))
        assert(artemis.py_object.comms_id == "Artemis (tsn)")

        ds1 = Npc().spawn(0,0,0, f"DS1", "tsn", "Starbase", "behav_spaceport")
        py_ds1 = ds1.py_object 
        assert(py_ds1 is not None)
        assert(not py_ds1.is_player)
        assert(not py_ds1.is_passive)
        assert(not py_ds1.is_terrain)
        assert(py_ds1.is_npc)
        assert(py_ds1.is_active)
        assert(py_ds1.has_role("__NPC__"))
        assert(py_ds1.has_role("Npc"))
        assert(py_ds1.has_role("tsn"))
        assert(py_ds1.comms_id == "DS1 (tsn)")

        ast = Terrain().spawn(0,0,0, None, None, "Asteroid 1", "behav_asteroid")
        py_ast = ast.py_object 
        assert(py_ast is not None)
        assert(not py_ast.is_player)
        assert(py_ast.has_role("__TERRAIN__"))
        assert(py_ast.has_role("Terrain"))
        assert(not py_ast.is_player)
        assert(py_ast.is_passive)
        assert(py_ast.is_terrain)
        assert(not py_ast.is_npc)
        assert(not py_ast.is_active)

        # Sanity check to make sure
        # SpaceObject and GridObject are sharing static data
        assert(len(GridObject.all.keys())!=0)
        assert(len(SpaceObject.all.keys())!=0)
        assert(SpaceObject.all.keys()==GridObject.all.keys())


        assert(py_ast.comms_id == "")


    
    def test_roles(self):
        test_obj = []
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent()) 

        names = ["Artemis", "Hera", "Atlas", "Juno", "Zeus", "Jupiter"]
        for name in names:
            test_obj.append(PlayerShip().spawn(0,0,0, name, "tsn, test_side_role", "tsn_battle_cruiser").py_object)
        
        for station in range(5):
            station = Npc().spawn(0,0,0, f"DS{station}", "tsn, test_side_role", "starbase_command", "behav_spaceport").py_object
            test_obj.append(station)
            station.add_role("Station")

            role_list = get_role_list(station)
            assert(len(role_list)>0)
            role_string = get_role_string(station)
            assert(",".join(role_list)==role_string)
            assert("tsn" in role_string)
            assert("test_side_role" in role_string)
            assert("station" in role_string)


        # Test is they all have side as a role
        for obj in test_obj:
            assert(obj.has_role("tsn"))
            assert(obj.has_role("test_side_role"))

        players_a = len(SpaceObject.get_role_objects("__PLAYER__"))
        players_b = len(SpaceObject.get_role_objects("PlayerShip"))
        stations = len(SpaceObject.get_role_objects("Station"))
        tsn = len(SpaceObject.get_role_objects("tsn"))

        assert(tsn == len(test_obj))
        assert(players_a==players_b)
        assert(players_a == len(names))
        assert(stations==5)

        #
        # test default values
        #
        for obj in SpaceObject.get_role_objects("__PLAYER__"):
            assert(obj.has_role("ship"))
        
        
        ###test remove role
        stations = SpaceObject.get_role_objects("Station")
        first = stations[0]
        last = stations[-1]
        first.remove_role("Station")
        last.remove_role("Station")
        stations = SpaceObject.get_role_objects("Station")
        assert(len(stations)==3)

        players = SpaceObject.get_role_objects("PlayerShip")
        players[0].add_link("Visit", stations[0])
        assert(players[0].has_link_to("Visit", stations[0]))


        # LINK to any objet
        test = object()
        players[0].add_link("Visit", test)
        assert(players[0].has_link_to("Visit", test))
        # This is a test to make sure objects are different than ints
        test_id = id(test)
        assert(not players[0].has_link_to("Visit", test_id))
        assert(players[0].id in SpaceObject.has_links_set("Visit"))

        stations = SpaceObject.get_role_objects("Station")
        assert(len(stations)==3)


    def test_closest_old_method(self):
        test_obj = []
        names = ["Artemis", "Hera", "Atlas", "Juno", "Zeus", "Jupiter"]
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent()) 

        for i, name in enumerate(names):
            test_obj.append(PlayerShip().spawn(i*100,0,0, name, "tsn", "Battle Cruiser").py_object)
        
        for station in range(5):
            station_obj = Npc().spawn(station*100,0,100, f"DS{station}", "tsn", "Starbase", "behav_spaceport").py_object
            test_obj.append(station_obj)
            station_obj.add_role("Station")
            eo = station_obj.get_space_object()
            assert(eo)
            pos = eo.pos
            assert(pos.x == station*100)
            assert(pos.y == 0)
            assert(pos.z == 100)

        stations = SpaceObject.get_role_objects("Station")
        players = SpaceObject.get_role_objects("PlayerShip")
        # Make sure mock is return right values
        dist = sbs.distance(stations[0].get_space_object(), stations[1].get_space_object())
        assert(dist == 100)
        dist = sbs.distance_id(stations[0].id, stations[1].id)
        assert(dist == 100)
        dist = sbs.distance_id(stations[0].id, stations[2].id)
        assert(dist == 200)

        # test = players[0].find_close_list(sim, "Station")
        # assert(len(test)==5) 

        # test = players[0].find_closest(sim, "Station")
        # name = test.py_object.name
        # assert(name=="DS0") 


    def test_closest_set_method(self):
        test_obj = []
        names = ["Artemis", "Hera", "Atlas", "Juno", "Zeus", "Jupiter"]
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent()) 

        for i, name in enumerate(names):
            test_obj.append(PlayerShip().spawn(i*100,0,0, name, "tsn", "Battle Cruiser").py_object)

        players = role("PlayerShip")
        assert(len(players)==6)
        players=list(players)
        artemis = players[0]

        player_objs = to_py_object_list(players)
        assert(len(player_objs) == len(players))

        
        for station in range(5):
            station_obj = Npc().spawn(station*100,0,100, f"DS{station}", "tsn", "Starbase", "behav_spaceport").py_object
            test_obj.append(station_obj)
            station_obj.add_role("Station")
            # Add there visits to artemis
            if station % 2:
                player_objs[0].add_link("Visit", station_obj)
            eo = station_obj.get_space_object()
            assert(eo)
            pos = eo.pos
            assert(pos.x == station*100)
            assert(pos.y == 0)
            assert(pos.z == 100)

        for friendly in range(5):
            friendly_obj = Npc().spawn(friendly*100,0,100, f"F{friendly}", "tsn", "Light Cruiser", "behav_npcship").py_object
            if friendly  % 2:
                player_objs[0].add_link("Visit", friendly_obj)


        for raider in range(5):
            Npc().spawn(station*100,0,100, f"R{raider}", "raider", "Light Cruiser", "behav_npcship").py_object


        stations = role("Station")
        assert(len(stations)==5)



        test = closest(artemis, role("Station"))
        print(f"{test.py_object.name}")
        assert(test.py_object.name=="DS0") 

        all = role("PlayerShip") | role("Station")
        assert(len(all)==11)
        all = all - role("Station")
        assert(len(all)==6)

        # get a set of things with the role Station
        stations = role("Station")
        assert(len(stations)==5)
        # Get the list of things artemis is supposed to visit
        visit_list = linked_to(artemis, "Visit")
        assert(len(visit_list )==4)
        # Get the set active objects in the area
        in_range = broad_test(10000,10000, -10000, -10000, 0x10)
        assert(len(in_range)==15)
        test = in_range & visit_list & stations 
        assert(len(test)==2) # 2 stations and NOT the two friendly
        # get the closest stations Artemis is assigned to visit the is in
        test = closest(artemis,  in_range & visit_list & stations )

        assert(test.py_object.name == "DS1")

        test = closest(artemis,  
            broad_test(10000,10000, -10000, -10000, 0xF0) 
            & linked_to(artemis, "Visit")
            & role("Station") )
        assert(test.py_object.name == "DS1")

        # Gets the all visitable in range
        test = closest_list(artemis,  
            broad_test(5000,5000, -5000, -5000, 0xF0) 
            & linked_to(artemis, "Visit")
             )
        assert(len(test)==4)
        names = [obj.py_object.name for obj in test]
        assert("DS1" in names)
        assert("F1" in names)
        assert("DS3" in names)
        assert("F3" in names)
        # Gets the all visitable in narrower range
        test = closest_list(artemis,  
            broad_test(200,200, -200, -200, 0xF0) 
            & linked_to(artemis, "Visit")
             )
        assert(len(test)==2)
        names = [obj.py_object.name for obj in test]
        assert("DS1" in names)
        assert("F1" in names)

        # get all visitable that are not stations
        test = closest_list(artemis,  
            broad_test(10000,10000, -10000, -10000, 0xF0) 
            & linked_to(artemis, "Visit")
            - role("Station") )
        assert(len(test)==2)
        names = [obj.py_object.name for obj in test]
        assert("F1" in names)
        assert("F3" in names)

        # get all visitable that are stations
        test = closest_list(artemis,  
            broad_test(10000,10000, -10000, -10000, 0xFF) 
            & linked_to(artemis, "Visit")
            & role("Station") )
        assert(len(test)==2)
        names = [obj.py_object.name for obj in test]
        assert("DS1" in names)
        assert("DS3" in names)

        friendly_tsn = role("tsn") - role("PlayerShip") - role("Station")
        assert(len(friendly_tsn) == 5)
        names = [obj.name for obj in to_py_object_list(friendly_tsn)]
        assert("F0" in names)
        assert("F1" in names)
        assert("F2" in names)
        assert("F3" in names)
        assert("F4" in names)

        raiders = role("Npc") - role("tsn")
        assert(len(raiders) == 5)
        names = [obj.name for obj in to_py_object_list(raiders)]
        assert("R0" in names)
        assert("R1" in names)
        assert("R2" in names)
        assert("R3" in names)
        assert("R4" in names)
        

    def test_fake_broad_test(self):
        test_obj = []
        names = ["Artemis", "Hera", "Atlas", "Juno", "Zeus", "Jupiter"]
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent()) 

        for i, name in enumerate(names):
            test_obj.append(PlayerShip().spawn(i*100,0,0, name, "tsn", "Battle Cruiser").py_object)

        for station in range(5):
            station_obj = Npc().spawn(station*100-5,0,100, f"DS{station}", "tsn", "Starbase", "behav_spaceport").py_object
            test_obj.append(station_obj)
            station_obj.add_role("Station")

        for asteroid in range(10):
            asteroid_obj = Terrain().spawn(asteroid*100-10,0,200, None, None, "Asteroid 1", "behav_asteroid").py_object
            asteroid_obj.add_role("Asteroid")
        
        test = sbs.broad_test(-50,-50, 50,50, TickType.ALL)
        assert(len(test)==1) # Just the player

        test = sbs.broad_test(-100,-200, 100,200, TickType.ALL)
        assert(len(test)==5) # 1 Player, 2 npc, 2 asteroid

        # """int, 0=passive, 1=active, 2=playerShip""" #
        for asteroid in range(1,11):
            test = sbs.broad_test(-(asteroid*100-20),-200, asteroid*100-20,200, TickType.PASSIVE)
            assert(len(test)==asteroid) # Just the asteroid
            assert(test[0].data_tag=="Asteroid 1")

        for station in range(1,6):
            test = sbs.broad_test(-(station)*100+20,-100, (station)*100-20,100, TickType.NPC)
            assert(len(test)==station) # Just the starbases
            assert(test[0].data_tag=="Starbase")
        
        for player in range(1,7):
            test = sbs.broad_test(-(player*100)-10,-100, (player*100)-10,100, TickType.PLAYER)
            assert(len(test)==player) # Just the player
            assert(test[0].data_tag=="Battle Cruiser")

    def test_inventory(self):
        
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent()) 

        
        artemis = PlayerShip().spawn(0,0,0, "Artemis", "tsn", "Battle Cruiser").py_object
        artemis.set_inventory_value("Gold", 5)
        assert(artemis.has_any_inventory("Gold"))
        assert(artemis.get_inventory_value("Gold")==5)

        class Passenger:
            def __init__(self, name):
                self.name = name

        kirk = Passenger("Kirk")
        spock = Passenger("Spock")
        mccoy = Passenger("McCoy")
        artemis.add_inventory("Passengers", kirk)
        artemis.add_inventory("Passengers", spock)
        artemis.add_inventory("Passengers", mccoy)
        artemis.add_inventory("Doctor", mccoy)

        passengers = artemis.get_inventory_set("Passengers")
        assert(len(passengers)==3)
        names = [obj.name for obj in passengers]
        assert("Kirk" in names)
        assert("Spock" in names)
        assert("McCoy" in names)

        doctors = artemis.get_inventory_set("Doctor")
        assert(len(doctors)==1)
        names = [obj.name for obj in doctors]
        assert("McCoy" in names)

        collections = artemis.get_inventory_in(mccoy)
        assert(len(collections)==2)
        # role, links are all lower now
        # but inventory is not
        assert("Passengers" in collections)
        assert("Doctor" in collections)
        assert("passengers" not in collections)
        assert("doctor" not in collections)

        artemis.remove_inventory("Passengers", mccoy)
        collections = artemis.get_inventory_in(mccoy)
        assert(len(collections)==1)
        assert("Doctor" in collections)


        collections = artemis.get_inventory_in(spock)
        assert(len(collections)==1)
        # Inventory is case sensitive
        assert("Passengers" in collections)
        

        passengers = artemis.get_inventory_set("Passengers")
        assert(len(passengers)==2)
        names = [obj.name for obj in passengers]
        assert("Kirk" in names)
        assert("Spock" in names)

    def test_inventory_find_inventory(self):

        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent()) 

        
        for x in range(10):
            artemis = PlayerShip().spawn(0,0,0, "Artemis", "tsn", "Battle Cruiser").py_object
            if (x % 2)==1:
                artemis.set_inventory_value("Gold", 5)
            else:
                artemis.set_inventory_value("Gold", 12)

        the_set = has_inventory_value("Gold", 5)
        assert(len(the_set)==5)
        the_set = has_inventory_value("Gold", 12)
        assert(len(the_set)==5)

