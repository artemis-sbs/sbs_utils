import unittest
from sbs_utils import names
import sys

class TestNames(unittest.TestCase):

    def test_init(self):
        for i in range(1296):
            sys.stdout.write(names.random_canonical_kralien_comms_id(i,"kralien_cruiser") +"   ")
            if i%6 == 5:
                sys.stdout.write('\n')
        self.assertEqual(3, 3)

    def test_something(self):
        test = set()
        # for i,id in enumerate(id_pool["kralien_cruiser"]):
        #     name = kralien_name(id)
        #     sys.stdout.write(name)
        #     sys.stdout.write("   ")
        #     if (i % 6)==5:
        #         print()
        #     test.add(name)
        print(len(test))