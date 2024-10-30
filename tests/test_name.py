import unittest
import sys
sys.path.append("..")
from mock import sbs as sbs
from sbs_utils import names
from sbs_utils.fs import test_set_exe_dir
from sbs_utils.procedural import ship_data
import sys
    
class FakeSim:
    def __init__(self) -> None:
        self.time_tick_counter = 0
    def tick(self):
        self.time_tick_counter +=30


class TestNames(unittest.TestCase):

    def test_init(self):
        for i in range(1296):
            sys.stdout.write(names.random_canonical_kralien_comms_id(i,"kralien_cruiser") +"   ")
            if i%6 == 5:
                sys.stdout.write('\n')
        self.assertEqual(3, 3)

    def test_yaml(self):
        import sbs_utils.yaml as yaml

        names_yaml = """
            - 'eric'
            - 'justin'
            - 'mary-kate'
"""
        names = yaml.safe_load(names_yaml)
        assert(len(names)==3)



    def test_filter_ship_data(self):
        test_set_exe_dir()
        ast = ship_data.asteroid_keys()
        self.assertEqual(len(ast), 11)
        cast = ship_data.crystal_asteroid_keys()
        self.assertEqual(len(cast), 5)
        past = ship_data.plain_asteroid_keys()
        self.assertEqual(len(past), 6)
        ships = ship_data.terran_ship_keys()
        self.assertGreater(len(ships), 0)
        ships = ship_data.pirate_ship_keys()
        self.assertGreater(len(ships), 0)

        
        ships = ship_data.arvonian_ship_keys()
        self.assertGreater(len(ships), 0)
        ships = ship_data.skaraan_ship_keys()
        self.assertGreater(len(ships), 0)
        ships = ship_data.kralien_ship_keys()
        self.assertGreater(len(ships), 0)
        ships = ship_data.torgoth_ship_keys()
        self.assertGreater(len(ships), 0)
        ships = ship_data.ximni_ship_keys()
        self.assertGreater(len(ships), 0)
        

