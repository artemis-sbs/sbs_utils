"""A deleted agent must not hand out its engine handles any more.

An Agent instance routinely outlives the C++ object it describes - a route task
holds SPAWNED for its whole life, a console task snapshots a roster into a list,
a Modifier stores its target. `_data_set` / `_engine_object` are raw pointers
into memory the engine frees on delete, so a write through a stale instance
lands in whatever now owns that block.

That is what crashed the engine on 2026-08-23: three dumps, all faulting in
ObjectDataBlob::Set on a std::map whose head pointer had been recycled into
other data (zeroes, an ASCII string, packed ints). Dropping the id out of
Agent.all was never enough, because a caller holding the instance never consults
Agent.all - so `->END if to_object(x) is None` was silently inert whenever x was
an object rather than an id.
"""
import unittest

from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

from cosmos_dev.mock import sbs
from sbs_utils.agent import Agent, CloseData, SpawnData
from sbs_utils.helpers import FrameContext, Context
from sbs_utils.spaceobject import SpaceObject
from sbs_utils.procedural.query import (to_object, to_object_list, to_agent_list,
                                        to_set, to_blob)
from sbs_utils.procedural.spawn import npc_spawn


class FakeEvent:
    def __init__(self):
        self.client_id = 0
        self.tag = ""
        self.sub_tag = ""
        self.parent_id = 0
        self.origin_id = 0
        self.selected_id = 0
        self.value_tag = ""
        self.extra_tag = ""
        self.extra_extra_tag = ""
        self.sub_float = 0.0
        self.source_point = None
        self.event_time = 0


class TestStaleHandle(unittest.TestCase):
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        SpaceObject.clear()

    def _spawn(self, name="Scout"):
        return npc_spawn(0, 0, 0, name, "tsn", "tsn_scout", "behav_npcship")

    def test_live_agent_resolves_and_has_a_blob(self):
        """The control. Without this the rest could pass for the wrong reason."""
        spawned = self._spawn()
        obj = to_object(spawned.id)
        self.assertIsNotNone(obj)
        self.assertIsNotNone(obj.data_set)
        self.assertIsNotNone(to_blob(obj))

    def test_to_object_on_a_deleted_agent_is_none(self):
        """The guard every mission writes. It used to return the dead instance."""
        spawned = self._spawn()
        obj = to_object(spawned.id)
        obj.delete_object()
        self.assertIsNone(to_object(obj))

    def test_deleted_agent_drops_its_engine_handles(self):
        spawned = self._spawn()
        obj = to_object(spawned.id)
        self.assertIsNotNone(obj.data_set)
        obj.delete_object()
        self.assertIsNone(obj.data_set)
        self.assertIsNone(obj.engine_object)

    def test_to_blob_on_a_deleted_agent_is_none(self):
        """`blob = to_blob(x)` then `blob.set(...)` is the crashing shape."""
        spawned = self._spawn()
        obj = to_object(spawned.id)
        obj.delete_object()
        self.assertIsNone(to_blob(obj))

    def test_to_blob_on_a_deleted_spawn_data_is_none(self):
        """SpawnData caches the raw blob at spawn and used to return it blind."""
        spawned = self._spawn()
        self.assertIsNotNone(to_blob(spawned))
        to_object(spawned.id).delete_object()
        self.assertIsNone(to_blob(spawned))
        self.assertIsNone(to_object(spawned))

    def test_to_object_on_a_deleted_close_data_is_none(self):
        """CloseData caches py_object the same way closest() hands it out."""
        spawned = self._spawn()
        obj = to_object(spawned.id)
        close = CloseData(obj.id, obj, 100.0)
        self.assertIsNotNone(to_object(close))
        obj.delete_object()
        self.assertIsNone(to_object(close))

    def test_deleting_by_id_also_tombstones_the_instance(self):
        """Agent.remove_id is the other removal path (grid objects use it)."""
        spawned = self._spawn()
        obj = to_object(spawned.id)
        Agent.remove_id(obj.id)
        self.assertIsNone(to_object(obj))
        self.assertIsNone(obj.data_set)

    def test_respawn_rearms_a_reused_instance(self):
        """add() must clear the tombstone or a recycled instance stays dead."""
        spawned = self._spawn()
        obj = to_object(spawned.id)
        obj.delete_object()
        self.assertIsNone(to_object(obj))
        obj.add()
        self.assertIs(to_object(obj), obj)

    def test_live_agents_cost_no_instance_attribute(self):
        """_alive must stay a CLASS attribute for live agents - this sits on the
        per-tick query path and object_exists regressed measurably once from
        doing real work here."""
        spawned = self._spawn()
        obj = to_object(spawned.id)
        self.assertNotIn("_alive", vars(obj))
        obj.delete_object()
        self.assertIn("_alive", vars(obj))


if __name__ == "__main__":
    unittest.main()


class _RecordingSbs:
    """Captures send_client_widget_rects calls."""
    def __init__(self):
        self.rects = []

    def send_client_widget_rects(self, client_id, widget, *coords):
        self.rects.append((client_id, widget, coords))


class TestRetireDroppedEngineWidgets(unittest.TestCase):
    """An engine widget cannot be un-declared, so one dropped from a console's
    widget list carries on drawing against whatever object the console was last
    pointed at. When that object has been deleted the engine walks freed memory -
    a client died in ViewGridObjectListDraw that way, two minutes after the
    mission ended, still drawing the Engineering grid list for a dead ship.

    Parking is only safe for a widget we can put BACK, which means one a script
    placed and whose rect we therefore recorded. Everything here turns on that.
    """
    def setUp(self):
        # _retire_dropped_engine_widgets remembers what it parked and where each
        # widget was placed, so these cases are not independent without this.
        from sbs_utils.mast_sbs.maststorypage import StoryPage
        StoryPage._forget_parked_widgets()

    @staticmethod
    def _place(widget, client_id=7, rect=(10, 20, 30, 40)):
        """Stand in for ConsoleWidget._present / gui_panel_*_show."""
        from sbs_utils.gui import Gui
        Gui.record_widget_rect(client_id, widget, *rect)

    def _retire(self, prev, current, client_id=7):
        from sbs_utils.mast_sbs.maststorypage import StoryPage
        rec = _RecordingSbs()
        StoryPage._retire_dropped_engine_widgets(prev, current, client_id, rec)
        return [w for _cid, w, _c in rec.rects]

    def _retire_rects(self, prev, current, client_id=7):
        from sbs_utils.mast_sbs.maststorypage import StoryPage
        rec = _RecordingSbs()
        StoryPage._retire_dropped_engine_widgets(prev, current, client_id, rec)
        return {w: c for _cid, w, c in rec.rects}

    def test_widgets_dropped_from_the_list_are_pushed_offscreen(self):
        self._place("ship_internal_view")
        self._place("grid_object_list")
        retired = self._retire(("engineering", "ship_internal_view^grid_object_list"),
                               ("", ""))
        self.assertCountEqual(retired, ["ship_internal_view", "grid_object_list"])

    def test_widgets_still_declared_are_left_alone(self):
        self._place("ship_internal_view")
        self._place("grid_object_list")
        retired = self._retire(("engineering", "ship_internal_view^grid_object_list"),
                               ("helm", "ship_internal_view"))
        self.assertEqual(retired, ["grid_object_list"])

    def test_no_previous_list_retires_nothing(self):
        self._place("2dview")
        self.assertEqual(self._retire(None, ("helm", "2dview")), [])

    def test_unchanged_widgets_retire_nothing(self):
        self._place("2dview")
        self.assertEqual(self._retire(("helm", "2dview"), ("weapons", "2dview")), [])

    def test_offscreen_rect_is_outside_the_visible_area(self):
        from sbs_utils.mast_sbs.maststorypage import StoryPage
        self._place("grid_object_list")
        rec = _RecordingSbs()
        StoryPage._retire_dropped_engine_widgets(("engi", "grid_object_list"), ("", ""), 7, rec)
        _cid, _w, coords = rec.rects[0]
        self.assertTrue(all(c >= 100 for c in coords), coords)

    # --- a widget that COMES BACK has to be un-parked, WHERE IT WAS ----------
    # Parking is permanent: re-declaring a widget in the list does not restore
    # the rect we pushed offscreen. A main screen toggles 3dview <-> 2dview every
    # time the viewer goes Tactical and back, so a parked 3D view never came back
    # on the way out - "it gets stuck on tactical".
    def test_a_widget_that_returns_is_put_back_where_it_was(self):
        self._place("3dview", rect=(0, 5, 100, 95))
        self._place("2dview", rect=(0, 5, 71, 95))
        # into tactical: the 3D view is parked
        parked = self._retire_rects(("normal_main", "3dview^ship_data"),
                                    ("normal_main", "2dview^ship_data"))
        self.assertIn("3dview", parked)
        # back out: it must be put back at its OWN rect, not at a guess
        back = self._retire_rects(("normal_main", "2dview^ship_data"),
                                  ("normal_main", "3dview^ship_data"))
        self.assertIn("3dview", back, "the 3D view was left parked offscreen")
        self.assertEqual(back["3dview"], (0, 5, 100, 95, 0, 5, 100, 95))
        self.assertIn("2dview", back, "the 2D view should now be the parked one")

    def test_a_widget_never_parked_is_not_re_rected(self):
        """Only un-park what we parked - a widget the console placed itself keeps
        the rect its own layout gave it."""
        self._place("3dview")
        back = self._retire_rects(("normal_main", "ship_data"),
                                  ("normal_main", "3dview^ship_data"))
        self.assertNotIn("3dview", back)

    def test_parking_is_tracked_per_console(self):
        self._place("3dview", client_id=7)
        self._place("3dview", client_id=8)
        self._place("2dview", client_id=7)
        self._place("2dview", client_id=8)
        self._retire_rects(("normal_main", "3dview"), ("normal_main", "2dview"), 7)
        back = self._retire_rects(("normal_main", "2dview"), ("normal_main", "3dview"), 8)
        self.assertNotIn("3dview", back, "one console's parking un-parked another's")

    # --- and the reason all of the above turns on a recorded rect ------------

    def test_engine_placed_widgets_are_never_touched(self):
        """THE FIELD REPORT. Weapons leaves six of its widgets to the engine's own
        layout - nothing sends them a rect, so we have nowhere to put them back.

        Clicking the Upgrades tab drops the whole widget list ("upgrade", ""), and
        clicking the back tab re-declares it. This used to park all of them and
        then un-park each one to the FULL CONSOLE, stacking every control over the
        whole screen. Reported as "the client console will be hosed", repro every
        time, on Weapons and Helm - the only two consoles with engine-placed
        widgets.
        """
        weapons = ("normal_weap",
                   "weapon_2d_view^radar_zoom_ctrl^weapon_control^weap_beam_freq"
                   "^weap_beam_speed^weap_torp_conversion^ship_data^shield_control"
                   "^main_screen_control")
        # The two LegendaryMissions actually places, plus ship_data from the panel.
        for widget in ("radar_zoom_ctrl", "weapon_2d_view", "ship_data"):
            self._place(widget)

        to_tab = self._retire_rects(weapons, ("upgrade", ""))
        self.assertCountEqual(to_tab, ["radar_zoom_ctrl", "weapon_2d_view", "ship_data"],
                              "parked a widget it cannot put back")

        back = self._retire_rects(("upgrade", ""), weapons)
        for widget in ("weapon_control", "weap_beam_freq", "weap_beam_speed",
                       "weap_torp_conversion", "shield_control", "main_screen_control"):
            self.assertNotIn(widget, back,
                             f"{widget} was moved without knowing where it belongs")

    def test_a_widget_its_owner_hid_is_left_where_the_owner_put_it(self):
        """ship_data while the info panel is on the log tab. gui_panel_ship_data_hide
        drops the placement record, so the un-park must not drag it back on screen
        over the tab the crew chose instead of it."""
        from sbs_utils.gui import Gui
        self._place("ship_data")
        self._retire_rects(("normal_weap", "ship_data"), ("upgrade", ""))
        Gui.forget_widget_rect(7, "ship_data")           # the panel hides it
        back = self._retire_rects(("upgrade", ""), ("normal_weap", "ship_data"))
        self.assertNotIn("ship_data", back)

    def test_both_rects_are_restored_not_just_one(self):
        """data/guiboxdata.txt gives every stock widget a DIFFERENT pair of rects
        and send_client_widget_rects takes both, so a console reproducing a stock
        placement sends two. Putting the widget back has to replay both, or the
        second one silently becomes a copy of the first."""
        from sbs_utils.gui import Gui
        # normal_helm throttle, verbatim
        Gui.record_widget_rect(7, "throttle", 0, 62, 10, 100, 0, 61, 5, 99)
        self._retire_rects(("normal_helm", "throttle"), ("upgrade", ""))
        back = self._retire_rects(("upgrade", ""), ("normal_helm", "throttle"))
        self.assertEqual(back["throttle"], (0, 62, 10, 100, 0, 61, 5, 99))

    def test_one_rect_still_fills_both_slots(self):
        """A caller that computed a single rect meant it for both."""
        from sbs_utils.gui import Gui
        Gui.record_widget_rect(7, "grid_control", 1, 2, 3, 4)
        self.assertEqual(Gui.widget_rect_of(7, "grid_control"), (1, 2, 3, 4, 1, 2, 3, 4))

    def test_a_hidden_widget_is_not_parked(self):
        """gui_widget_offscreen is a deliberate one-way park; nothing else should
        move that widget on the caller's behalf."""
        from sbs_utils.gui import Gui
        self._place("comms_2d_view")
        Gui.forget_widget_rect(7, "comms_2d_view")       # gui_widget_offscreen
        dropped = self._retire(("normal_comm", "comms_2d_view"), ("upgrade", ""))
        self.assertEqual(dropped, [])


class TestDeletedObjectSetters(unittest.TestCase):
    """The setters reach the engine object through space_object(), NOT through the
    guarded Agent.data_set property - set_name does `so.data_set.set("name_tag", ...)`
    on the ENGINE object's own blob. That bypass is how a server still died in
    ObjectDataBlob::Set with "name_tag" on the stack after the first round of guards.
    """
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        SpaceObject.clear()
        spawned = npc_spawn(0, 0, 0, "Scout", "tsn", "tsn_scout", "behav_npcship")
        self.obj = to_object(spawned.id)

    def test_space_object_is_none_once_deleted(self):
        self.assertIsNotNone(self.obj.space_object())
        self.obj.delete_object()
        self.assertIsNone(self.obj.space_object())

    def test_set_name_on_a_deleted_object_does_not_write(self):
        self.obj.delete_object()
        self.obj.name = "Renamed"      # must be a no-op, not a write to freed memory

    def test_set_art_id_on_a_deleted_object_does_not_write(self):
        self.obj.delete_object()
        self.obj.art_id = "tsn_battleship"

    def test_set_side_on_a_deleted_object_does_not_write(self):
        self.obj.delete_object()
        self.obj.side = "kralien"

    def test_pos_read_is_none_once_deleted(self):
        self.assertIsNotNone(self.obj.pos)
        self.obj.delete_object()
        self.assertIsNone(self.obj.pos)

    def test_pos_write_on_a_deleted_object_does_not_reposition(self):
        from sbs_utils.vec import Vec3
        self.obj.delete_object()
        self.obj.pos = Vec3(500, 0, 500)


class TestLoadoutSkipsDeletedShips(unittest.TestCase):
    """The start-of-game cull strips __player__ from unused slots and deletes them,
    but never removes default_player_ship - so that role alone, and any snapshot list
    taken before the cull, can still name ships that are gone. The loadout apply then
    writes .name/.art_id straight through to the engine object.
    """
    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        SpaceObject.clear()

    def test_a_deleted_ship_in_a_supplied_list_is_skipped(self):
        from sbs_utils.procedural.maps import player_loadout_apply_to_ships
        from sbs_utils.procedural.execution import set_shared_variable
        alive = to_object(npc_spawn(0, 0, 0, "Alive", "tsn", "tsn_scout", "behav_npcship").id)
        dead = to_object(npc_spawn(0, 0, 0, "Dead", "tsn", "tsn_scout", "behav_npcship").id)
        dead.delete_object()
        set_shared_variable("SHIP_LOADOUT", "")
        # Both in the snapshot; only the live one may be touched. The assertion that
        # matters is that this does not write through the dead one.
        player_loadout_apply_to_ships([alive, dead])


class ToObjectListTests(unittest.TestCase):
    """The LIST form has to refuse what the singular form refuses.

    `to_object_list` resolved through `Agent.resolve_py_object`, which does not consult
    `_alive` - so `to_object(x)` returned None for a deleted agent while
    `to_object_list([x])` handed it straight back. Every guard written as "resolve it, then
    use it" is only as good as the resolve.

    Not a use-after-free today: a dead agent's `data_set` is already None, so a write
    through one raises rather than reaching freed memory. This is the inconsistency, not
    the crash.
    """

    def setUp(self):
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())
        SpaceObject.clear()
        # The server's own agent, which Gui.present builds on the first server frame.
        self.server = Agent()
        self.server.id = 0
        self.server.add()

    def tearDown(self):
        # A leaked Agent.all[0] outlives this file.
        SpaceObject.clear()

    def _npc(self, x, name):
        return to_object(npc_spawn(x, 0, 0, name, "tsn", "tsn_scout", "behav_npcship"))

    def test_a_deleted_agent_is_filtered_from_the_list(self):
        dead = self._npc(0, "Doomed")
        dead.delete_object()
        self.assertIsNone(to_object(dead), "the singular form should already refuse it")
        self.assertEqual([], to_object_list([dead]),
                         "the list form handed back an agent the singular form refused")

    def test_live_agents_are_untouched(self):
        alive = self._npc(5000, "Alive")
        self.assertEqual([alive], to_object_list([alive]))

    def test_a_mixed_list_keeps_only_the_living(self):
        dead = self._npc(0, "Doomed")
        alive = self._npc(5000, "Alive")
        dead.delete_object()
        self.assertEqual([alive], to_object_list([dead, alive]))

    # ------------------------------------------------------------------
    # The OTHER axis of the same contract.
    #
    # Everything above pins the `_alive` half, and it held: the change that made
    # to_object_list resolve through to_object kept all three of those green. What it
    # ALSO did was inherit to_object's refusal of id 0 - and id 0 is the server's own
    # agent - so every write built on this list silently stopped reaching the server
    # console. Timers and counters ride set_inventory_value, so `start_counter(0, name)`
    # wrote nothing and read back None forever (LM #719).
    #
    # Nothing asserted that half, which is how half a contract was removed by a change
    # whose stated purpose was to strengthen the other half. Both halves live here now,
    # so the next person editing these resolvers reads both rules in one place.
    # ------------------------------------------------------------------

    def test_to_object_list_still_refuses_id_zero(self):
        """The line that must NOT move. to_object_list is the SPACE-OBJECT resolver, and
        for a space object 0 really does mean "no object" - `->END if to_object(x) is
        None` is everywhere in MAST. Fixing the server by resurrecting 0 here would
        start returning a console from object queries."""
        self.assertEqual([], to_object_list([0]))
        self.assertEqual([], to_object_list(to_set(0)))

    def test_to_agent_list_resolves_the_server(self):
        """The write-side twin, in the two shapes callers actually use: a bare id, and
        the set that add_role / link / set_inventory_value build."""
        self.assertEqual([self.server], to_agent_list(0))
        self.assertEqual([self.server], to_agent_list(to_set(0)))

    def test_to_agent_list_still_drops_a_deleted_agent(self):
        """Both rules at once - the assertion that was missing. Resolving the server
        must not cost the liveness guarantee, and vice versa."""
        dead = self._npc(0, "Doomed")
        alive = self._npc(5000, "Alive")
        dead.delete_object()
        self.assertEqual([self.server, alive], to_agent_list([0, dead, alive]))

    def test_neither_resolver_ever_returns_none(self):
        """A caller writes `for obj in to_..._list(x): obj.something()`. An unresolvable
        entry is dropped, never passed through as None."""
        dead = self._npc(0, "Doomed")
        dead.delete_object()
        unknown = 0x4000000000009999
        self.assertNotIn(None, to_object_list([dead, 0, unknown]))
        self.assertNotIn(None, to_agent_list([dead, 0, unknown]))

    def test_a_torn_down_server_is_dropped_by_to_agent_list(self):
        """Catches a future fix that special-cases 0 BEFORE the liveness rule instead of
        after it."""
        self.server.remove()
        self.assertEqual([], to_agent_list([0]))
