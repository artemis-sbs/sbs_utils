"""Drive LegendaryMissions' REAL console picker headless. INCOMPLETE - see BLOCKED below.

WHY IT IS WANTED. Rewriting the ship binding in `common_console_select.mast` has a failure
mode nothing else catches: the screen builds EMPTY, or a console attaches to the wrong
ship. No unit test sees it (MAST plus widgets), `--test` never opens the picker, and a
screenshot is not reliable evidence. Until this works, the listbox half of that rewrite
should not land.

WHAT ALREADY WORKS, so it need not be rediscovered:

  * boot order: `_load_libs` + mock sbs + `sys.modules["script"]` + BOTH `fs.exe_dir` and
    `fs.script_dir`, then the mast/story/procedural imports;
  * a tick that also calls `_drain_client_strings` - without it a connected client sits in
    `client_main` forever, its three client-string round trips never resolving;
  * sides and player ships. `start_server` does NOT run under this bootstrap, so the two
    things the picker needs are driven directly: `signal_emit("create_sides")` and a seeded
    roster spawned through the real `player_ensure`. Verified - sides come back as
    {tsn, raider, civ} and eight ships exist.

BLOCKED ON: the client never gets a page at all. Measured tick by tick after
`register_client` plus a `client_connect` event, `CID in Gui.clients` is False from t+1
through t+40 - nothing is ever pushed for it, even though `Gui.client_start_page_class` is
set. Start at `Gui.push` (gui.py ~437) and work backwards to whoever should call it.

FIXED ALONG THE WAY, and worth knowing on its own: `Gui.clients` maps client_id ->
**GuiClient**, NOT -> page. The live page is the top of that object's `page_stack`. Reading
the dict value as a page walks a GuiClient for widgets it can never have, so the harness
reported "the picker built nothing" as its verdict on everything - worse than useless for a
tool whose whole job is telling a blank screen from a working one. `client_page()` reads
the stack now.

Two known-harmless noises: `sim.set_diplomacy_color` raises inside the create_sides route
(the MAST-level `sim` is None here; the sides themselves load fine), and the ship picker
raises IndexError if reached with no player ships - the symptom of the bootstrap gap above,
not a library defect.

Recipe this came from: the `reference_drive_console_picker_headless` memory.

    python -m cosmos_dev.tools.drive_picker [--profile tng_all]
"""
import os
import sys

MISSIONS_ROOT = r"E:\a\Cosmos-dev\data\missions"
PROJECT = os.path.join(MISSIONS_ROOT, "sbs_utils")
MISSION = os.path.join(MISSIONS_ROOT, "LegendaryMissions")

sys.path.insert(0, PROJECT)

PROFILE = None
if "--profile" in sys.argv:
    PROFILE = sys.argv[sys.argv.index("--profile") + 1]

from cosmos_dev.mission_runner import _load_libs, _drain_client_strings  # noqa: E402
_load_libs(MISSION, MISSIONS_ROOT, use_working_tree=True)

import cosmos_dev.mock.sbs as sbs  # noqa: E402
sys.modules["script"] = sys.modules.get("__main__")

from sbs_utils import fs  # noqa: E402
fs.exe_dir = MISSIONS_ROOT
fs.script_dir = MISSION

from sbs_utils.mast import core_nodes            # noqa: F401,E402
from sbs_utils.mast_sbs import story_nodes       # noqa: F401,E402
from sbs_utils.mast_sbs import mast_sbs_procedural  # noqa: F401,E402
from sbs_utils.mast_sbs.maststorypage import StoryPage  # noqa: E402
from sbs_utils.helpers import FrameContext, Context, FakeEvent  # noqa: E402
from sbs_utils.agent import Agent  # noqa: E402
from sbs_utils.handlerhooks import cosmos_event_handler  # noqa: E402
from sbs_utils.gui import Gui  # noqa: E402
from sbs_utils.procedural.settings import settings_seed_apply  # noqa: E402

if PROFILE:
    os.environ["COSMOS_PROFILE"] = PROFILE
    try:
        from sbs_utils.procedural.command_line import set_command_line
        set_command_line(["engine.exe", f"profile={PROFILE}", "map=siege"])
    except Exception as exc:                      # pragma: no cover - diagnostic only
        print(f"[harness] could not set command line: {exc}")

settings_seed_apply(7)
sim = sbs.create_new_sim()
Agent.SHARED.set_inventory_value("sim", sim)
FrameContext.context = Context(sim, sbs, FakeEvent())


class _MissionPage(StoryPage):
    story_file = os.path.join(MISSION, "story.mast")


Gui.server_start_page_class(_MissionPage)
Gui.client_start_page_class(_MissionPage)

CID = 0x8080000000000001


def tick(n=1):
    for _ in range(n):
        sbs.sim._time_tick_counter += 1
        cosmos_event_handler(sim, FakeEvent(0, "mission_tick"))
        _drain_client_strings(sim, cosmos_event_handler, FakeEvent)


def walk(page):
    """Every (tag, display text) on a client's page, depth-first."""
    from sbs_utils.pages.layout.layout import Column
    found = []

    def rec(node, depth=0):
        for attr in ("layouts", "rows", "columns"):
            kids = getattr(node, attr, None)
            if kids:
                for k in kids:
                    rec(k, depth + 1)
        tag = getattr(node, "tag", None)
        if tag is not None:
            val = getattr(node, "value", None)
            found.append((str(tag), type(node).__name__, str(val)[:70]))
    rec(page)
    return found


def client_page():
    """The page a client is CURRENTLY presenting.

    Gui.clients maps client_id -> GuiClient, NOT -> page. The GuiClient holds a
    `page_stack` and the live page is its top. Reading the dict value as a page is what
    made this harness report "the picker built nothing" when the picker was fine - it was
    walking a GuiClient for widgets it never has.
    """
    gui = Gui.clients.get(CID)
    if gui is None:
        return None
    stack = getattr(gui, "page_stack", None) or []
    return stack[-1] if stack else None


def report(label):
    print(f"\n===== {label} =====")
    ship = sbs.get_ship_of_client(CID)
    print(f"  client ship id : {ship}")
    obj = None
    if ship:
        from sbs_utils.procedural.query import to_object
        obj = to_object(ship)
    if obj is not None:
        print(f"  ship name/hull : {obj.name} / {obj.art_id} / side={obj.side}")
    else:
        print("  ship name/hull : <none>")
    try:
        from sbs_utils.procedural.player_roster import (
            player_roster_slot_of_client, player_roster_resolve, player_roster_active_count)
        slot = player_roster_slot_of_client(CID)
        print(f"  roster slot    : {slot}"
              + (f"  resolves to {player_roster_resolve(slot)}" if slot is not None else ""))
        print(f"  active slots   : {player_roster_active_count()}")
    except Exception as exc:
        print(f"  roster         : n/a ({exc})")
    page = client_page()
    widgets = walk(page) if page is not None else []
    print(f"  widgets on page: {len(widgets)}")
    for t, kind, v in widgets[:14]:
        print(f"      {t:<28} {kind:<14} {v}")
    return len(widgets)


print("[harness] booting story...")
tick(40)

# The server-boot path (server_console `start_server`) does not run under this bootstrap,
# so the two things the picker depends on are driven directly. Both are the REAL code -
# the route LM registers, and the roster it would have built - so what the picker is handed
# is what it would be handed in a game.
from sbs_utils.procedural.signal import signal_emit  # noqa: E402
from sbs_utils.procedural.sides import side_keys_set  # noqa: E402
from sbs_utils.procedural.player_roster import player_roster_seed, player_roster  # noqa: E402
from sbs_utils.procedural.spawn import player_ensure  # noqa: E402
from sbs_utils.procedural.roles import add_role  # noqa: E402
from sbs_utils.procedural.settings import settings_get_defaults  # noqa: E402

signal_emit("create_sides")
tick(2)
if not side_keys_set():
    from sbs_utils.procedural.amd_sides import sides_load_amd
    sides_load_amd("maps/sides.amd")
print(f"[harness] sides: {sorted(side_keys_set())}")

roster = settings_get_defaults().get("PLAYER_LIST") or []
player_roster_seed(roster)
for _rec in player_roster():
    _sid = player_ensure(_rec["slot"], (_rec["slot"] - 3.5) * 2000, 0, 2000,
                         _rec["ship"], _rec["name"], _rec["side"])
    if _sid is not None:
        add_role(_sid, "default_player_ship")
tick(2)
from sbs_utils.procedural.query import to_id_list  # noqa: E402
from sbs_utils.procedural.roles import role  # noqa: E402
print(f"[harness] player ships: {len(to_id_list(role('__player__')))}")

print("[harness] connecting client...")
sbs.register_client(CID)
cosmos_event_handler(sim, FakeEvent(client_id=CID, tag="client_connect"))
tick(40)

n = report("PICKER, as built")

if n == 0:
    print("\n!! THE PICKER BUILT NOTHING - that is the failure this harness exists to catch")
    sys.exit(1)

print("\n[harness] OK - picker painted %d widgets" % n)
