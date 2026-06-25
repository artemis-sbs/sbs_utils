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
    def __init__(self, sbs):
        self._sbs = sbs
        self._offset = 0
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

    def _server_ctx(self):
        """Return the server task, or None if not ready."""
        return FrameContext.server_task

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
                    except Exception:
                        self.errors += 1
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
