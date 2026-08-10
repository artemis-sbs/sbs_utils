"""Every name the incoming-hail consoles call must actually reach MAST.

This exists because the failure it guards is INVISIBLE to the headless runner. A
mission's console layout only names these when a console renders, and the exerciser
never reaches the comms console (it forces combat, the player dies, console cycling
stops) - so a `.mast` file naming something MAST cannot see still reports PASS, and the
NameError waits for a human to open that console.

Two rules are asserted, both learned the hard way:

* Only FUNCTIONS become MAST globals. A module-level constant is never exported, so
  `HAIL_PANEL_ICON` was invisible and `hail_panel_icon()` is not.
* A function is only exported if it is reachable from the imported PACKAGE - which for
  `sbs_utils.procedural.gui` means being re-exported from its `__init__`.

    python -m unittest tests.test_hail_mast_namespace
"""
import unittest
from inspect import isfunction

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from sbs_utils.procedural import gui as GUI_PKG
from sbs_utils.procedural import hail as HAIL

# Exactly what LegendaryMissions' console layout calls today. Add to this when a
# console starts calling something new; that is the point of the list.
CALLED_FROM_MAST = {
    "sbs_utils.procedural.hail": (
        "hail_is_active", "hail_shows_here", "hail_form", "hail_repaint_needed",
        "hail_offer", "hail_offer_amd", "hail_accept", "hail_answer", "hail_close",
        "hail_pending_count", "hail_where", "hail_where_set", "hail_console_cares",
        "hail_console_revision", "hail_more", "hail_advance", "hail_defer",
        "hail_audio", "hail_audio_set",
    ),
    "sbs_utils.procedural.gui": (
        "hail_choice_strip", "hail_where_dropdown", "hail_view",
        "hail_panel_history", "hail_panel_icon", "hail_audio_checkbox",
    ),
}

_MODULES = {"sbs_utils.procedural.hail": HAIL, "sbs_utils.procedural.gui": GUI_PKG}


class MastNamespaceTests(unittest.TestCase):
    def test_every_name_a_console_calls_is_reachable(self):
        for mod_name, names in CALLED_FROM_MAST.items():
            module = _MODULES[mod_name]
            for name in names:
                self.assertTrue(hasattr(module, name),
                                f"{name} is not reachable from {mod_name} - a .mast "
                                f"file naming it would raise only when a console renders")

    def test_every_name_a_console_calls_is_a_FUNCTION(self):
        # import_python_module walks getmembers(module, isfunction). A constant is
        # never exported, however public it looks.
        for mod_name, names in CALLED_FROM_MAST.items():
            module = _MODULES[mod_name]
            for name in names:
                self.assertTrue(isfunction(getattr(module, name)),
                                f"{name} must be a FUNCTION: only functions become "
                                f"MAST globals, so a constant is invisible to .mast")

    def test_the_gui_half_is_re_exported_from_the_package(self):
        # The export filter keeps a function only when its __module__ sits under the
        # imported package name, so a gui helper must be visible on the package.
        for name in CALLED_FROM_MAST["sbs_utils.procedural.gui"]:
            fn = getattr(GUI_PKG, name)
            self.assertIn("sbs_utils.procedural.gui", fn.__module__, name)

    def test_nothing_generic_leaks_into_the_flat_namespace(self):
        # One flat namespace, silently overwritten by the last writer. A leading
        # underscore is NOT private here - `_now` collided with gui/camera.py once.
        import sbs_utils.procedural.gui.hail_gui as HAIL_GUI
        for module in (HAIL, HAIL_GUI):
            for name, obj in vars(module).items():
                if not isfunction(obj) or obj.__module__ != module.__name__:
                    continue
                self.assertTrue(name.startswith("hail_") or name.startswith("_hail"),
                                f"{module.__name__}.{name} is neither hail_* nor "
                                f"_hail_*, so it can collide in the MAST namespace")


if __name__ == "__main__":
    unittest.main()
