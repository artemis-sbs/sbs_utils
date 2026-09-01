from __future__ import annotations
import re
from typing import Callable
from enum import IntEnum
from .agent import Agent, SpawnData
from .helpers import FrameContext
from .procedural import ship_data as SHIP_DATA
from .vec import Vec3
from .procedural.ship_data import get_ship_data_for


# --- ASCII-only names -------------------------------------------------------------
#
# WORKAROUND, NOT A FIX, AND MEANT TO BE REVERTED. Set ASCII_NAMES = False (or delete
# the one `ascii_name()` call in set_name) the day the engine renders these correctly.
# That is the whole revert; nothing else depends on it.
#
# WHAT IT IS FOR. The engine accepts non-ASCII everywhere it was tested - name_tag
# stores and returns it byte-identical up to 2048 UTF-8 bytes, print() is fine, the GUI
# style parser accepts it, and it survives the wire. Only the RENDERER is wrong: it
# expands the UTF-8 bytes into characters, so a name draws as a long run of garbage
# (measured on screen 2026-08-30). `names.py` seeds the Kralien generator from
# alphabets containing s-circumflex and u-breve, so ~40% of Kralien names hit this.
#
# The NAME DATA IS LEFT ALONE on purpose. Folding here rather than editing names.py
# keeps the generator's flavour, covers every other source of a name - a crew typing
# one in the lobby, a game code's SHIP_LOADOUT, a mod's roster - and makes the revert a
# one-line change rather than an archaeology exercise.
#
# COST. `str.isascii()` is a flag check on the string object in CPython, not a scan, so
# the common path pays O(1) and allocates nothing. Only a name that actually contains
# non-ASCII does any work.
ASCII_NAMES = True

# Specific letters first, so a name keeps its shape: the Kralien alphabet's Esperanto
# pair, then the accented Latin most likely to arrive from a person typing one.
_NAME_FOLD = str.maketrans({
    "ŝ": "s", "Ŝ": "S",      # s-circumflex
    "ŭ": "u", "Ŭ": "U",      # u-breve
    "ĉ": "c", "Ĉ": "C",      # c-circumflex   (same Esperanto family)
    "ĝ": "g", "Ĝ": "G",      # g-circumflex
    "ĥ": "h", "Ĥ": "H",      # h-circumflex
    "ĵ": "j", "Ĵ": "J",      # j-circumflex
    "’": "'", "‘": "'",      # curly quotes
    "“": '"', "”": '"',
    "–": "-", "—": "-",      # en/em dash
    "…": "...",
})


def ascii_name(name):
    """A name the engine can draw. Returns `name` unchanged when it is already ASCII."""
    if not ASCII_NAMES or not isinstance(name, str) or name.isascii():
        return name
    folded = name.translate(_NAME_FOLD)
    if folded.isascii():
        return folded
    # Anything still outside ASCII gets decomposed (e-acute -> e) and, failing that,
    # dropped. Dropping beats a placeholder: a name is a label, and a run of '?' is
    # exactly the garbage this exists to prevent.
    import unicodedata
    folded = unicodedata.normalize("NFKD", folded)
    return folded.encode("ascii", "ignore").decode("ascii")


# --- Characters a name must never carry ------------------------------------------
#
# Separate from the ASCII workaround above, and NOT part of its revert: these are
# ASCII characters that mean something to the engine, so they corrupt whatever draws
# the name rather than merely looking wrong.
#
#   ^   The engine's LINE BREAK, and the separator in `send_client_widget_list`.
#       Backtick quoting does not neutralise it -- a caret breaks the line either
#       way, so a name carrying one splits across two lines wherever it is drawn.
#   ;   Terminates a style property. `gui_text_escape` protects the callers that
#       use it, but the common mission spelling is a hand-built `f"$text:{name};"`,
#       and there the name ends early and its tail is parsed as styling.
#   `   The delimiter `gui_text_escape` quotes values with; one inside the value
#       closes the quote.
#   Control characters, newline and tab included. Nothing downstream expects them.
#
# `:` is deliberately left alone: it is legitimate inside a name ("Home: Reborn")
# and, unlike `;`, it cannot start a new property on its own.
#
# Everything but the backtick folds to a SPACE so words stay apart ("Ares^Beta" ->
# "Ares Beta"); the backtick is dropped, matching `gui_text_escape`. Whitespace runs
# are collapsed afterwards, but ONLY for a name that actually contained one of these
# -- a name that was already clean is returned untouched, double spaces and all.
#
# COST. A compiled `search` over a short string, once per name. The clean path
# allocates nothing.
_NAME_UNSAFE_RE = re.compile(r"[\^;`\x00-\x1f\x7f]")


def safe_name(name):
    """A name safe to hand the engine: no `^`, `;`, backtick or control characters.

    Applies `ascii_name` as well, so this is the single call every name path needs.
    Returns `name` unchanged when it is a non-string (`None` is a legal name) or is
    already clean.
    """
    if not isinstance(name, str):
        return name
    if _NAME_UNSAFE_RE.search(name):
        name = _NAME_UNSAFE_RE.sub(" ", name.replace("`", ""))
        name = " ".join(name.split())
    return ascii_name(name)


class TickType(IntEnum):
    # Engine value bit 1111
    # Passive = 0x1 = Engine 
    PASSIVE = 0x01,
    TERRAIN = 0x01,
    ACTIVE = 0x10,
    NPC = 0x10,
    PLAYER = 0x20,
    ALL = 0xffff,
    #
    #
    NPC_AND_PLAYER = 0x30,
    UNKNOWN = 0


class SpaceObject(Agent):
    # roles : Stuff = Stuff()
    # _has_inventory : Stuff = Stuff()
    # has_links : Stuff = Stuff()
    # all = {}
    # removing = set()

    def __init__(self):
        super().__init__()
        self._name = ""
        self._side = ""
        self._art_id = ""
        """_art_id is deprecated. Use _ship_data_key instead."""
        self._ship_data_key = ""
        self.spawn_pos = Vec3(0,0,0)
        self.tick_type = TickType.UNKNOWN
        self._data_set = None
        self._engine_object = None
    
    @property
    def is_player(self) -> bool:
        return self.tick_type & TickType.PLAYER

    @property
    def is_npc(self) -> bool:
        return self.tick_type & TickType.ACTIVE

    @property
    def is_terrain(self) -> bool:
        return self.tick_type & TickType.PASSIVE

    @property
    def is_active(self) -> bool:
        return self.tick_type & TickType.ACTIVE

    @property
    def is_passive(self) -> bool:
        return self.tick_type & TickType.PASSIVE


    def get_space_object(self) -> SpaceObject:
        """ 
        Gets the simulation space object.

        Returns:
            SpaceObject: The simulation space object
        """

        return FrameContext.context.sim.get_space_object(self.id)

    def get_engine_object(self) -> SpaceObject:
        """ 
        Gets the simulation space object.

        Returns:
            SpaceObject: The simulation space_object
        """
        return FrameContext.context.sim.get_space_object(self.id)

    def delete_object(self):
        """
        Delete this SpaceObject **and the grid objects it hosts**.

        The native free is **deferred**: the agent is tombstoned now
        (``destroyed()`` drops it from ``Agent.all``/roles, so
        ``object_exists()``/``to_object()`` report it gone immediately) and the
        actual ``sbs.delete_object()`` runs when the event handler drains the
        queue, after every MAST task for this tick has yielded. This closes the
        use-after-free window where another task still references this object
        within the same tick. See ``delete_queue.DeleteQueue``.

        The interior goes with the ship. A grid object is an independent agent
        that only carries its host's id, so deleting the ship alone ORPHANED
        them: they stayed live with a ``host_id`` pointing at nothing, and any
        AI still walking them kept dereferencing the dead ship (LM's
        ``damcon_ai`` re-enters every 3s and reads ``obj.host_id`` on the way
        through). Nothing else owns that cleanup, so it belongs here.
        """
        from .delete_queue import DeleteQueue
        self._delete_grid_objects()
        self.destroyed()
        DeleteQueue.queue(self.id)

    def _delete_grid_objects(self):
        """Tombstone + queue every grid object hosted on this ship.

        Best-effort and deliberately quiet: a ship with no hull map (most
        non-player objects) simply has no interior to clean up, and this runs
        while something is already being torn down -- a failure here must not
        stop the ship itself from being deleted.
        """
        try:
            from .procedural.grid import grid_objects
            from .procedural.query import to_object
            for gid in grid_objects(self.id):
                go = to_object(gid)
                if go is not None:
                    go.delete_object()
        except Exception:
            pass

        
    
    

    def debug_mark_loc(sim,  x: float, y: float, z: float, name: str, color: str):
        """ 
        Adds a nav point to the location passed, if debug mode is active.

        Args:
            x (float): x location.
            y (float): y location.
            z (float): z location.
            name (str): Name of the navpoint.
            color (str): Color of the navpoint.
        Returns:
            Navpoint | None: The navpoint added, or None if debug mode is not active.
        """
        if SpaceObject.debug:
            return FrameContext.context.sim.add_navpoint(x, y, z, name, color)
        return None

    def debug_remove_mark_loc(name: str):
        """
        Delete the navpoint specified.
        Args
            name (str): The name of the navpoint to delete.
        """
        if SpaceObject.debug:
            return FrameContext.context.sim.delete_navpoint_by_name(name)
        return None

    def log(s: str) -> None:
        if SpaceObject.debug:
            print(s)

    def space_object(self) -> SpaceObject:
        """ 
        Get the simulation's space object for the object.

        Returns:
            SpaceObject: The simulation space object.
        """
        # None once the agent is tombstoned. This is the RAW pointer into memory the
        # engine frees on delete, and it is what every setter below reaches through --
        # set_name does `so.data_set.set("name_tag", ...)`, which is the ENGINE object's
        # blob, not Agent.data_set, so the guard on that property never sees it. A
        # server died on exactly that write with "name_tag" still on the stack.
        # Every caller here and in procedural/ already handles None.
        if not self._alive:
            return None
        return self._engine_object
        # return FrameContext.context.sim.get_space_object(self.id)

    def set_side(self, side):
        """ 
        Get the side of the object

        Returns:
            str: The side.
        """
        if side != self._side:
            self.remove_role(self._side)
            self.add_role(side)
            so = self.space_object()
            self._side = side
            self.update_comms_id()
            if so is not None:
                so.side = side
                FrameContext.context.sim.force_update_to_clients(self.id,0)

    def set_name(self, name) -> str:
        """
        Get the name of the object

        Returns:
            str: The name of the object.
        """
        so = self.space_object()
        name = safe_name(name)
        self._name = name
        self.update_comms_id()
        if so is None:
            return
        blob = so.data_set
        return blob.set("name_tag", name, 0)
    
    def set_art_id(self, ship_key):
        """ 
        Deprecated. Use `SpaceObject.set_ship_data_key()` instead.

        Set the ship key from shipData for this space object to change it's 3D model and art.
        Args:
            ship_key (str): The ship key.
        """
        # Delegates rather than repeating the body, so there is exactly ONE funnel every
        # hull change passes through - which is what makes the signal below trustworthy.
        self.set_ship_data_key(ship_key)

    def set_ship_data_key(self, ship_data_key):
        """ 
        Set the ship key from shipData for this space object to change it's 3D model and art.
        Args:
            ship_data_key (str): The ship key.

        Emits the ``ship_hull_changed`` signal when the key actually changes. Its data
        becomes task variables in the handler: ``SHIP_ID``, ``HULL_OLD_KEY``,
        ``HULL_NEW_KEY``. CAPS because the convention reserves that spelling for signals
        the SYSTEM emits, as against a mission's own snake_case ones.

        WHY A SIGNAL. Changing the hull re-sizes the ship's internal map, but the
        engineering grid standing in it is NOT rebuilt - and nothing in sbs_utils rebuilds
        it, because ``grid_rebuild_grid_objects`` has no caller here. Missions build the
        interior once from a ``//spawn`` route, so any hull change after that leaves a
        blank or mismatched Engineering console with nothing logged. This is the hook that
        lets a mission notice; see ``LegendaryMissions/ai/grid_ai.mast``.

        The signal is emitted, not acted on: a rebuild deletes and respawns 60-100 grid
        objects, which is far too heavy to hide inside a property setter, and the library
        has no other dependency on that function.
        """
        if ship_data_key != self._ship_data_key:
            old_key = self._ship_data_key
            so = self.space_object()
            if so is not None:
                so.data_tag = ship_data_key
                FrameContext.context.sim.force_update_to_clients(self.id,0)
            self._ship_data_key = ship_data_key
            try:
                from .procedural.signal import signal_emit
                signal_emit("ship_hull_changed", {"SHIP_ID": self.id,
                                                  "HULL_OLD_KEY": old_key,
                                                  "HULL_NEW_KEY": ship_data_key})
            except Exception:                       # noqa: BLE001
                pass            # a notification never breaks the hull change itself

    def update_comms_id(self):
        """ 
        Updates the comms ID when the name or side has changed.
        If the side of the object is empty, the comms ID is the name of the object.
        Otherwise, the comms ID is the name and side of the object in the format
        ```
        name (side)
        ```
        Returns:
            str: The comms ID.
        """

        if (self.side_display != ""):
            self._comms_id = f"{self.name} ({self.side_display})"
        else:
            self._comms_id = self.name

    @property
    def name(self: SpaceObject) -> str:
        """
        The name of the space object.
        Returns:
            str: The name.
        """
        return self._name

    @name.setter
    def name(self: SpaceObject, value: str) -> None:
        """
        Set the name of the space object.
        Args:
            value (str): The name to apply to the space object.
        """
        self.set_name(value)

    @property
    def side(self: SpaceObject) -> str:
        """
        Get the side of the space object.
        Returns:
            str: The side.
        """
        return self._side
    
    @side.setter
    def side(self: SpaceObject, value: str) -> None:
        """
        Set the side of the space object.
        Args:
            value (str): The side to apply to the space object.
        """
        self.set_side(value)

    @property
    def side_display(self: SpaceObject) -> str:
        """
        Get the display value for the object's side.
        Returns:
            str: The side
        """
        # data_set is None once the object is deleted (see Agent._alive). Fall back to
        # the cached Python side rather than raising: update_comms_id() reads this, and
        # it runs from set_name(), which a snapshot list can still reach after a delete.
        blob = self.data_set
        if blob is not None:
            test = blob.get("hull_side", 0)
            if test is not None and isinstance(test, str):
                return test
        return self._side
    
    @side_display.setter
    def side_display(self: SpaceObject, value: str) -> None:
        """
        Set the display value for the object's side.
        Args:
            value (str): The side.
        """
        blob = self.data_set
        if blob is None:
            return
        blob.set("hull_side", value, 0)


    @property
    def comms_id(self: SpaceObject) -> str:
        """
        Get the cached version of the object's comms ID.
        Returns:
            str: The comms ID.
        """
        return self._comms_id
    
    @property
    def art_id(self: SpaceObject) -> str:
        """
        Deprecated. Use `SpaceObject.ship_data_key` instead.

        Get the ship key from shipData that this space object is using.
        Returns:
            str: The ship key.
        """
        return self._ship_data_key

    @art_id.setter
    def art_id(self: SpaceObject, ship_data_key: str) -> None:
        """
        Deprecated. Use `SpaceObject.ship_data_key` instead.

        Set the ship key from shipData for this space object to change it's 3D model and art.
        Args:
            ship_data_key (str): The ship key.
        """
        self.set_ship_data_key(ship_data_key)

    @property
    def ship_data_key(self: SpaceObject) -> str:
        """
        Get the ship key from shipData that this space object is using.
        Returns:
            str: The ship key.
        """
        return self._ship_data_key
    
    @ship_data_key.setter
    def ship_data_key(self: SpaceObject, ship_data_key: str) -> None:
        """
        Set the ship key from shipData for this space object to change it's 3D model and art.
        Args:
            ship_data_key (str): The ship key.
        """
        self.set_ship_data_key(ship_data_key)

    @property
    def race(self):
        return self.origin
    
    @property
    def origin(self):
        # None once deleted -- same guard as side_display above. "no origin" is what
        # this already answers when the blob holds nothing, so a gone object gives the
        # same "nothing known" answer rather than a new one callers have never seen.
        blob = self.data_set
        if blob is None:
            return "no origin"
        test = blob.get("hull_origin", 0)
        if test is None:
            return "no origin"
        return test.lower()
    
    @origin.setter
    def origin(self: SpaceObject, value: str) -> None:
        blob = self.data_set
        if blob is None:
            return
        blob.set("hull_origin", value, 0)

    @property
    def crew(self):
        return self.get_inventory_value("__CREW__", self.origin)
    
    @crew.setter
    def crew(self: SpaceObject, value: str) -> None:
        self.set_inventory_value("__CREW__", value)


    @property
    def pos(self: SpaceObject) -> Vec3:
        """
        Get the position of the object.
        Returns:   
            Vec3: The position.
        """
        # Reading a freed object's position is the same use-after-free as writing it,
        # just quieter. None makes a caller fail where the mistake is, instead of
        # returning coordinates read out of recycled memory.
        if not self._alive:
            return None
        return Vec3(self._engine_object.pos)

    @pos.setter
    def pos(self: SpaceObject, *args):
        """
        Set the position of the object.
        Args:
            *args (tuple): A variable-length argument list. This should be a single Vec3, or up to three floats, representing the position of the object.
        """
        if not self._alive:
            return
        v = Vec3(*args)
        FrameContext.context.sim.reposition_space_object(self._engine_object, v.x, v.y, v.z)



class MSpawn:
    def spawn_common(self, obj, x, y, z, name, side, art_id):
        self.spawn_pos = FrameContext.context.sbs.vec3(x,y,z)
        self._engine_object = obj

        FrameContext.context.sim.reposition_space_object(obj, x, y, z)
        self.add()
        self.add_role(self.__class__.__name__)
        self.add_role("__SPACE_OBJECT__")
        #
        # Add default roles
        #
        ship_data = SHIP_DATA.get_ship_data_for(art_id)
        if ship_data:
            roles = ship_data.get("roles", None)
            if roles:
                self.add_role(roles)


        blob = obj.data_set
        self._data_set = blob

        if name is not None:
            # Sanitised HERE too, not only in set_name: spawn writes the blob
            # directly, so every npc_spawn/player_spawn/terrain_spawn name used to
            # miss the fold entirely.
            name = safe_name(name)
            self._name = name
            blob.set("name_tag", name, 0)

        if side is not None:
            if isinstance(side, str):
                roles = side.split(",")
            else:
                roles = side
            side = roles[0].strip().lower()
            if side != "#":
                obj.side = side
                self._side = side
            self.update_comms_id()
            for role in roles:
                self.add_role(role)
        else:
            self._comms_id = name if name is not None else f""

        # Entries merged at runtime (tagged "#mod") aren't in the engine's shipData, so this
        # freshly-created object never received the entry's art/stats. Apply them now that
        # name/side/data_set are set up. (See ship_data.mod_ship_data_process.)
        if ship_data and ship_data.get(SHIP_DATA.SHIP_DATA_MOD_KEY) is not None:
            SHIP_DATA.mod_ship_data_process(self, ship_data)

        return blob


class MSpawnPlayer(MSpawn):
    def _make_new_player(self, behave, data_id):
        self.id = FrameContext.context.sim.create_space_object(behave, data_id, TickType.PLAYER)
        self.tick_type = TickType.PLAYER
        return FrameContext.context.sim.get_space_object(self.id)

    def _spawn(self, x, y, z, name, side, art_id) -> SpawnData:
        # playerID will be a NUMBER, a unique value for every space object that you create.
        ship = self._make_new_player("behav_playership", art_id)
        blob = self.spawn_common(ship, x, y, z, name, side, art_id)
        self.add_role("__PLAYER__")
        self.add_role("__space_spawn__")
        self._ship_data_key = art_id
        return SpawnData(self.id, ship, blob, self)

    def spawn(self, x, y, z, name, side, art_id) -> SpawnData:
        """ Spawn a new player

        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :param x: x location
        :type x: float
        :param y: y location
        :type y: float
        :param z: z location
        :type z: float
        :param name: name of object
        :type name: str
        :param side: name of object
        :type side: str
        :param art_id: art id
        :type art_id: str
        :param behave_id: the simulation behavior
        :type behave_id: str
        :return: spawn data
        :rtype: SpawnData
        """
        return self._spawn(x, y, z, name, side, art_id)

    def spawn_v(self, v, name, side, art_id) -> SpawnData:
        """ Spawn a new player

        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :param v: location
        :type v: Vec3
        :param name: name of object
        :type name: str
        :param side: name of object
        :type side: str
        :param art_id: art id
        :type art_id: str

        :return: spawn data
        :rtype: SpawnData
        """
        return self.spawn(v.x, v.y, v.z, name, side, art_id)


class MSpawnActive(MSpawn):
    """
    Mixin to add Spawn as an Active
    """

    def _make_new_active(self, behave, data_id):
        self.id = FrameContext.context.sim.create_space_object(behave, data_id, TickType.ACTIVE)
        self.tick_type = TickType.ACTIVE
        return self.get_space_object()

    def _spawn(self, x, y, z, name, side, art_id, behave_id):
        ship = self._make_new_active(behave_id, art_id)
        blob = self.spawn_common(ship, x, y, z, name, side, art_id)
        self._ship_data_key = art_id
        self.add_role("__NPC__")
        self.add_role("__space_spawn__")
        return SpawnData(self.id, ship, blob, self)

    def spawn(self, x, y, z, name, side, art_id, behave_id) -> SpawnData:
        """ Spawn a new active object e.g. npc, station

        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :param x: x location
        :type x: float
        :param y: y location
        :type y: float
        :param z: z location
        :type z: float
        :param name: name of object
        :type name: str
        :param side: name of object
        :type side: str
        :param art_id: art id
        :type art_id: str
        :param behave_id: the simulation behavior
        :type behave_id: str

        :return: spawn data
        :rtype: SpawnData
        """
        return self._spawn(x, y, z, name, side, art_id, behave_id)

    def spawn_v(self, sim, v, name, side, art_id, behave_id) -> SpawnData:
        """ Spawn a new Active Object e.g. npc, station

        :param v: location
        :type v: Vec3
        :param name: name of object
        :type name: str
        :param side: name of object
        :type side: str
        :param art_id: art id
        :type art_id: str
        :param behave_id: the simulation behavior
        :type behave_id: str

        :return: spawn data
        :rtype: SpawnData
        """
        return self._spawn( v.x, v.y, v.z, name, side, art_id, behave_id)


class MSpawnPassive(MSpawn):
    """
    Mixin to add Spawn as an Passive
    """

    def _make_new_passive(self, behave, data_id):
        self.id = FrameContext.context.sim.create_space_object(behave, data_id, TickType.PASSIVE)
        self.tick_type = TickType.PASSIVE
        return self.get_space_object()

    def _spawn(self, x, y, z, name, side, art_id, behave_id) -> SpawnData:
        ship = self._make_new_passive(behave_id, art_id)
        blob = self.spawn_common(ship, x, y, z, name, side, art_id)
        self._ship_data_key = art_id
        self.add_role("__TERRAIN__")
        return SpawnData(self.id, ship, blob, self)

    def spawn(self, x, y, z, name, side, art_id, behave_id) -> SpawnData:
        """ Spawn a new passive object e.g. Asteroid, etc.

        :param x: x location
        :type x: float
        :param y: y location
        :type y: float
        :param z: z location
        :type z: float
        :param name: name of object
        :type name: str
        :param side: name of object
        :type side: str
        :param art_id: art id
        :type art_id: str
        :param behave_id: the simulation behavior
        :type behave_id: str

        :return: spawn data
        :rtype: SpawnData
        """
        return self._spawn(x, y, z, name, side, art_id, behave_id)

    def spawn_v(self, v, name, side, art_id, behave_id) -> SpawnData:
        """ Spawn a new passive object e.g. asteroid, etc.

        :param v: location
        :type v: Vec3
        :param name: name of object
        :type name: str
        :param side: name of object
        :type side: str
        :param art_id: art id
        :type art_id: str
        :param behave_id: the simulation behavior
        :type behave_id: str
        :return: spawn data
        :rtype: SpawnData
        """
        return self._spawn(v.x, v.y, v.z, name, side, art_id, behave_id)

