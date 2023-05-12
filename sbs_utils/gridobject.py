from __future__ import annotations
import sbs
import functools
from .engineobject import EngineObject, SpawnData, CloseData, Stuff

  

class GridObject(EngineObject):
    # roles : Stuff = Stuff()
    # _has_inventory : Stuff = Stuff()
    # has_links : Stuff = Stuff()
    # all = {}
    # removing = set()

    def __init__(self):
        super().__init__()
        self._name = ""
        self._tag =""
        self._gotype = ""


    def grid_object(self, sim):
        """ get the simulation's space object for the object

        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :return: simulation space object
        :rtype: simulation space object
        """
        hullMap: sbs.hullmap
        hullMap = sim.get_hull_map(self.host_id)
        return  hullMap.get_grid_object_by_id(self.id)
        
    def set_name(self, sim, name):
        """ Set the name of the object

        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :param name: The object name
        :type str: The object name
        """
        go : sbs.grid_object
        go = self.grid_object(sim)
        if go is None:
            return ""
        self._name = name
        go.name = name

    def set_tag(self, sim, tag):
        """ Set the name of the object

        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :param name: The object name
        :type str: The object name
        """
        go : sbs.grid_object
        go = self.grid_object(sim)
        if go is None:
            return ""
        self._tag = tag
        go.tag = tag

    @property
    def name(self: GridObject) -> str:
        """str, cached version of name"""
        return self._name
    
    @property
    def tag(self: GridObject) -> str:
        """str, cached version of tag"""
        return self._tag
    
    @property
    def gotype(self: GridObject) -> str:
        """str, cached version of type"""
        return self._gotype

    @property
    def comms_id(self: GridObject) -> str:
        """str, cached version of comms_id"""
        return f"{self._name}({self._gotype})"

    def update_blob(self, sim:sbs.simulation, speed=None, icon_index=None, icon_scale=None, color=None):
        go = self.grid_object(sim)
        if go is None:
            return

        blob = go.data_set
        # blob.set("curx", x, 0)
        # blob.set("cury", y, 0)
        # blob.set("lastx", x, 0)
        # blob.set("lasty", y, 0)
        # blob.set("percent", 1.0, 0)
        if speed is not None:
            blob.set("move_speed", speed, 0)
        if icon_index is not None:
            blob.set("icon_index", icon_index, 0)
        if icon_scale is not None:
            blob.set("icon_scale", icon_scale, 0)
        if color is not None:
            blob.set("icon_color", color , 0)

    def get_engine_object(self, sim):
        """ Gets the simulation space object

        :param sim: The simulation
        :type sim: Artemis Cosmos simulation
        :return: The simulation space object
        :rtype: The simulation space_object
        """
        return self.grid_object(sim)
    
    
    def spawn(self, sim:sbs.simulation, host_id, name, tag, x, y, icon_index, color,  go_type=None):
        self.host_id = host_id
        hullMap: sbs.hullmap
        hullMap = sim.get_hull_map(self.host_id)
        if go_type is None:
            go_type = self.__class__.__name__
        if isinstance(go_type, str):
            roles = go_type.split(",")
            go_type = roles[0].strip()
        else:
            roles = go_type
            go_type = roles[0].strip()

        self._name = name
        self._tag = tag
        go : sbs.grid_object
        go   = hullMap.create_grid_object(name, tag, go_type)
        self.id = go.unique_ID
        self.add()
        for role in roles:
            self.add_role(role)
        self.add_role(self.__class__.__name__)
        self.add_role("__grid_spawned__")
        self.add_role("__GRID_OBJECT__")

        blob = go.data_set
        blob.set("curx", x, 0)
        blob.set("cury", y, 0)
        blob.set("lastx", x, 0)
        blob.set("lasty", y, 0)
        blob.set("percent", 1.0, 0)
        blob.set("move_speed", 0, 0)
        blob.set("icon_index", icon_index, 0)
        blob.set("icon_scale", 1.0, 0)
        blob.set("icon_color", color , 0)

