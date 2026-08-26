"""Goal-directed pilot for the mock test harness (dev-only).

WHAT THIS IS FOR. `--exercise` drives the world generically - select everything, hail
everything, shoot something. That is the right policy for a combat mission and close to
useless for a quest-driven one, where the content is gated behind a job the player has to
ACCEPT and then a specific act the player has to PERFORM. On Peacetime Remastered the
whole board (19 jobs, 4 multi-step arcs, a 5-child investigation) is unreachable without a
person, and the mission says so itself in a comment beside the unused `AUTO_ACCEPT_JOBS`
hook.

WHY THIS CAN BE MISSION-AGNOSTIC. Because a quest already declares what the player must
do. `quest_driver._COUNT_GOAL_KEYS` is the entire vocabulary - on_kill, on_scan, on_dock,
on_tow, on_collect, on_reach, on_signal - and each is a dict carrying an optional `role`
filter naming WHAT to do it to. So the pilot reads the live quest tree and derives the
action; it holds no per-mission knowledge and needs no per-mission script. The same code
drives a peacekeeping job board, a stealth-archaeology campaign and a siege.

FAITHFUL, NOT CHEATING. Every actuation here is the call the real interaction makes:

  * Accept is `quest_mark_active`, which is the ENTIRE body of `quest_tab_accept` - the
    Accept button does nothing else. Pressing the button is unreachable headless
    (`gui_queue_console_tabs` builds tab controls outside the tag map), so this is the
    same act by its only reachable name.
  * Scanning is `science_ensure_scan`, the same call the science console's scan completes.
  * Towing is `grav_tether_attach`, the same call the Weapons tether control makes.
  * Flying is `steerToDirD{X,Y,Z}` + `steeringToDirFlag` + `playerThrottle`, which is what
    the helm AI writes (see mock `_playership_drive`).

Nothing here teleports, refills, or grants. The one thing it deliberately does NOT do is
synthesize `on_signal`: that trigger exists precisely so a mission can define a beat of
its own, and firing the signal directly would test the harness rather than the mission.
Those goals are counted and REPORTED as unreachable instead - see `snapshot()`.

THE GOAL VERB IS THE TRIGGER, NOT THE ACTION - and on a real board most goals are
`on_signal`. Measured on Peacetime Remastered: of 19 accepted jobs, 12 complete on a
signal that the mission's own watcher (`pr_barge_watch`, `pr_mercy_watch`, ...) emits once
an object reaches a drop. The quest says `Done when: signal barge_delivered` and nowhere
says "tow the barge" - that sentence exists only in the prose a human reads. So goal-verb
dispatch alone reaches a minority of the board.

The answer is not to teach the pilot about barges. It is to have it exercise the game's
PHYSICAL VOCABULARY - tow something and drop it somewhere, fly to the places the mission
marked, pass over loose objects - and let whichever watcher is listening notice. That is
what a player does, it needs no mission knowledge, and the mission's own rules do the
vetoing: `grav_tether_attach` consults the mission's attach policy and returns None when
it says no. Those are the `_sweep_*` behaviors below, and they run for any ship a quest
goal has not otherwise claimed.

PORTABLE BY CONSTRUCTION, AND IT WAS NOT AT FIRST. The world layer here goes through the
library's own primitives - `role`, `to_object`, `object_exists`, `broad_test_around`,
`closest` - and never through `sbs.sim.space_objects`. That dict is MOCK-ONLY: the real
`sbs` module has no `sim` attribute at all and the real `sbs.simulation` has no
`space_objects`, so the first engine run of this pilot logged
`module 'sbs' has no attribute 'sim'` on every single tick and drove exactly nothing while
the verdict still said PASS. `pilot_steps` in the engine verdict exists so that failure can
never be silent again.

WHY IT ALSO SUPPRESSES COMBAT. Measured on Peacetime Remastered: the exerciser's staged
combat (shields to zero, heat to critical, an armed hostile teleported into range) killed
the player ship in ~7 sim-seconds, ending and restarting the mission nine times inside a
60-second run. Coverage 26.5%, comms routes 0/123. With combat off the same run survives,
reaches 35.5%, and covers 32/123 comms routes - and damage coverage is UNCHANGED at 29/34,
because the mission's own NPCs already fight. So a mission whose quests never ask for a
kill should not be having one staged for it. `wants_combat()` is that decision, and it is
derived from the quest goals rather than hardcoded.
"""
import math

from sbs_utils.helpers import FrameContext

# The goal vocabulary, mirrored from quest_driver._COUNT_GOAL_KEYS. Kept as a local
# tuple rather than imported because it is a private name there; `verify_goal_keys()`
# below fails loudly if the two ever drift, which is cheaper than a pilot that silently
# stops recognizing a goal the library added.
GOAL_KEYS = ("on_signal", "on_kill", "on_scan", "on_reach", "on_dock", "on_collect",
             "on_tow")

# Goals the pilot can actuate. `on_signal` is deliberately absent - see the module
# docstring.
DRIVABLE = ("on_kill", "on_scan", "on_reach", "on_dock", "on_collect", "on_tow")

_ARRIVE = 900.0          # how close "flown to it" counts as, in engine units
_TOW_DROP_RADIUS = 1500.0
# How many steps to keep chasing one candidate before ruling it out. A sweep with no
# patience never arrives; a sweep with unlimited patience chases one unreachable rock
# for the whole run.
_GIVE_UP_STEPS = 90
# How much empty space the ship wants around it before going to warp. At throttle 3
# it covers 1080 units a second, and a passive collision at that speed is ~5400
# damage - fatal. Generous, because being slow costs a test nothing and dying costs
# it the whole run.
# How far out to look for candidates. broad_test is a rectangle query, so this is a half-extent; generous
# enough to find work without asking the engine to walk the whole sector.
_SEARCH_REACH = 40000.0
_WARP_CLEARANCE = 6000.0


def verify_goal_keys():
    """Return the goal keys the library knows that this module does not.

    A quest goal the pilot does not recognize is invisible: the quest sits ACTIVE
    forever and the run reports it as merely unreached, which reads like a mission
    problem rather than a harness one. Called once at startup so the drift is a printed
    warning instead of a silent blind spot.
    """
    try:
        from sbs_utils.procedural.quest_driver import _COUNT_GOAL_KEYS
    except Exception:
        return ()
    return tuple(k for k in _COUNT_GOAL_KEYS if k not in GOAL_KEYS)


class QuestPilot:
    """Reads the live quest trees and drives the player ships toward their goals."""

    def __init__(self, sbs, accept="all", goals=True):
        self._sbs = sbs
        # "all" accepts every IDLE quest; a list/tuple accepts only those keys; None or
        # "none" accepts nothing (useful to prove a board is reachable the hard way).
        self._accept = accept
        self._goals = bool(goals)
        self.steps = 0
        self.errors = 0
        self.accepted = 0           # quests taken from IDLE to ACTIVE
        self.scans = 0
        self.tows = 0
        self.docks = 0
        self.flights = 0
        # Per-ship intent, so a tow or a transit persists across ticks instead of being
        # re-decided every step. Keyed by player id -> dict(kind=..., target=...).
        self._intent = {}
        self._unreachable = {}      # quest path -> the goal key we cannot synthesize
        self._warned_drift = False
        # World-sweep bookkeeping. Objects already hauled and points already visited are
        # remembered so the sweep moves on instead of polishing the same one forever.
        self._towed = set()
        self._visited = set()
        # Targets already scanned. Without this the scan goal re-scans the same contact
        # every step, reports "I acted", and MONOPOLIZES the ship - measured at 476 scans
        # and 0 tows in a 120-second run. A quest counts each distinct target once
        # (`quest_on_scan` keeps a `_scanned` list), so re-scanning advances nothing.
        self._scanned = set()
        self._sweep_rotor = 0
        self.visits = 0

    # -- context ---------------------------------------------------------------
    def _server_ctx(self):
        try:
            return FrameContext.server_task
        except Exception:
            # The property reaches through `Agent.get(0).page.gui_task` unguarded; a
            # half-built server page must not take the tick down with it.
            return None

    def _sim(self):
        """The live simulation, the way the shipped library gets it.

        NOT `sbs.sim` - that is a mock-only convenience. In the engine the sim arrives on
        the event context.
        """
        try:
            return FrameContext.context.sim
        except Exception:
            return None

    def _nearby(self, pid, reach, broad_type=0xffff):
        """IDs around a ship, via the engine's own broad-phase query.

        `broad_test_around` is the portable "what is near me" primitive - it calls
        `sbs.broad_test`, which exists in both the engine and the mock. It takes a
        rectangle in X/Z, so `reach` is a half-extent.
        """
        try:
            from sbs_utils.procedural.space_objects import broad_test_around
            return broad_test_around(pid, reach * 2, reach * 2, broad_type)
        except Exception:
            return set()

    # -- quest tree reading ----------------------------------------------------
    @staticmethod
    def _holders():
        """Every agent holding a quest tree (players, SHARED, stations, sides).

        Uses the `__quests__` inventory registry directly - the same set
        `quest_driver._quest_holders` walks - because a quest granted to a station or a
        side is just as real as one granted to a ship, and `[SHARED] + players` silently
        skips it.
        """
        try:
            from sbs_utils.procedural.inventory import has_inventory
            return list(has_inventory("__quests__"))
        except Exception:
            return []

    @staticmethod
    def _walk(children, prefix, out, want_state):
        """Collect (path, node) for every quest in `want_state`, nested steps included.

        Mirrors `quest_driver._collect_active_quests`, but parameterized by state so the
        same walk finds IDLE quests to accept and COMPLETE ones to report. Paths are
        '/'-separated so `quest_mark_active` and friends can navigate them.
        """
        from sbs_utils.procedural.quest import QuestState
        for cid, q in (children or {}).items():
            path = prefix + cid
            if int(q.get("state", 0) or 0) == int(want_state):
                out.append((path, q))
            sub = q.get("children")
            if sub:
                QuestPilot._walk(sub, path + "/", out, want_state)
        return out

    def _quests_in(self, agent_id, state):
        from sbs_utils.procedural.quest import quest_agent_quests
        tree = quest_agent_quests(agent_id)
        if tree is None:
            return []
        return self._walk(tree.get("children", {}), "", [], state)

    def active_goals(self):
        """[(agent_id, quest_path, goal_key, trigger_dict)] across every holder."""
        from sbs_utils.procedural.quest_driver import _active_quests
        out = []
        for aid in self._holders():
            for qid, data in _active_quests(aid):
                for key in GOAL_KEYS:
                    trig = data.get(key)
                    if isinstance(trig, dict):
                        out.append((aid, qid, key, trig))
        return out

    # -- policy ----------------------------------------------------------------
    def wants_combat(self):
        """True when some ACTIVE quest actually asks for a kill.

        The exerciser consults this before staging combat. A peacetime patrol whose jobs
        are tow/scan/hail work has no business being shot at by the harness - see the
        module docstring for the measurement.
        """
        for _aid, _qid, key, _trig in self.active_goals():
            if key == "on_kill":
                return True
        return False

    def kill_roles(self):
        """Roles an ACTIVE on_kill goal names, so combat can be pointed at the right thing."""
        out = set()
        for _aid, _qid, key, trig in self.active_goals():
            if key == "on_kill" and trig.get("role"):
                out.add(trig["role"])
        return out

    # -- actuation -------------------------------------------------------------
    def step(self):
        """One pilot tick: accept what is offered, then push each goal along."""
        if self._sim() is None:
            return
        st = self._server_ctx()
        if st is None:
            return
        if not self._warned_drift:
            self._warned_drift = True
            drift = verify_goal_keys()
            if drift:
                print(f"[pilot] WARNING: unrecognized quest goal key(s) {', '.join(drift)} - "
                      "quests using them cannot be driven and will read as unreached")

        prev_task, prev_mast = FrameContext.task, FrameContext.mast
        FrameContext.task = st
        FrameContext.mast = st.main.mast
        try:
            self._accept_step()
            if self._goals:
                self._goal_step()
            self.steps += 1
        finally:
            FrameContext.task, FrameContext.mast = prev_task, prev_mast

    def _accept_step(self):
        """Take every IDLE quest to ACTIVE - what the Accept button does, and all it does."""
        if not self._accept or self._accept == "none":
            return
        from sbs_utils.procedural.quest import QuestState
        from sbs_utils.procedural.quest_driver import quest_mark_active
        wanted = None if self._accept == "all" else set(self._accept)
        for aid in self._holders():
            for path, _node in self._quests_in(aid, QuestState.IDLE):
                if wanted is not None and path not in wanted:
                    continue
                try:
                    quest_mark_active(aid, path)
                    self.accepted += 1
                except Exception:
                    self.errors += 1

    def _goal_step(self):
        from sbs_utils.procedural.roles import role
        players = self._player_ids()
        if not players:
            return
        # Round-robin the goals over the player ships so several jobs progress at once
        # rather than every ship chasing the same one.
        goals = [g for g in self.active_goals() if g[2] in DRIVABLE]
        for n, pid in enumerate(players):
            if not goals:
                break
            # An intent in flight owns the ship until it completes or its target dies.
            if self._continue_intent(pid):
                continue
            aid, qid, key, trig = goals[(self.steps + n) % len(goals)]
            if not self._drive_goal(pid, aid, qid, key, trig):
                # Nothing the goal vocabulary could do with this ship - most of a real
                # board is `on_signal`, so this is the common case, not the fallback.
                self._sweep_step(pid)
        # Record the goals nothing here can satisfy, for the report.
        for aid, qid, key, trig in self.active_goals():
            if key not in DRIVABLE:
                self._unreachable[qid] = key

    def _drive_goal(self, pid, aid, qid, key, trig):
        """Act on one goal. True when the ship was actually given something to do."""
        want = trig.get("role")
        if key == "on_scan":
            return self._do_scan(pid, want)
        if key == "on_dock":
            return self._do_dock(pid, want)
        if key == "on_tow":
            return self._do_tow(pid, want)
        if key in ("on_reach", "on_collect"):
            radius = float(trig.get("radius", _ARRIVE) or _ARRIVE)
            return self._do_fly_to_role(pid, want or trig.get("key"), radius)
        # on_kill is handled by the exerciser's combat staging, gated on wants_combat().
        return False

    # -- individual verbs ------------------------------------------------------
    def _do_scan(self, pid, want):
        from sbs_utils.procedural.science import science_ensure_scan
        tid = self._pick_by_role(pid, want, exclude=self._scanned)
        if tid is None:
            return False            # nothing new to scan - let the ship do something else
        self._scanned.add(tid)
        try:
            science_ensure_scan(pid, tid, tabs="*")
            self.scans += 1
            return True
        except Exception:
            self.errors += 1
        return False

    def _do_dock(self, pid, want):
        from sbs_utils.procedural.query import to_object
        tid = self._pick_by_role(pid, want)
        p = to_object(pid)
        if tid is None or p is None:
            return False
        try:
            p.data_set.set("dock_base_id", tid, 0)
            p.data_set.set("dock_state", "dock_start", 0)
            self.docks += 1
            return True
        except Exception:
            self.errors += 1
        return False

    def _do_tow(self, pid, want):
        """Attach the tether to a matching target, then haul it to a drop.

        HEURISTIC, AND SAID SO OUT LOUD: the quest declares WHAT to deliver but not WHERE
        - the destination lives in the mission's own proximity watcher, not in the goal
        dict. So the pilot hauls to the nearest friendly station, which is where the great
        majority of haul jobs deliver. A job that drops at a navpoint will not complete
        this way, and shows up as an unreached quest rather than a pass.
        """
        from sbs_utils.procedural.grav_tether import grav_tether_attach, grav_tether_targets_of
        held = list(grav_tether_targets_of(pid) or ())
        if held:
            drop = self._nearest_station(pid)
            if drop is not None:
                self._intent[pid] = {"kind": "tow", "target": held[0], "drop": drop}
            return True
        tid = self._pick_by_role(pid, want)
        if tid is None:
            return False
        # Close before grabbing: the tether has a grab speed limit and a range, exactly
        # as it does for a player.
        if self._distance(pid, tid) > _ARRIVE:
            self._fly_toward(pid, tid)
            return True
        try:
            if grav_tether_attach(pid, tid) is not None:
                self.tows += 1
                return True
        except Exception:
            self.errors += 1
        return False

    def _do_fly_to_role(self, pid, want, radius):
        tid = self._pick_by_role(pid, want)
        if tid is None:
            return False
        if self._distance(pid, tid) <= radius:
            return False
        self._intent[pid] = {"kind": "fly", "target": tid, "radius": radius}
        self._fly_toward(pid, tid)
        return True

    def _continue_intent(self, pid):
        """Keep pushing an in-flight intent. True while it still owns the ship."""
        it = self._intent.get(pid)
        if not it:
            return False
        if self._pos_of(it.get("target")) is None:
            self._intent.pop(pid, None)      # target destroyed or despawned
            return False
        if it["kind"] == "fly":
            if self._distance(pid, it["target"]) <= it.get("radius", _ARRIVE):
                self._intent.pop(pid, None)
                self._visited.add(it["target"])
                self.visits += 1
                self._stop(pid)
                return False
            self._fly_toward(pid, it["target"])
            return True
        if it["kind"] == "grab":
            tid = it["target"]
            if self._distance(pid, tid) > _ARRIVE:
                if it.get("age", 0) > _GIVE_UP_STEPS:
                    # Unreachable in a sensible time (too far, or we cannot catch it).
                    # Rule it out rather than chase it for the rest of the run.
                    self._towed.add(tid)
                    self._intent.pop(pid, None)
                    return False
                it["age"] = it.get("age", 0) + 1
                self._fly_toward(pid, tid)
                return True
            from sbs_utils.procedural.grav_tether import grav_tether_attach
            self._intent.pop(pid, None)
            try:
                if grav_tether_attach(pid, tid) is not None:
                    self.tows += 1
                    drop = self._nearest_station(pid)
                    if drop is not None:
                        self._intent[pid] = {"kind": "tow", "target": tid, "drop": drop}
                    return True
            except Exception:
                self.errors += 1
            # Refused by the mission's own attach policy, or moving too fast to grab.
            # Remember it so the sweep stops asking the same forbidden question.
            self._towed.add(tid)
            return False
        if it["kind"] == "tow":
            drop = it.get("drop")
            if drop is None or self._pos_of(drop) is None:
                self._intent.pop(pid, None)
                return False
            if self._distance(pid, drop) <= _TOW_DROP_RADIUS:
                # Arrived: let go, the same act the Weapons tether release performs.
                from sbs_utils.procedural.grav_tether import grav_tether_release
                try:
                    grav_tether_release(pid, it["target"])
                except Exception:
                    self.errors += 1
                self._intent.pop(pid, None)
                self._stop(pid)
                return False
            self._fly_toward(pid, drop)
            return True
        return False

    # -- world sweeps ----------------------------------------------------------
    # These carry NO mission knowledge. They exercise the physical vocabulary of the
    # game - haul something somewhere, go to the places the mission marked - so that
    # whichever proximity watcher a mission wired up gets a chance to notice. This is
    # what reaches an `on_signal` job, which is most of a real board.

    def _sweep_step(self, pid):
        """One sweep action for a ship no quest goal claimed. True if it acted."""
        # Alternate haul and visit so a mission with only one kind of job still gets
        # both, and neither starves the other.
        self._sweep_rotor += 1
        order = (self._sweep_tow, self._sweep_visit)
        if self._sweep_rotor % 2:
            order = tuple(reversed(order))
        for fn in order:
            if fn(pid):
                return True
        return False

    def _sweep_tow(self, pid):
        """Grab the nearest thing the mission will let us grab, and haul it to a station.

        Candidate selection is deliberately crude - anything that is not a player and not
        a station - because the AUTHORITY is the mission's own attach policy:
        `grav_tether_attach` runs `_attach_allowed` (which Peacetime hooks with
        `pr_tether_ownership_policy`) and returns None when the answer is no. Asking the
        game rather than guessing is what keeps this mission-agnostic, and it means the
        sweep cannot manufacture a grab a player could not perform.
        """
        from sbs_utils.procedural.grav_tether import (grav_tether_attach,
                                                      grav_tether_targets_of)
        if list(grav_tether_targets_of(pid) or ()):
            return False                    # already hauling; the intent owns it
        tid = self._pick_towable(pid)
        if tid is None:
            return False
        # COMMIT, don't re-decide. The goal rotor hands this ship a different goal every
        # step, so a sweep that merely pointed the nose each time never actually arrived
        # anywhere - it turned toward a new object every tick and towed nothing all run.
        # An intent owns the ship until the grab succeeds or the candidate is ruled out.
        self._intent[pid] = {"kind": "grab", "target": tid}
        self._fly_toward(pid, tid)
        return True

    def _sweep_visit(self, pid):
        """Fly to somewhere the mission marked and has not been visited yet.

        Navpoints and navareas are where a mission puts the places it cares about - a
        drop zone, a rendezvous, a hazard field - so touring them is the general form of
        "go where the job says". Proximity watchers keyed to those places fire on arrival
        without the pilot knowing what any of them mean.
        """
        tid = self._pick_unvisited(pid)
        if tid is None:
            return False
        if self._distance(pid, tid) <= _ARRIVE:
            self._visited.add(tid)
            self.visits += 1
            return False
        self._intent[pid] = {"kind": "fly", "target": tid, "radius": _ARRIVE}
        self._fly_toward(pid, tid)
        return True

    def _pick_towable(self, pid):
        """Nearest plausible tow candidate not already tried."""
        from sbs_utils.procedural.roles import role
        try:
            skip = set(role("__player__")) | set(role("station"))
        except Exception:
            skip = {pid}
        ids = [i for i in self._nearby(pid, _SEARCH_REACH)
               if i not in skip and i not in self._towed]
        if not ids:
            return None
        return min(ids, key=lambda i: self._distance(pid, i))

    def _pick_unvisited(self, pid):
        """Nearest navpoint the sweep has not reached yet, else an unvisited object.

        Navpoint ENUMERATION is mock-only (`nav_points_by_id`); the engine can look one
        up by id but will not hand over the list. So navpoints are toured when the table
        happens to be there, and otherwise the sweep visits objects - which is the part
        that works everywhere.
        """
        cands = []
        sim = self._sim()
        nav = getattr(sim, "nav_points_by_id", None) if sim is not None else None
        if nav:
            cands = [i for i in nav.keys() if i not in self._visited]
        if not cands:
            try:
                from sbs_utils.procedural.roles import role
                skip = set(role("__player__"))
            except Exception:
                skip = {pid}
            cands = [i for i in self._nearby(pid, _SEARCH_REACH)
                     if i not in skip and i not in self._visited]
        if not cands:
            return None
        return min(cands, key=lambda i: self._distance(pid, i))

    # -- movement --------------------------------------------------------------
    def _fly_toward(self, pid, tid):
        """Point the ship at a target and open the throttle.

        This is the helm AI's own actuation - direction steering via steerToDirD{X,Y,Z}
        plus steeringToDirFlag, with playerThrottle for speed (mock `_playership_drive`).
        No position is ever written.
        """
        from sbs_utils.procedural.query import to_object
        p = to_object(pid)
        tp = self._pos_of(tid)
        if p is None or tp is None:
            return
        dx = tp.x - p.pos.x
        dy = tp.y - p.pos.y
        dz = tp.z - p.pos.z
        d = math.sqrt(dx * dx + dy * dy + dz * dz)
        if d <= 0.001:
            return
        try:
            ds = p.data_set
            ds.set("steerToDirDX", dx / d, 0)
            ds.set("steerToDirDY", dy / d, 0)
            ds.set("steerToDirDZ", dz / d, 0)
            ds.set("steeringToDirFlag", 1, 0)
            # WARP WHEN IT IS FAR AND CLEAR, which is what a helm actually does. Impulse
            # tops out at PLAYER_IMPULSE_SPEED (180 u/s); a Cosmos map is tens of
            # thousands of units across, so an impulse-only pilot spends a whole
            # 120-second run in transit and arrives nowhere - measured: 160 flights, 1
            # arrival, 0 tows. Warp is 180 + (throttle-1) * 450, so throttle 3 is 1080.
            #
            # "AND CLEAR" IS LOAD-BEARING. Warping blind rammed terrain at 1080 u/s for
            # 5400 damage - it destroyed the player ship, ended the mission mid-window
            # and restarted it, which is BOTH a false failure and the thing that made
            # runs unrepeatable (whether you clip a rock depends on physics-thread
            # timing, so the same seed diverged: 57 jobs accepted one run, 19 the next).
            # No pilot should fly in a way that gets the ship killed, and no helm would.
            if d > 12000 and self._clear_ahead(pid):
                throttle = 3.0
            elif d > 4000:
                throttle = 1.0
            else:
                throttle = 0.35
            ds.set("playerThrottle", throttle, 0)
            self.flights += 1
        except Exception:
            self.errors += 1

    def _clear_ahead(self, pid):
        """Whether it is safe to go to warp: nothing else close by.

        Deliberately crude - a radius, not a swept volume - because the point is not to
        model navigation, it is to stop the harness killing the ship it is meant to be
        testing with. Terrain is the usual culprit and it does not move, so a plain
        proximity check is enough.
        """
        if self._pos_of(pid) is None:
            return False
        for oid in self._nearby(pid, _WARP_CLEARANCE):
            if oid == pid:
                continue
            if self._distance(pid, oid) < _WARP_CLEARANCE:
                return False
        return True

    def _stop(self, pid):
        from sbs_utils.procedural.query import to_object
        p = to_object(pid)
        if p is None:
            return
        try:
            p.data_set.set("playerThrottle", 0.0, 0)
            p.data_set.set("steeringToDirFlag", 0, 0)
        except Exception:
            self.errors += 1

    # -- world queries ---------------------------------------------------------
    def _player_ids(self):
        try:
            from sbs_utils.procedural.roles import role
            from sbs_utils.procedural.query import object_exists
            return [i for i in role("__player__") if object_exists(i)]
        except Exception:
            return []

    def _pick_by_role(self, pid, want, exclude=None):
        """Nearest live object holding `want` (anything nearby when want is None)."""
        from sbs_utils.procedural.query import object_exists
        skip = set(exclude or ())
        if want:
            try:
                from sbs_utils.procedural.roles import role
                ids = [i for i in role(want) if i != pid and i not in skip
                       and object_exists(i)]
            except Exception:
                return None
        else:
            ids = [i for i in self._nearby(pid, _SEARCH_REACH)
                   if i != pid and i not in skip]
        if not ids:
            return None
        return min(ids, key=lambda i: self._distance(pid, i))

    def _nearest_station(self, pid):
        from sbs_utils.procedural.roles import role
        from sbs_utils.procedural.query import object_exists
        try:
            ids = [i for i in role("station") if object_exists(i)]
        except Exception:
            return None
        if not ids:
            return None
        return min(ids, key=lambda i: self._distance(pid, i))

    def _pos_of(self, oid):
        """Position of a space object OR a navpoint.

        Two lookups because they live in different places, and a sweep that tours the
        spots a mission marked needs both. Checking only one meant a navpoint intent was
        dropped on the tick after it was set, so the ship never went anywhere and the
        sweep looked inert.
        """
        from sbs_utils.procedural.query import to_object
        o = to_object(oid)
        pos = getattr(o, "pos", None) if o is not None else None
        if pos is not None:
            return pos
        sim = self._sim()
        if sim is None:
            return None
        try:
            # `get_navpoint_by_id` is in the REAL engine API, unlike the mock's
            # `nav_points_by_id` dict.
            n = sim.get_navpoint_by_id(oid)
        except Exception:
            n = None
        return getattr(n, "pos", None) if n is not None else None

    def _distance(self, a, b):
        pa, pb = self._pos_of(a), self._pos_of(b)
        if pa is None or pb is None:
            return float("inf")
        dx = pa.x - pb.x
        dy = pa.y - pb.y
        dz = pa.z - pb.z
        return math.sqrt(dx * dx + dy * dy + dz * dz)

    # -- reporting -------------------------------------------------------------
    def snapshot(self):
        """Quest outcomes for the verdict and the ratchet baseline.

        `unreachable` is the honest part: goals the pilot cannot synthesize (on_signal)
        are listed rather than quietly counted as "not done yet", so a run that leaves
        them unfinished reads as a harness limit and not a mission failure.
        """
        from sbs_utils.procedural.quest import QuestState
        complete, active, failed = set(), set(), set()
        for aid in self._holders():
            for path, _n in self._quests_in(aid, QuestState.COMPLETE):
                complete.add(path)
            for path, _n in self._quests_in(aid, QuestState.ACTIVE):
                active.add(path)
            for path, _n in self._quests_in(aid, QuestState.FAILED):
                failed.add(path)
        return {
            "complete": sorted(complete),
            "active": sorted(active),
            "failed": sorted(failed),
            "unreachable": dict(sorted(self._unreachable.items())),
            "accepted": self.accepted,
            "scans": self.scans,
            "tows": self.tows,
            "docks": self.docks,
            "visits": self.visits,
            "flights": self.flights,
            "errors": self.errors,
        }
