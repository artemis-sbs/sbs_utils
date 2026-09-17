"""Engine-network culling by player proximity.

`sbs.push_to_standby_list_id` suspends an object from the engine's active sim +
network replication while its py-side Agent (roles/links/inventory) persists - so
distant, irrelevant objects stop costing the network without losing script
state. (physics/replication iterate sim.space_objects; standby pulls the object
out of it.) It is a SUSPENSION, not a deletion: a standby object is still
existence-valid - `space_object_exists`/`object_exists` return True for it
(engine-confirmed) - so use `sbs.in_standby_list_id`, not `object_exists`, to
tell "docked/parked" from "destroyed".

Brains are MAST tasks independent of the sim, so a parked NPC's brain would keep
acting on a non-simulated object - so the culler pauses a parked object's brain
(`brain_pause`) and resumes it on retrieve. That makes terrain AND self-brained
NPCs/POIs *safe* to cull. A parked object isn't in normal space, so its position is
cached here.

**Cull the fighters, not the rocks.** Standby only pays off for objects that cost
the engine sim/network *continuously* - moving, brained, per-tick-replicating NPCs
and fleets. It is a poor fit for terrain:
  * Engine tick cost of passive terrain is near-zero (measured: ~100k passive agents
    held real-time; see OpenUniverse/MULTI_SYSTEM_FEASIBILITY.md).
  * Terrain replicates to a client once, then only on a forced update - so there is
    no ongoing network cost for standby to save.
  * The py-side Agent persists while parked, so standby never shrinks the Python
    heap / GC pressure regardless.
And it is net-negative for terrain: `retrieve` re-inserts the object into sim +
network, so crossing the radius re-sends parked terrain to in-range clients (a
network burst + pop-in hitch) that resident terrain never incurs. So although
terrain is *safe* to cull, prefer to leave it resident and aim the culler at active
content (`standby_cull_fleets` is the valuable path). Terrain standby is justified
only as an engine-side memory measure for genuinely dormant, far, unlikely-to-be-
visited systems - not as a per-tick or network optimization.
(Caveat: the perf run that grounds "terrain is cheap" had NO connected clients, so it
measured compute only - the NETWORK axis, which is standby's whole reason to exist,
is unmeasured. The "terrain replicates once, then only on force" model and the
`retrieve`-re-sends churn cost are *reasoned*, not measured. So the compute + heap
legs of "leave terrain resident" are solid; the network leg is a hypothesis - verify
with a client-connected run before relying on the churn-cost argument.)

Fleets are handled as a unit (`standby_cull_fleets`): a fleet's brain lives on the
fleet agent, not its ships (linked via a "ship_list" role/link), so all a fleet's
ships park/retrieve together and the one fleet brain pauses/resumes - the whole
formation goes dark when no player is near any of its ships.

Extracted from the Open Universe's culler so any large-world mission can reuse it.
Side-agnostic: proximity is measured to every `__player__`.
"""
import sbs
from sbs_utils.procedural.query import to_object_list, to_object, object_exists
from sbs_utils.procedural.roles import role
from sbs_utils.procedural.links import linked_to, unlink
from sbs_utils.procedural.brain import brain_pause, brain_resume

# id -> (x, y, z), captured when parked (parked objects aren't in normal space).
_parked_pos = {}
# fleet_id -> [ship_id, ...], the fleets whose ships are parked + brain paused.
_parked_fleets = {}


def _player_points():
    """(x,y,z) of every player, or None if there are no players."""
    players = to_object_list(role("__player__"))
    if not players:
        return None
    return [(p.pos.x, p.pos.y, p.pos.z) for p in players]


def _near_any(x, y, z, pts, r2):
    for (px, py, pz) in pts:
        dx, dy, dz = px - x, py - y, pz - z
        if dx * dx + dy * dy + dz * dz <= r2:
            return True
    return False


def _standby_push(oid):
    """Push one id to standby, but ONLY if the engine still has the object.

    `sbs.push_to_standby_list_id` IS A NULL DEREF ON A DEAD ID - it crashes the
    server, it does not raise. The engine's `PushToStandbyList(ID64)` does
    `PushToStandbyList(allMap[id])`, and for an id the container never had (or no
    longer has) `allMap[id]` is NULL; the pointer overload's only early-out is
    `if (standbyMapID[sco])`, which is 0 for null, so it falls straight through into
    `Remove(NULL)` and reads a member off address 0.
    (Measured: `SuperContainer.cpp:562`, `mov r13,[rbx+38h]` with rbx=0, reached from
    `GSPushToStandbyListID` - a Storm's Beacon server CTD, 2026-09-17.)

    The RETRIEVE side is safe by luck - same lookup, but a null takes the early-out -
    yet a missing key still inserts a null entry into the engine's two standby maps,
    so it is guarded here too (`_standby_retrieve`).

    The mock cannot substitute for this guard: it popped a missing id and did nothing.

    Returns True if the object was pushed.
    """
    if not object_exists(oid):
        return False
    sbs.push_to_standby_list_id(oid)
    return True


def _standby_retrieve(oid):
    """Retrieve one id from standby if the engine still has the object."""
    if not object_exists(oid):
        return False
    sbs.retrieve_from_standby_list_id(oid)
    return True


def standby_cull_step(candidates, radius):
    """Park candidates with no player within `radius` (out of the engine
    network); retrieve parked ones once a player comes near. `candidates` is an
    iterable of Agents (e.g. a role set); non-space agents that share a role are
    skipped. A parked self-brained NPC has its brain paused while parked."""
    pts = _player_points()
    if pts is None:
        return
    r2 = radius * radius
    for obj in candidates:
        oid = obj.id
        parked = oid in _parked_pos
        if parked:
            x, y, z = _parked_pos[oid]
        else:
            pp = getattr(obj, "pos", None)
            if pp is None:
                continue   # skip non-space agents that share a role
            x, y, z = pp.x, pp.y, pp.z
        near = _near_any(x, y, z, pts, r2)
        if near and parked:
            _standby_retrieve(oid)
            brain_resume(oid)            # no-op if the object has no brain
            _parked_pos.pop(oid, None)
        elif (not near) and not parked:
            # Push FIRST: a candidate can have been destroyed since it was handed to
            # us (a role set is a snapshot), and recording it as parked when the engine
            # no longer has it would leave an id here that retrieve/clear must carry
            # for the rest of the mission.
            if not _standby_push(oid):
                continue
            _parked_pos[oid] = (x, y, z)
            brain_pause(oid)             # a self-brained NPC stops acting while parked


def standby_cull_fleets(fleet_role, radius):
    """Park/retrieve whole fleets by proximity. A fleet (an agent with `fleet_role`
    whose ships are linked under "ship_list") is parked when no player is within
    `radius` of ANY of its ships: every ship goes to standby and the fleet's brain
    is paused (it lives on the fleet agent). It is retrieved the moment a player
    comes near. Treating the formation as one unit keeps the fleet brain from
    steering non-simulated ships."""
    pts = _player_points()
    if pts is None:
        return
    r2 = radius * radius
    for fleet in to_object_list(role(fleet_role)):
        fid = fleet.id
        parked = fid in _parked_fleets
        if parked:
            ship_ids = _parked_fleets[fid]
        else:
            # PRUNE THE DANGLING MEMBERS HERE. Links are uni-directional and there is
            # no reverse index from a target id back to the agents that link to it, so
            # deleting a ship purges it as a link OWNER and leaves every INCOMING link
            # intact (Agent._remove and Agent.remove both purge only the
            # DEAD agent's own collections). A destroyed raider therefore stays in its
            # fleet's "ship_list" as a dangling id until something resolves it - and
            # handing that id to standby is the server CTD described on _standby_push.
            ship_ids = []
            # list(), not the live set - `unlink` mutates the collection we walk.
            for sid in list(linked_to(fid, "ship_list")):
                if object_exists(sid):
                    ship_ids.append(sid)
                else:
                    unlink(fid, "ship_list", sid)
                    _parked_pos.pop(sid, None)
        if not ship_ids:
            continue
        # Near if any member ship is within radius (cached pos for parked ships).
        near = False
        for sid in ship_ids:
            if sid in _parked_pos:
                x, y, z = _parked_pos[sid]
            else:
                so = to_object(sid)
                sp = getattr(so, "pos", None) if so is not None else None
                if sp is None:
                    continue
                x, y, z = sp.x, sp.y, sp.z
            if _near_any(x, y, z, pts, r2):
                near = True
                break
        if near and parked:
            for sid in ship_ids:
                _standby_retrieve(sid)
                _parked_pos.pop(sid, None)
            brain_resume(fid)
            _parked_fleets.pop(fid, None)
        elif (not near) and not parked:
            pushed = []
            for sid in ship_ids:
                # Read the position BEFORE the push - a parked object is out of normal
                # space, so this is the last tick its position can be trusted.
                so = to_object(sid)
                sp = getattr(so, "pos", None) if so is not None else None
                at = (sp.x, sp.y, sp.z) if sp is not None else None
                # The push is what can kill the server, so it is guarded and it gates
                # everything else. A member that died between the prune above and here
                # is dropped rather than remembered as parked.
                if not _standby_push(sid):
                    unlink(fid, "ship_list", sid)
                    continue
                if at is not None:
                    _parked_pos[sid] = at
                pushed.append(sid)
            if not pushed:
                continue
            brain_pause(fid)          # the fleet brain stops steering parked ships
            _parked_fleets[fid] = pushed


def standby_cull_clear():
    """Retrieve everything parked and forget it - call before clearing a system
    on a jump, so parked terrain returns to normal space and gets despawned with
    the rest (delete-by-box only sees objects in normal space, not standby)."""
    for oid in list(_parked_pos.keys()):
        _standby_retrieve(oid)
        brain_resume(oid)
    for fid in list(_parked_fleets.keys()):
        brain_resume(fid)            # ships already retrieved via _parked_pos above
    _parked_pos.clear()
    _parked_fleets.clear()


def standby_cull_count():
    """How many objects are currently parked (diagnostics): loose objects + fleet
    ships."""
    return len(_parked_pos)


def standby_cull_reset():
    """The per-mission reset: FORGET what is parked, retrieve nothing.

    Distinct from `standby_cull_clear`, and the difference matters. `clear` is a
    GAMEPLAY call - the sim still exists, so it hands parked objects back to normal
    space first. This is the RELOAD call: the sim is gone, every id here is dead, and
    touching one is the null deref on `_standby_push`.

    `cosmos_dev` reuses one interpreter across `run_next_mission` (the engine forks a
    process per mission), so without this run 2 of a soak starts holding run 1's parked
    ids and reports them as already-parked - the classic second-run bug.
    """
    _parked_pos.clear()
    _parked_fleets.clear()


def standby_cull_parked_count():
    """Reset-ledger probe: parked loose objects + parked fleets."""
    return len(_parked_pos) + len(_parked_fleets)
