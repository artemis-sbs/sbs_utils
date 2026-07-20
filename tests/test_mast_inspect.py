"""Live-inspection tests (Phase: Signal Tracer). Prove the InspectionBus + the
signal tap: a mission that emits a signal publishes a typed event, the bus is
inert with no sink, and the tap cleanly restores.
"""
from sbs_utils.fs import test_set_exe_dir
test_set_exe_dir()

import unittest
from tests.test_mast_debug import build_runner
from cosmos_dev.mast_inspect import InspectionBus, SignalTap, WorldTap, GuiTap, BrainTap, _json_safe

SIG_CODE = """
logger(var="output")
sub_task_schedule(listen)
signal_emit("test_sig", {"say": "hi"})
await delay_test(5)

=== listen
signal_register("test_sig", respond)
yield idle

=== respond
log("got {say}")
yield idle
"""


class TestSignalTap(unittest.TestCase):
    def tearDown(self):
        # Ensure no wrapper lingers on the class between tests.
        from sbs_utils.mast.mast import Mast
        base = getattr(Mast.signal_emit, "_mast_orig", None)
        if base is not None:
            Mast.signal_emit = base

    def test_bus_inert_without_sink(self):
        bus = InspectionBus()
        self.assertFalse(bus.active)
        bus.publish("signal", {"name": "x"})   # no sink -> no-op, no error

    def test_signal_tap_publishes_on_emit(self):
        got = []
        bus = InspectionBus()
        bus.subscribe(got.append)
        tap = SignalTap(bus).install()
        try:
            errors, runner, mast = build_runner(SIG_CODE)
            self.assertEqual(errors, [])
            runner.start_task("main")            # runs main -> emits test_sig
            for _ in range(8):
                runner.tick()
            sigs = [e for e in got if e["kind"] == "signal"]
            self.assertTrue(sigs, "no signal events captured")
            payloads = [e["payload"] for e in sigs]
            hit = next(p for p in payloads if p["name"] == "test_sig")
            self.assertEqual(hit["data"], {"say": "hi"})   # json-safe copy
            self.assertGreaterEqual(hit["routes"], 1)      # the listener registered
            # source locations: the emitter (the signal_emit call) + the route(s)
            self.assertIn("emitter", hit)
            self.assertIn("route_list", hit)
            self.assertIsInstance(hit["route_list"], list)
            self.assertTrue(hit["emitter"] and hit["emitter"].get("line"),
                            f"no emitter location: {hit['emitter']}")
            self.assertTrue(any(r.get("line") and r.get("path") for r in hit["route_list"]),
                            f"no route locations: {hit['route_list']}")
            # events carry a monotonic seq
            self.assertEqual([e["seq"] for e in got], sorted(e["seq"] for e in got))
        finally:
            tap.uninstall()

    def test_inert_when_no_sink_even_if_installed(self):
        bus = InspectionBus()                    # not subscribed
        tap = SignalTap(bus).install()
        try:
            errors, runner, mast = build_runner(SIG_CODE)
            runner.start_task("main")
            for _ in range(4):
                runner.tick()
            # nothing to assert on the (empty) sink; the point is it didn't raise
        finally:
            tap.uninstall()

    def test_uninstall_restores(self):
        from sbs_utils.mast.mast import Mast
        original = Mast.signal_emit
        tap = SignalTap(InspectionBus()).install()
        self.assertIsNot(Mast.signal_emit, original)     # patched
        tap.uninstall()
        self.assertIs(Mast.signal_emit, original)        # restored

    def test_json_safe(self):
        self.assertEqual(_json_safe({"a": 1, "b": [1, "x"]}), {"a": 1, "b": [1, "x"]})
        self.assertIsInstance(_json_safe(object()), str)  # non-serializable -> repr


class TestWorldTap(unittest.TestCase):
    def setUp(self):
        from cosmos_dev.mock import sbs
        from sbs_utils.spaceobject import SpaceObject
        from sbs_utils.helpers import FrameContext, Context, FakeEvent
        SpaceObject.clear()
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())

    def test_snapshot_lists_space_objects(self):
        from sbs_utils.objects import Npc, PlayerShip
        from sbs_utils.procedural.roles import add_role
        PlayerShip().spawn(0, 0, 0, "Console", "tsn", "Battle Cruiser")
        raider = Npc().spawn(500, 0, 0, "Raider1", "raider", "Battleship", "behav_npcship")
        add_role(raider, "enemy")

        snap = WorldTap().snapshot()
        by_name = {a["name"]: a for a in snap["agents"]}
        self.assertIn("Console", by_name)
        self.assertIn("Raider1", by_name)
        self.assertEqual(by_name["Console"]["kind"], "player")
        self.assertEqual(by_name["Console"]["side"], "tsn")
        self.assertEqual(by_name["Raider1"]["kind"], "npc")
        self.assertEqual(by_name["Raider1"]["side"], "raider")
        self.assertIn("enemy", by_name["Raider1"]["roles"])
        # each agent carries a diplomacy verdict (the value depends on live side
        # relationships; here we assert the field is present and boolean).
        self.assertIn("enemy", by_name["Console"])
        self.assertIsInstance(by_name["Console"]["enemy"], bool)

    def test_poll_thread_publishes(self):
        from sbs_utils.objects import PlayerShip
        PlayerShip().spawn(0, 0, 0, "Console", "tsn", "Battle Cruiser")
        got = []
        bus = InspectionBus()
        bus.subscribe(got.append)
        tap = WorldTap(bus, interval=0.02).install()
        try:
            import time
            time.sleep(0.12)
            agent_events = [e for e in got if e["kind"] == "agents"]
            self.assertTrue(agent_events, "poll thread published nothing")
            names = [a["name"] for a in agent_events[-1]["payload"]["agents"]]
            self.assertIn("Console", names)
        finally:
            tap.uninstall()


class TestGuiTap(unittest.TestCase):
    def setUp(self):
        from cosmos_dev.mock import sbs
        from sbs_utils.helpers import FrameContext, Context, FakeEvent
        self.sbs = sbs
        FrameContext.context = Context(None, sbs, FakeEvent())

    def test_frame_capture_builds_widget_list(self):
        got = []
        bus = InspectionBus()
        bus.subscribe(got.append)
        tap = GuiTap(bus).install()
        try:
            self.sbs.send_gui_clear(0, "root")
            self.sbs.send_gui_button(0, "root", "btn1", "style", 0.0, 0.0, 1.0, 0.5)
            self.sbs.send_gui_text(0, "root", "txt1", "note", 0.0, 0.5, 1.0, 1.0)
            self.sbs.send_gui_complete(0, "root")

            widget_events = [e for e in got if e["kind"] == "widgets"]
            self.assertTrue(widget_events, "no widgets snapshot published on complete")
            widgets = widget_events[-1]["payload"]["widgets"]
            by_tag = {w["tag"]: w for w in widgets}
            self.assertIn("btn1", by_tag)
            self.assertIn("txt1", by_tag)
            self.assertEqual(by_tag["btn1"]["type"], "button")
            self.assertEqual(by_tag["btn1"]["parent"], "root")
            self.assertEqual(by_tag["btn1"]["rect"], [0.0, 0.0, 1.0, 0.5])
        finally:
            tap.uninstall()

    def test_uninstall_restores(self):
        orig = self.sbs.send_gui_button
        tap = GuiTap().install()
        self.assertIsNot(self.sbs.send_gui_button, orig)   # wrapped
        tap.uninstall()
        self.assertIs(self.sbs.send_gui_button, orig)      # restored


class TestBrainTap(unittest.TestCase):
    def setUp(self):
        from cosmos_dev.mock import sbs
        from sbs_utils.spaceobject import SpaceObject
        from sbs_utils.helpers import FrameContext, Context, FakeEvent
        SpaceObject.clear()
        sbs.create_new_sim()
        FrameContext.context = Context(sbs.sim, sbs, FakeEvent())

    def _build_brain(self):
        from sbs_utils.objects import Npc
        from sbs_utils.procedural.brain import Brain, BrainType
        from sbs_utils.procedural.inventory import set_inventory_value
        from sbs_utils.mast.pollresults import PollResults
        raider = Npc().spawn(500, 0, 0, "Raider1", "raider", "Battleship", "behav_npcship")
        aid = raider.id
        root = Brain(aid, "SEL root", None, 0, BrainType.Select)
        patrol = Brain(aid, "patrol", None, 0, BrainType.Simple)
        attack = Brain(aid, "attack", None, 0, BrainType.Simple)
        root.children = [patrol, attack]
        root._active = attack
        attack._result = PollResults.BT_SUCCESS
        set_inventory_value(aid, "__BRAIN__", root)
        return aid

    def test_snapshot_walks_tree(self):
        self._build_brain()
        snap = BrainTap().snapshot()
        self.assertEqual(len(snap["brains"]), 1)
        b = snap["brains"][0]
        self.assertEqual(b["name"], "Raider1")
        self.assertFalse(b["paused"])
        self.assertEqual(b["tree"]["type"], "select")
        kids = b["tree"]["children"]
        by_label = {k["label"]: k for k in kids}
        self.assertIn("patrol", by_label)
        self.assertIn("attack", by_label)
        self.assertEqual(by_label["attack"]["type"], "simple")
        self.assertTrue(by_label["attack"].get("active"))     # the active child is marked
        self.assertNotIn("active", by_label["patrol"])
        # BT_SUCCESS aliases OK_END (both == 99); .name yields the canonical alias.
        self.assertIn(by_label["attack"]["result"], ("BT_SUCCESS", "OK_END"))

    def test_poll_thread_publishes(self):
        self._build_brain()
        got = []
        bus = InspectionBus()
        bus.subscribe(got.append)
        tap = BrainTap(bus, interval=0.02).install()
        try:
            import time
            time.sleep(0.12)
            brain_events = [e for e in got if e["kind"] == "brains"]
            self.assertTrue(brain_events, "poll thread published nothing")
            names = [b["name"] for b in brain_events[-1]["payload"]["brains"]]
            self.assertIn("Raider1", names)
        finally:
            tap.uninstall()


if __name__ == "__main__":
    unittest.main()
