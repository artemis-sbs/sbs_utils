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
                # Weapons: lock the nearest armed hostile so player beams engage
                # -> hits -> //damage routes. Stable target so the 6s beam cooldown
                # isn't reset by retargeting every tick.
                enemy = self._pick_enemy(sbs, pid)
                if enemy:
                    try:
                        set_weapons_selection(pid, enemy)
                    except Exception:
                        self.errors += 1
            # Force a fight so //damage routes fire in a bounded test (enemies
            # spawn far and close too slowly to engage within a few seconds).
            self._force_combat(sbs, player_ids[0])
            self._offset += 1
            self.steps += 1
        finally:
            FrameContext.task = prev_task
            FrameContext.mast = prev_mast

    def _pick_enemy(self, sbs, pid):
        """Nearest *damageable hostile* to `pid` (raider/enemy/monster preferred;
        else any armed non-player). None if there are none."""
        from sbs_utils.procedural.roles import any_role
        space = sbs.sim.space_objects

        def armed(i):
            o = space.get(i)
            return o is not None and (o.data_set.get("armorMax") or 0) > 0

        cand = [i for i in any_role("raider,enemy,monster") if armed(i)]
        if not cand:
            cand = [i for i in space.keys()
                    if i != pid and armed(i) and not (space[i]._abits & 0x20)]
        self.enemies_last = len(cand)
        return self._nearest(sbs, pid, cand)

    def _force_combat(self, sbs, pid):
        """Make //damage routes fire in a bounded test. Mission-spawned mock ships
        don't reliably carry beam shipData (beamRange 0), so emergent beam combat
        won't engage in a few seconds. Instead generate the hit directly via the
        mock's apply_damage, which queues the SAME engine events a real beam hit
        does (damage -> //damage; lethal -> //damage/destroy + npc/station_killed),
        so the mission's damage logic is exercised identically. (set_beam_damages
        governs beam damage when beams do fire - covered by a unit test.)"""
        e_id = self._pick_enemy(sbs, pid)
        e = sbs.sim.space_objects.get(e_id) if e_id else None
        if e is None:
            return
        armor = e.data_set.get("armor") or 0.0
        # Chip first (non-fatal -> //damage), then finish (-> //damage/destroy + killed).
        amount = 5.0 if armor > 5.0 else (armor + 1.0)
        try:
            sbs.apply_damage(e_id, amount, pid)
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
