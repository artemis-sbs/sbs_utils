"""Names a `.mast` calls must actually resolve to.

MAST replaces `__builtins__` with MastGlobals' table, so a library function is callable
from a script ONLY if its module was registered with `MastGlobals.import_python_module`.
A name that was not is a bare `NameError` at RUNTIME, in whatever route happens to call
it - and a route that a headless conformance run never enters never reports it.

That is exactly how the urge functions shipped: the library only ever called them from
PYTHON (Open Universe installs a passenger's urges from `universe_lifeforms.py`), so
nothing noticed that `urge_teach_note` and `urges_install_on` were unreachable from a
`.mast` until a mission tried.

This pins the names missions call, so adding a module without registering it fails here
rather than on a bridge.

    python -m unittest tests.test_mast_reachable_names
"""
import sys
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import sbs_utils.mast_sbs.story_nodes  # import first to break a circular import
from cosmos_dev.mock import sbs as _mock_sbs

# mast_sbs_procedural does `import sbs` at module scope - the engine module, which does
# not exist off-engine. The mock stands in, exactly as the mission runner arranges.
sys.modules.setdefault("sbs", _mock_sbs)
import sbs_utils.mast_sbs.mast_sbs_procedural  # noqa: F401,E402  registers the modules
from sbs_utils.mast.mast_globals import MastGlobals  # noqa: E402


#: Called from a .mast in LegendaryMissions, Open Universe or StormsBeacon.
REQUIRED = (
    # offers - the board's route condition and the badge
    "offer_count", "offer_count_here", "offers", "offers_for_object",
    "offer_register", "offer_record", "offer_clear",
    "offer_board_count_here", "quest_offers_tab_items", "quest_offers_tab_sig",
    "quest_offers_title", "quest_tab_items", "quest_tab_accept",
    # urges - the teaching nudges and their ledger
    "urge_add", "urge_record", "urge_teach_note", "urge_taught",
    "urges_install_on", "urges_from_section",
    # hails - the closing echo
    "hail_echo_enable", "hail_echo_text",
    # comms - the selection-title decoration
    "comms_selection_annotator",
)


class ReachableNameTests(unittest.TestCase):
    def test_every_required_name_resolves(self):
        missing = [n for n in REQUIRED if n not in MastGlobals.globals]
        self.assertEqual(missing, [], f"not reachable from MAST: {missing}")

    def test_private_helpers_are_not_exported(self):
        """A leading underscore is private - it must not reach the flat namespace, where
        it could collide with a mission's own variable of that name. (A28's `_mine`
        turned autoplay's `_mine = ...` into a compile error that emptied a whole story.)

        Dunders are excluded: `__name__` and `__build_class__` are what the eval
        environment is built out of, not exported helpers.
        """
        leaked = sorted(k for k in MastGlobals.globals
                        if k.startswith("_") and not k.startswith("__"))
        self.assertEqual(leaked, [], f"private names exported: {leaked[:10]}")


if __name__ == "__main__":
    unittest.main()
