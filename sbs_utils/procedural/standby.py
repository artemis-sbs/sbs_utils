"""Engine-network culling by player proximity.

`sbs.push_to_standby_list_id` removes an object from the engine sim + network
replication while its py-side Agent (roles/links/inventory) persists - so
distant, irrelevant objects stop costing the network without losing script
state. (physics/replication iterate sim.space_objects; standby pulls the object
out of it.)

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
from sbs_utils.procedural.query import to_object_list, to_object
from sbs_utils.procedural.roles import role
from sbs_utils.procedural.links import linked_to
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
            sbs.retrieve_from_standby_list_id(oid)
            brain_resume(oid)            # no-op if the object has no brain
            _parked_pos.pop(oid, None)
        elif (not near) and not parked:
            _parked_pos[oid] = (x, y, z)
            brain_pause(oid)             # a self-brained NPC stops acting while parked
            sbs.push_to_standby_list_id(oid)


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
            ship_ids = list(linked_to(fid, "ship_list"))
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
                sbs.retrieve_from_standby_list_id(sid)
                _parked_pos.pop(sid, None)
            brain_resume(fid)
            _parked_fleets.pop(fid, None)
        elif (not near) and not parked:
            for sid in ship_ids:
                so = to_object(sid)
                sp = getattr(so, "pos", None) if so is not None else None
                if sp is not None:
                    _parked_pos[sid] = (sp.x, sp.y, sp.z)
                sbs.push_to_standby_list_id(sid)
            brain_pause(fid)          # the fleet brain stops steering parked ships
            _parked_fleets[fid] = ship_ids


def standby_cull_clear():
    """Retrieve everything parked and forget it - call before clearing a system
    on a jump, so parked terrain returns to normal space and gets despawned with
    the rest (delete-by-box only sees objects in normal space, not standby)."""
    for oid in list(_parked_pos.keys()):
        sbs.retrieve_from_standby_list_id(oid)
        brain_resume(oid)
    for fid in list(_parked_fleets.keys()):
        brain_resume(fid)            # ships already retrieved via _parked_pos above
    _parked_pos.clear()
    _parked_fleets.clear()


def standby_cull_count():
    """How many objects are currently parked (diagnostics): loose objects + fleet
    ships."""
    return len(_parked_pos)
