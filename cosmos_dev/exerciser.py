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
                tid = target_ids[(self._offset + n) % len(target_ids)]
                for fn in (follow_route_select_science, follow_route_select_comms):
                    try:
                        fn(pid, tid)
                    except Exception:
                        # Route runtime errors flow to the verdict via the
                        # MastScheduler seam; count Python-level failures here.
                        self.errors += 1
            self._offset += 1
            self.steps += 1
        finally:
            FrameContext.task = prev_task
            FrameContext.mast = prev_mast
