import unittest
import types

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.engine_guards import install_engine_guards


class TestGetShipOfClientGuard(unittest.TestCase):
    """The engine ASSERTS (whole server down) on get_ship_of_client(<space object id>).
    The guard must stop that id before the engine sees it, and pass real ones through."""

    def setUp(self):
        self.seen = []
        fake = types.SimpleNamespace()
        fake.get_ship_of_client = lambda cid: self.seen.append(cid) or 0x4000000000000004
        install_engine_guards(fake)
        self.sbs = fake

    def test_ship_id_never_reaches_the_engine(self):
        self.assertEqual(self.sbs.get_ship_of_client(0x4000000000000018), 0)
        self.assertEqual(self.seen, [])

    def test_client_and_server_pass_through(self):
        self.assertEqual(self.sbs.get_ship_of_client(0x8000000000000001), 0x4000000000000004)
        self.sbs.get_ship_of_client(0)
        self.assertEqual(self.seen, [0x8000000000000001, 0])

    def test_install_is_idempotent(self):
        wrapped = self.sbs.get_ship_of_client
        install_engine_guards(self.sbs)
        self.assertIs(self.sbs.get_ship_of_client, wrapped)


if __name__ == "__main__":
    unittest.main()
