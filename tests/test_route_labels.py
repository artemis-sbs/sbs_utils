from sbs_utils.mast.mast import Mast
from sbs_utils.agent import clear_shared
from sbs_utils.mast_sbs import story_nodes  # registers Cosmos MAST nodes via @mast_node()
import unittest


def compile_mast(code):
    mast = Mast()
    clear_shared()
    errors = mast.compile(code, "test", mast)
    return errors, mast


class TestRouteLabels(unittest.TestCase):

    def test_spawn_routes(self):
        errors, _ = compile_mast("""
->END

//spawn
//spawn/grid
""")
        self.assertEqual(errors, [], errors)

    def test_comms_route(self):
        errors, _ = compile_mast("""
->END

//comms/my_path
//comms/nested/path
""")
        self.assertEqual(errors, [], errors)

    def test_science_route(self):
        errors, _ = compile_mast("""
->END

//science
""")
        self.assertEqual(errors, [], errors)

    def test_gui_route(self):
        errors, _ = compile_mast("""
->END

//gui/my_panel
""")
        self.assertEqual(errors, [], errors)

    def test_popup_route(self):
        errors, _ = compile_mast("""
->END

//popup/my_popup
""")
        self.assertEqual(errors, [], errors)

    def test_damage_routes(self):
        errors, _ = compile_mast("""
->END

//damage/object
//damage/destroy
//damage/killed
//damage/internal
//damage/heat
""")
        self.assertEqual(errors, [], errors)

    def test_collision_routes(self):
        errors, _ = compile_mast("""
->END

//collision/passive
//collision/interactive
""")
        self.assertEqual(errors, [], errors)

    def test_launch_routes(self):
        errors, _ = compile_mast("""
->END

//launch/missile
//launch/drone
""")
        self.assertEqual(errors, [], errors)

    def test_dock_route(self):
        errors, _ = compile_mast("""
->END

//dock/hangar
""")
        self.assertEqual(errors, [], errors)

    def test_focus_routes(self):
        errors, _ = compile_mast("""
->END

//focus/comms
//focus/comms2d
//focus/normal
//focus/weapons
//focus/science
//focus/grid
""")
        self.assertEqual(errors, [], errors)

    def test_select_routes(self):
        errors, _ = compile_mast("""
->END

//select/comms
//select/comms2d
//select/normal
//select/weapons
//select/science
//select/grid
""")
        self.assertEqual(errors, [], errors)

    def test_point_routes(self):
        errors, _ = compile_mast("""
->END

//point/comms
//point/comms2d
//point/normal
//point/weapons
//point/science
//point/grid
""")
        self.assertEqual(errors, [], errors)

    def test_object_grid_route(self):
        errors, _ = compile_mast("""
->END

//object/grid
""")
        self.assertEqual(errors, [], errors)

    def test_signal_routes(self):
        errors, _ = compile_mast("""
->END

//signal/enemy_destroyed
//shared/signal/mission_complete
""")
        self.assertEqual(errors, [], errors)

    def test_route_with_condition(self):
        errors, _ = compile_mast("""
->END

//spawn if enemy_count > 0
//damage/object if shield_level < 50
""")
        self.assertEqual(errors, [], errors)

    def test_route_with_body(self):
        errors, _ = compile_mast("""
->END

//spawn
    x = 1
    ->END
""")
        self.assertEqual(errors, [], errors)

    def test_invalid_route_produces_error(self):
        errors, _ = compile_mast("""
->END

//not/a/real/route
""")
        self.assertGreater(len(errors), 0)

    def test_inline_route(self):
        errors, _ = compile_mast("""
///my_handler
->END
""")
        self.assertEqual(errors, [], errors)


if __name__ == '__main__':
    unittest.main()
