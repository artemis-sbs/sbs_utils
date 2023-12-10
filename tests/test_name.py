import unittest
import sys
sys.path.append("..")
from mock import sbs as sbs
from sbs_utils import names
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

    def test_filter_ship_data(self):
        ast = names.asteroid_keys()
        self.assertEqual(len(ast), 11)
        cast = names.crystal_asteroid_keys()
        self.assertEqual(len(cast), 5)
        past = names.plain_asteroid_keys()
        self.assertEqual(len(past), 6)
        ships = names.terran_ship_keys()
        self.assertGreater(len(ships), 0)
        ships = names.pirate_ship_keys()
        self.assertGreater(len(ships), 0)

        
        ships = names.arvonian_ship_keys()
        self.assertGreater(len(ships), 0)
        ships = names.skaraan_ship_keys()
        self.assertGreater(len(ships), 0)
        ships = names.kralien_ship_keys()
        self.assertGreater(len(ships), 0)
        ships = names.torgoth_ship_keys()
        self.assertGreater(len(ships), 0)
        ships = names.ximni_ship_keys()
        self.assertGreater(len(ships), 0)
        

