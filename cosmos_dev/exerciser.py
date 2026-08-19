"""Coverage exerciser for the mock test harness (dev-only).

Drives the procedural selection / comms / science API across the live world so
mission `//` routes fire - pushing coverage past what a play-to-win autoplayer
reaches (e.g. comms routes a greedy combat bot never opens). Used by
``mission_runner --test --exercise``. See AUTOPLAY_PLAN.md.

Each ``step()`` selects one target per player on science + comms (rotating
through all contacts over successive steps), which fires the science select
route and opens comms (//enable/comms + //comms). Calls run inside the server
task's MAST context (FrameContext.mast/task), because the procedural route
helpers no-op / mis-fire without it (same reason game_started needed it).
"""
from sbs_utils.helpers import FrameContext


class Exerciser:
    def __init__(self, sbs, extra_consoles=None, console_dwell=None,
                 click_labels=None, click_every=3):
        self._sbs = sbs
        # Steps to sit on each console. The default is brisk, which means a
        # console is swapped away in well under a sim-second -- so `on change`
        # and watcher logic keyed to a 1s tick NEVER RUNS. Raise it when the
        # thing under test has live panels (--exercise-dwell).
        if console_dwell:
            self._CONSOLE_DWELL = int(console_dwell)
        # Mission-defined consoles to fold into the cycle (--exercise-console).
        # Opt-in: the default set is core gameplay only, because a demo/admin
        # console usually has context needs of its own.
        self._extra_consoles = tuple(extra_consoles or ())
        self._offset = 0
        # Named clicks run on their OWN clock, because _offset only advances
        # while there is a live player ship -- see step().
        self._click_offset = 0
        self._click_rotor = 0
        self.steps = 0
        self.errors = 0
        self.enemies_last = 0   # diagnostics
        self.forced = 0
        # Preconditioning (shields-down + overheat) is lethal if applied forever -
        # it kills the player and starves late-game/respawn content. Spend a small
        # budget to trip //damage/internal + heat a few times, then back off and
        # let real beam combat carry on.
        self._precondition_budget = 8
        self._comms_step = 0     # rotates the comms button-walk path each step
        self._dock_budget = 3    # times to force a dock (cover dock routes), then stop
        self._console_step = 0   # rotates the synthetic client through each console
        self._console_dwell = 0  # steps spent on the current console before cycling on
        self._warned_consoles = False   # print an unknown --exercise-console name once
        # Buttons to press BY LABEL (--exercise-click). Lets one boot walk a
        # mission's own paging control -- a gallery tour, a wizard, a next-page
        # button -- instead of booting once per state. The mastlib compile is
        # most of a run's cost, so walking N states in one session is ~N times
        # cheaper than N sessions.
        self._click_labels = tuple(click_labels or ())
        self._click_every = max(1, int(click_every or 1))
        self.clicked = 0
        self._warned_click = False

    def _server_ctx(self):
        """Return the server task, or None if not ready."""
        return FrameContext.server_task

    def click_step(self) -> None:
        """Press the buttons named by --exercise-click. Nothing else.

        Separate from step(), and callable when step() is not, because the
        screens most worth driving BY NAME are the ones that outlive the
        gameplay loop -- the end-of-mission results page and its tabs. Three
        things independently stopped that working, and each alone was enough to
        make --exercise-click look like it did nothing:

          * step() returns early with no live player ship, and the click used to
            sit below that -- so a mission ending in defeat could never have its
            end screen clicked;
          * step() is skipped entirely while the sim is PAUSED, which is what a
            mission does when it ends. The GUI is still live, so the click is
            still meaningful -- that is why the runner calls this directly;
          * _click_by_label was looking in the wrong places (see there).

        Its own counter: _offset only advances inside the player-dependent part
        of step(), so reusing it froze the cadence the moment the players died.
        """
        if not self._click_labels:
            return
        st = self._server_ctx()
        if st is None:
            return
        _pt, _pm = FrameContext.task, FrameContext.mast
        FrameContext.task = st
        FrameContext.mast = st.main.mast
        try:
            if self._click_offset % self._click_every == 0:
                self._click_by_label()
        finally:
            FrameContext.task, FrameContext.mast = _pt, _pm
        self._click_offset += 1

    def step(self) -> None:
        """One exercise tick: fire science + comms selects for each player ship
        against a rotating target, within the server MAST context."""
        sbs = self._sbs
        if sbs.sim is None:
            return
        st = self._server_ctx()
        if st is None:
            return

        from sbs_utils.procedural.roles import role
        from sbs_utils.procedural.routes import (
            follow_route_select_science, follow_route_select_comms,
            follow_route_select_grid, _follow_route_console,
        )
        from sbs_utils.procedural.query import set_weapons_selection
        from sbs_utils.procedural.science import science_ensure_scan

        # Named clicks FIRST, and outside every player-ship guard below.
        self.click_step()

        player_ids = list(role("__player__"))
        if not player_ids:
            return
        pset = set(player_ids)
        target_ids = [i for i in sbs.sim.space_objects.keys() if i not in pset]
        if not target_ids:
            return

        prev_task, prev_mast = FrameContext.task, FrameContext.mast
        FrameContext.task = st
        FrameContext.mast = st.main.mast
        try:
            for n, pid in enumerate(player_ids):
                # Rotate science/comms selects through all contacts over time.
                tid = target_ids[(self._offset + n) % len(target_ids)]
                for fn in (follow_route_select_science, follow_route_select_comms):
                    try:
                        fn(pid, tid)
                    except Exception:
                        # Route runtime errors flow to the verdict via the
                        # MastScheduler seam; count Python-level failures here.
                        self.errors += 1
                # Complete a science scan on the selected target -> fires the
                # science_scan_complete handler and //science / <scan> routes.
                try:
                    science_ensure_scan(pid, tid, tabs="*")
                except Exception:
                    self.errors += 1
                # follow_route_select_comms opened a live comms session; walk its
                # button tree to reach //comms/<submenu> routes the root never hits.
                self._walk_comms_buttons(pid, tid)
                # Also hail OWN ship (origin==selected) to reach internal/crew comms
                # (sickbay, security, engineering...) - a different comms context.
                try:
                    follow_route_select_comms(pid, pid)
                except Exception:
                    self.errors += 1
                self._walk_comms_buttons(pid, pid)
                # Grid select -> //focus/grid (+ //select/grid).
                try:
                    follow_route_select_grid(pid, tid)
                except Exception:
                    self.errors += 1
                # Weapons: lock the nearest armed hostile so player beams engage
                # -> hits -> //damage routes. Stable target so the 6s beam cooldown
                # isn't reset by retargeting every tick.
                enemy = self._pick_enemy(sbs, pid)
                if enemy:
                    try:
                        set_weapons_selection(pid, enemy)
                        # Weapons-console select route (//select/weapons).
                        _follow_route_console(pid, enemy, "weapon_target_UID",
                                              "weapon_sorted_list", None)
                        # Occasionally launch a torpedo -> //launch/missile (the
                        # event the engine emits when a player fires a torp). Rate-
                        # limited so it's not a per-tick spam.
                        if self._offset % 4 == 0 and hasattr(sbs, "launch_missile"):
                            sbs.launch_missile(pid, enemy)
                    except Exception:
                        self.errors += 1
            # Dock the player at a friendly station a few times -> dock routes +
            # //shared/signal/docked (real docking flow, briefly).
            if self._dock_budget > 0:
                self._force_dock(sbs, player_ids[0])
            # Cycle the synthetic console client through every console so each
            # @console body + watcher executes (deterministic console coverage).
            self._cycle_consoles()
            # (Named clicks already ran at the top of step(), before the
            # player-ship guards, so they also reach post-game screens.)
            # Monkey/fuzz: a random valid in-console GUI click every few steps (kept
            # sparse so it doesn't constantly yank a console off its AI loop).
            if self._offset % 3 == 0:
                self._fuzz_gui()
            # Stage a REAL beam exchange (TEST-ONLY teleport) so the genuine
            # damage flow drives //damage/internal + heat on the player; then a
            # synthetic kill on a *different* hostile for deterministic destroy.
            staged = self._stage_combat(sbs, player_ids[0])
            self._force_combat(sbs, player_ids[0], exclude=staged)
            self._offset += 1
            self.steps += 1
        finally:
            FrameContext.task = prev_task
            FrameContext.mast = prev_mast

    _COMMS_WIDTH = 6     # max button index tried per comms level

    def _walk_comms_buttons(self, pid, tid):
        """Press comms buttons on the session just opened by
        follow_route_select_comms, walking ~2 levels deep so //comms/<submenu>
        routes fire (the root select alone only hits //comms). A button press is
        a `press_comms_button` event (sub_tag = index) dispatched to
        comms_target_UID - the same path handlerhooks uses. Out-of-range indices
        no-op (CommsPromise guards `index < len(buttons)`). Rotates a depth-2 path
        across steps to fan out over the tree. TEST-ONLY: surfacing a broken comms
        route as a verdict failure is the point of the systems test."""
        from sbs_utils.consoledispatcher import ConsoleDispatcher
        from sbs_utils.helpers import FakeEvent
        w = self._COMMS_WIDTH
        path = (self._comms_step % w, (self._comms_step // w) % w)
        self._comms_step += 1
        for idx in path:
            ev = FakeEvent(client_id=0, tag="press_comms_button", sub_tag=str(idx),
                           origin_id=pid, selected_id=tid, value_tag="comms_target_UID")
            try:
                ConsoleDispatcher.dispatch_message(ev, "comms_target_UID")
            except Exception:
                # Route errors flow to the verdict via the scheduler seam; count
                # Python-level failures here.
                self.errors += 1

    def _click_by_label(self):
        """Press ONE widget whose DISPLAYED text matches a wanted label.

        Matches on what the engine would draw (props_display_text strips the
        style props off), case-insensitively, so the caller names the button the
        way a player sees it -- `--exercise-click "Next"` -- rather than by a tag
        that is regenerated on every rebuild.

        Server page included, unlike the fuzz: this is a click the caller asked
        for by name, not a random one, and a mission's own driver may well live
        on the server screen.

        **One press per pass, rotating through the names.** The engine delivers
        exactly one gui_message per press and handlerhooks runs tick_the_rest
        immediately after it, so several presses with no tick between them is a
        state the engine cannot reach -- and a driver that manufactures one
        produces phantom failures rather than finding real ones. This dispatched
        every match it could see, and because a sub-task handler repaints
        SYNCHRONOUSLY (adding fresh entries while the walk is still going), the
        LM results tabs took 40622 presses in a run where the queue-a-jump form
        took 3380. That starved the rest of the tick and read as lost AI
        coverage. Same family as the unreachable "rapid click" defect pinned in
        tests/test_gui_message_dead_builder.py::TestRepeatClicks.

        Coverage does not suffer: the caller's tick loop runs this again next
        tick, and a screen worth driving is up for thousands of ticks.
        """
        from sbs_utils.gui import Gui
        from sbs_utils.helpers import FakeEvent, props_display_text
        from sbs_utils.agent import Agent
        # The engine sets the `sim` MAST global at the top of
        # cosmos_event_handler and clears it at the bottom, so it is live for
        # the whole of a real click. This dispatches Gui.on_message directly, so
        # without it a handler that runs synchronously inside the click (any
        # sub-task handler) evaluates `sim` as None -- again, a state the engine
        # cannot reach. Restored after, so the harness leaves nothing set.
        _prev_sim = Agent.SHARED.get_inventory_value("sim")
        Agent.SHARED.set_inventory_value("sim", getattr(self._sbs, "sim", None))
        try:
            names = [w.strip().lower() for w in self._click_labels if w.strip()]
            if not names:
                return
            seen = []
            matches = []          # (cid, tag, text) for every visible match
            for cid, gc in list(Gui.clients.items()):
                # The whole page STACK, not just gc.page. A screen pushed over
                # the console -- the end-of-game results page is the one that
                # bit -- lives in page_stack, and gui_handler_audit.sample()
                # could see its widgets for 69k ticks while this reported
                # "no match".
                pages = list(getattr(gc, "page_stack", None) or [])
                page = getattr(gc, "page", None)
                if page is not None and page not in pages:
                    pages.append(page)
                # BOTH maps, for each. swap_layout moves pending_tag_map ->
                # tag_map on a repaint, so on most ticks a freshly built screen
                # is ONLY in the pending one and tag_map is empty.
                for pg in pages:
                    for attr in ("tag_map", "pending_tag_map"):
                        for tag, entry in list((getattr(pg, attr, None) or {}).items()):
                            # the maps hold (layout_item, runtime_node) tuples.
                            item = entry[0] if isinstance(entry, tuple) and entry else entry
                            text = props_display_text(getattr(item, "value", None))
                            if not text:
                                continue
                            text = text.strip()
                            seen.append(f"{cid}:{text}")
                            if text.lower() in names:
                                matches.append((cid, tag, text.lower()))
            if matches:
                # Rotate so every named button gets its turn over successive
                # ticks instead of the first one always winning.
                pref = names[self._click_rotor % len(names)]
                cid, tag, _ = next((m for m in matches if m[2] == pref), matches[0])
                self._click_rotor += 1
                try:
                    Gui.on_message(FakeEvent(client_id=cid, tag="gui_message",
                                             sub_tag=tag))
                    self.clicked += 1
                except Exception:
                    self.errors += 1
            # A label that never matches makes a --exercise-click run silently
            # vacuous: it passes while driving nothing. Say so once, with what
            # WAS on screen, so the caller can see whether it is a typo or a
            # page that was never reached.
            if not self.clicked and not self._warned_click:
                self._warned_click = True
                print(f"exercise-click: no match for {list(self._click_labels)}; "
                      f"visible labels so far: {sorted(set(seen))[:25]}")
        finally:
            Agent.SHARED.set_inventory_value("sim", _prev_sim)

    def _fuzz_gui(self):
        """Monkey/fuzz: fire a random *valid* widget click on each client's live
        page (a real tag from page.tag_map, dispatched via Gui.on_message - the
        same path as a browser click). Drives GUI/on_message handlers the greedy
        player never reaches; any crash surfaces via the verdict. TEST-ONLY."""
        import random
        from sbs_utils.gui import Gui
        from sbs_utils.helpers import FakeEvent
        for cid, gc in list(Gui.clients.items()):
            if cid == 0:
                continue   # never fuzz the server/mission-control page (jumps the map)
            page = getattr(gc, "page", None)
            # Skip the console picker: _cycle_consoles owns console navigation, and
            # random picker clicks would fight its deterministic rotation. Fuzz only
            # in-console widgets (most console widgets are engine-side and not in
            # tag_map, so this is a no-op there - but custom gui buttons get hit).
            if page is None or not getattr(page, "console", None):
                continue
            tag_map = getattr(page, "tag_map", None)
            if not tag_map:
                continue
            tag = random.choice(list(tag_map.keys()))
            try:
                Gui.on_message(FakeEvent(client_id=cid, tag="gui_message", sub_tag=tag))
                self.fuzzed = getattr(self, "fuzzed", 0) + 1
            except Exception:
                self.errors += 1

    _CONSOLE_DWELL = 3   # steps to sit on a console; see --exercise-dwell
    # Core gameplay consoles to cycle. mainscreen is intentionally omitted: switching
    # to it fires a main_screen_change reroute cascade onto other linked consoles,
    # which (driven synthetically) presents an uncompiled page -> spurious noise.
    _GAMEPLAY_CONSOLES = ("helm", "weapons", "engineering", "comms", "science")

    def _cycle_consoles(self):
        """Drive the synthetic test console client(s) deterministically through every
        console so each @console label body and its watch/on-change logic actually
        executes. The greedy autoplayer otherwise parks on one console (helm),
        leaving the rest uncovered.

        Routes via LegendaryMissions' own `show_console_selected` label with
        `CONSOLE_SELECT` set to each registered console key (helm, weapons,
        science, engineering, comms, ...) - the same entry the console picker uses,
        so it's robust to the picker's per-rebuild tag renumbering. The select
        flow sets up the gui_task scope (crew_name, consoles, tabs...) before its
        picker await, so jumping straight to show_console_selected is safe from the
        picker too. Rotate every _CONSOLE_DWELL steps. TEST-ONLY: a crash in any
        console body surfaces via the verdict."""
        from sbs_utils.gui import Gui
        from sbs_utils.helpers import FakeEvent, FrameContextOverride
        from sbs_utils.procedural.gui.console_types import gui_get_console_types
        from sbs_utils.procedural.roles import role
        sbs = self._sbs
        # Core gameplay consoles only. The demo/admin consoles (display_panels,
        # director, gamemaster, admin, hangar, admiral) have their own context
        # needs and aren't the coverage target here.
        registered = gui_get_console_types()
        wanted = self._GAMEPLAY_CONSOLES + self._extra_consoles
        keys = [k for k in wanted if k in registered]
        missing = [k for k in self._extra_consoles if k not in registered]
        if missing and not self._warned_consoles:
            self._warned_consoles = True
            print(f"exercise: no such console(s): {', '.join(missing)}; "
                  f"registered: {', '.join(sorted(registered))}")
        if not keys:
            return
        self._console_dwell += 1
        if self._console_dwell < self._CONSOLE_DWELL:
            return
        self._console_dwell = 0
        players = list(role("__player__"))
        for cid, gc in list(Gui.clients.items()):
            if cid == 0:
                continue
            page = getattr(gc, "page", None)
            gt = getattr(page, "gui_task", None) if page is not None else None
            if gt is None:
                continue
            # The synthetic client bypassed ship-select; console bodies (and tabs)
            # assume a ship, so assign it to a real player ship once.
            if players and not sbs.get_ship_of_client(cid):
                sbs.assign_client_to_ship(cid, players[0])
            key = keys[self._console_step % len(keys)]
            self._console_step += 1
            try:
                with FrameContextOverride(gt, page):
                    gt.set_variable("CONSOLE_SELECT", key)
                    gt.jump("show_console_selected")
                    gt.tick_in_context()
                    page.present(FakeEvent(client_id=cid, tag="client_change",
                                           sub_tag="change_console"))
            except Exception:
                self.errors += 1

    def _force_dock(self, sbs, pid):
        """TEST-ONLY: dock the player at a station to fire the dock routes
        (//dock, //shared/signal/docked, cockpit_dock_success). Sets dock_state
        directly the way the autoplay does on a close approach; the docking system
        then completes the handshake. Decrements a small budget so it doesn't keep
        the player permanently docked."""
        from sbs_utils.procedural.roles import role
        space = sbs.sim.space_objects
        p = space.get(pid)
        if p is None:
            return
        stations = [i for i in role("station") if i in space and i != pid]
        if not stations:
            return
        st = self._nearest(sbs, pid, stations) or stations[0]
        p.data_set.set("dock_base_id", st, 0)
        if p.data_set.get("dock_state", 0) not in ("docked", "dock_start"):
            p.data_set.set("dock_state", "dock_start", 0)
            self._dock_budget -= 1

    def _pick_enemy(self, sbs, pid, exclude=None, prefer_beams=False):
        """Nearest *damageable hostile* to `pid` (raider/enemy/monster preferred;
        else any armed non-player). `exclude` drops one id; `prefer_beams` favors
        a beam-armed hostile (so it can shoot back) when one exists. None if no
        candidate."""
        from sbs_utils.procedural.roles import any_role
        space = sbs.sim.space_objects

        def armed(i):
            o = space.get(i)
            # A combat ship/station: has beams, shields, or armor (NPC ships have
            # no armor - that's station-only - so don't key on armorMax alone).
            if o is None:
                return False
            ds = o.data_set
            return ((ds.get("beamCount") or 0) > 0 or (ds.get("shield_max_val") or 0) > 0
                    or (ds.get("armorMax") or 0) > 0)

        cand = [i for i in any_role("raider,enemy,monster") if armed(i)]
        if not cand:
            cand = [i for i in space.keys()
                    if i != pid and armed(i) and not (space[i]._abits & 0x20)]
        if exclude is not None:
            cand = [i for i in cand if i != exclude]
        self.enemies_last = len(cand)
        if prefer_beams:
            beamed = [i for i in cand if (space[i].data_set.get("beamRange") or 0) > 0]
            if beamed:
                cand = beamed
        return self._nearest(sbs, pid, cand)

    def _stage_combat(self, sbs, pid):
        """TEST-ONLY: teleport a beam-armed hostile into the player's beam range
        and forward arc, and wire mutual weapon targeting, so REAL beams trade
        fire both ways - exercising //damage (player->npc) and //damage/internal
        + //damage/heat (npc->player) through the genuine damage flow that the
        synthetic _force_combat can't reach. A brief opening burst (budgeted in
        __init__) trips the internal + heat routes a few times, then it stops so
        the player isn't machine-gunned to death and normal combat carries on.
        The teleport lives ONLY here; autoplay never moves objects. Returns the
        staged enemy id, or None."""
        if self._precondition_budget <= 0:
            return None                          # opening burst spent; let combat run
        space = sbs.sim.space_objects
        p = space.get(pid)
        if p is None:
            return None
        e_id = self._pick_enemy(sbs, pid, prefer_beams=True)
        e = space.get(e_id) if e_id else None
        if e is None:
            return None
        pr = p.data_set.get("beamRange") or 0.0
        er = e.data_set.get("beamRange") or 0.0
        rngs = [r for r in (pr, er) if r > 0]
        if not rngs:
            return None                      # neither can beam; nothing to stage
        d = min(rngs) * 0.5                  # well inside both ranges and the arc
        fwd = p.forward_vector()
        e._pos = type(p._pos)(p._pos.x + fwd.x * d,
                              p._pos.y + fwd.y * d,
                              p._pos.z + fwd.z * d)
        from sbs_utils.procedural.query import set_weapons_selection
        try:
            set_weapons_selection(pid, e_id)         # player beams -> enemy
        except Exception:
            self.errors += 1
        e.data_set.set("target_id", pid)             # enemy AI beams -> player
        e.data_set.set("beamArcWidth", 360.0)        # omni: enemy facing won't gate return fire
        e._beam_cooldown = 0.0                        # fire at the player this tick
        # TEST-ONLY preconditioning so the GENUINE damage flow reaches the
        # internal + heat routes inside a bounded run. The engine emits
        # player_internal_damage only once shields are down, and
        # heat_critical_damage only when overheated - both take far longer than a
        # few seconds to occur naturally. We don't fake the damage event; we set
        # the same preconditions the engine requires, then let the real NPC beam
        # hit (apply_damage) produce the internal hit, and the heat model fire.
        p.data_set.set("shield_val", 0.0, 0)         # shields down -> next hit is internal
        # Overheat the weapons system (engine system_cur_heat, SHPSYS 0) past
        # critical -> heat_critical_damage (engineering-style, not combat).
        p.data_set.set("system_cur_heat", 1.5, 0)
        self._precondition_budget -= 1
        self.forced += 1
        return e_id

    def _force_combat(self, sbs, pid, exclude=None):
        """Make //damage routes fire in a bounded test. Mission-spawned mock ships
        don't reliably carry beam shipData (beamRange 0), so emergent beam combat
        won't engage in a few seconds. Instead generate the hit directly via the
        mock's apply_damage, which queues the SAME engine events a real beam hit
        does (damage -> //damage; lethal -> //damage/destroy + npc/station_killed),
        so the mission's damage logic is exercised identically. (set_beam_damages
        governs beam damage when beams do fire - covered by a unit test.)"""
        e_id = self._pick_enemy(sbs, pid, exclude=exclude)
        e = sbs.sim.space_objects.get(e_id) if e_id else None
        if e is None:
            return
        # Enemy: small hit (shields absorb -> //damage) then a big hit through
        # shields + hull (-> //damage/destroy + npc/station_killed).
        # NOTE: we don't force player damage here - it pauses the sim early (game
        # logic) and //damage/internal /heat key on the ship's registered handler,
        # so forcing didn't cover them. The mock now emits player_internal_damage /
        # heat_critical_damage with the correct payloads (system index / sub_float /
        # source_point) for when the *real* damage flow drives them.
        try:
            sbs.apply_damage(e_id, 5.0, pid)          # non-fatal -> //damage
            sbs.apply_damage(e_id, 1.0e9, pid)        # lethal   -> //damage/destroy + killed
            self.forced += 1
        except Exception:
            self.errors += 1

    def _nearest(self, sbs, pid, target_ids):
        """Nearest target id to player `pid` by mock position (or None)."""
        p = sbs.sim.space_objects.get(pid)
        if p is None:
            return None
        best = None
        best_d = None
        for tid in target_ids:
            o = sbs.sim.space_objects.get(tid)
            if o is None:
                continue
            dx = o._pos.x - p._pos.x
            dy = o._pos.y - p._pos.y
            dz = o._pos.z - p._pos.z
            d = dx * dx + dy * dy + dz * dz
            if best_d is None or d < best_d:
                best_d = d
                best = tid
        return best
