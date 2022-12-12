import unittest
from . import mock_sbs as sbs

from sbs_utils.spaceobject import SpaceObject, role, linked_to, closest_list, closest, random, broad_test
from sbs_utils.objects import Npc, Terrain, PlayerShip

def get_sim():
    """ Function in case I change how to get the sim"""
    return sbs.sim


class TestMastSbsCompile(unittest.TestCase):
    
    
    def test_space_object(self):
        """ Test for the basic creation of SpaceObjects"""
        sbs.create_new_sim()
        sim = get_sim()

        artemis = PlayerShip().spawn(sim, 0,0,0, "Artemis", "tsn", "Battle Cruiser")
        assert(artemis is not None)
        assert(artemis.py_object is not None)
        assert(artemis.py_object.is_player)
        assert(artemis.py_object.has_role("__PLAYER__"))
        assert(artemis.py_object.has_role("PlayerShip"))
        assert(artemis.py_object.has_role("tsn"))
        assert(artemis.py_object.comms_id == "Artemis(tsn)")

        ds1 = Npc().spawn(sim, 0,0,0, f"DS1", "tsn", "Starbase", "behav_spaceport")
        py_ds1 = ds1.py_object 
        assert(py_ds1 is not None)
        assert(not py_ds1.is_player)
        assert(py_ds1.has_role("Npc"))
        assert(py_ds1.has_role("tsn"))
        assert(py_ds1.comms_id == "DS1(tsn)")

        ast = Terrain().spawn(sim, 0,0,0, None, None, "Asteroid 1", "behav_asteroid")
        py_ast = ast.py_object 
        assert(py_ast is not None)
        assert(not py_ast.is_player)
        assert(py_ast.has_role("Terrain"))

        assert(py_ast.comms_id == "")


    
    def test_roles(self):
        test_obj = []
        sbs.create_new_sim()
        sim = get_sim()

        names = ["Artemis", "Hera", "Atlas", "Juno", "Zeus", "Jupiter"]
        for name in names:
            test_obj.append(PlayerShip().spawn(sim, 0,0,0, name, "tsn", "Battle Cruiser").py_object)
        
        for station in range(5):
            station = Npc().spawn(sim, 0,0,0, f"DS{station}", "tsn", "Starbase", "behav_spaceport").py_object
            test_obj.append(station)
            station.add_role("Station")

        # Test is they all have side as a role
        for obj in test_obj:
            assert(obj.has_role("tsn"))

        players_a = len(SpaceObject.get_objects_with_role("__PLAYER__"))
        players_b = len(SpaceObject.get_objects_with_role("PlayerShip"))
        stations = len(SpaceObject.get_objects_with_role("Station"))
        tsn = len(SpaceObject.get_objects_with_role("tsn"))

        assert(tsn == len(test_obj))
        assert(players_a==players_b)
        assert(players_a == len(names))
        assert(stations==5)

        ###test remove role
        stations = SpaceObject.get_objects_with_role("Station")
        first = stations[0]
        last = stations[-1]
        first.remove_role("Station")
        last.remove_role("Station")
        stations = SpaceObject.get_objects_with_role("Station")
        assert(len(stations)==3)

        players = SpaceObject.get_objects_with_role("PlayerShip")
        players[0].add_link("Visit", stations[0])
        assert(players[0].has_link_to("Visit", stations[0]))


        # LINK to any objet
        test = object()
        players[0].add_link("Visit", test)
        assert(players[0].has_link_to("Visit", test))
        # This is a test to make sure objects are different than ints
        test_id = id(test)
        assert(not players[0].has_link_to("Visit", test_id))

        stations = SpaceObject.all("Station")
        assert(len(stations)==3)


    def test_closest_old_method(self):
        test_obj = []
        names = ["Artemis", "Hera", "Atlas", "Juno", "Zeus", "Jupiter"]
        sbs.create_new_sim()
        sim = get_sim()

        for i, name in enumerate(names):
            test_obj.append(PlayerShip().spawn(sim, i*100,0,0, name, "tsn", "Battle Cruiser").py_object)
        
        for station in range(5):
            station_obj = Npc().spawn(sim, station*100,0,100, f"DS{station}", "tsn", "Starbase", "behav_spaceport").py_object
            test_obj.append(station_obj)
            station_obj.add_role("Station")
            eo = station_obj.get_space_object(sim)
            assert(eo)
            pos = eo.pos
            assert(pos.x == station*100)
            assert(pos.y == 0)
            assert(pos.z == 100)

        stations = SpaceObject.get_objects_with_role("Station")
        players = SpaceObject.get_objects_with_role("PlayerShip")
        # Make sure mock is return right values
        dist = sbs.distance(stations[0].get_space_object(sim), stations[1].get_space_object(sim))
        assert(dist == 100)
        dist = sbs.distance_id(stations[0].id, stations[1].id)
        assert(dist == 100)
        dist = sbs.distance_id(stations[0].id, stations[2].id)
        assert(dist == 200)

        test = players[0].find_close_list(sim, "Station")
        assert(len(test)==5) 

        test = players[0].find_closest(sim, "Station")
        name = test.py_object.name
        assert(name=="DS0") 


    def test_closest_set_method(self):
        test_obj = []
        names = ["Artemis", "Hera", "Atlas", "Juno", "Zeus", "Jupiter"]
        sbs.create_new_sim()
        sim = get_sim()

        for i, name in enumerate(names):
            test_obj.append(PlayerShip().spawn(sim, i*100,0,0, name, "tsn", "Battle Cruiser").py_object)
        
        for station in range(5):
            station_obj = Npc().spawn(sim, station*100,0,100, f"DS{station}", "tsn", "Starbase", "behav_spaceport").py_object
            test_obj.append(station_obj)
            station_obj.add_role("Station")
            eo = station_obj.get_space_object(sim)
            assert(eo)
            pos = eo.pos
            assert(pos.x == station*100)
            assert(pos.y == 0)
            assert(pos.z == 100)

        players = role("PlayerShip")
        assert(len(players)==6)
        stations = role("Station")
        assert(len(stations)==5)
        players=list(players)
        artemis = players[0]

        test = closest(artemis, role("Station"))
        assert(test.py_object.name=="DS0") 

        all = role("PlayerShip") | role("Station")
        assert(len(all)==11)
        all = all - role("Station")
        assert(len(all)==6)

        # get a set of things with the role Station
        stations = role("Station")
        # Get the list of things artemis is supposed to visit
        visit_list = linked_to(artemis, "Visit")
        # Get the set active objects in the area
        in_range = broad_test(10000,10000, -10000, -10000, 2)
        # get the closest stations Artemis is assigned to visit the is in
        test = closest(artemis,  in_range & visit_list & stations )

        test = closest(artemis,  
            broad_test(10000,10000, -10000, -10000, 2) 
            & linked_to(artemis, "Visit")
            & role("Station") )

        friendly_tsn = role("tsn") - role("PlayerShip") - role("Station")
        




        

        


        





        