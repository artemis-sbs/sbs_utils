
#
# Possibly in the future this is generated?
#
class SpaceObjectProxy:
    @property
    def blink_state (self) -> int:
        """int, positive numbers are pulse delay, negative numbers are blink delay, 0 = normal, -1 = glow off"""
    @blink_state.setter
    def blink_state (self, arg0: int) -> None:
        """int, positive numbers are pulse delay, negative numbers are blink delay, 0 = normal, -1 = glow off"""
    @property
    def cur_speed (self) -> float:
        """float, speed of object"""
    @cur_speed.setter
    def cur_speed (self, arg0: float) -> None:
        """float, speed of object"""
    @property
    def data_set (self) -> sbs.object_data_set:
        """object_data_set, read only, refernce to the object_data_set of this particular object"""
    @property
    def data_tag (self) -> str:
        """string, name of data entry in shipData.json"""
    @data_tag.setter
    def data_tag (self, arg0: str) -> None:
        """string, name of data entry in shipData.json"""
    @property
    def exclusion_radius (self) -> float:
        """float, other objects cannot be closer to me than this distance"""
    @exclusion_radius.setter
    def exclusion_radius (self, arg0: float) -> None:
        """float, other objects cannot be closer to me than this distance"""
    @property
    def fat_radius (self) -> float:
        """float, radius of box for internal sorting calculations"""
    @fat_radius.setter
    def fat_radius (self, arg0: float) -> None:
        """float, radius of box for internal sorting calculations"""
    def forward_vector(self) -> sbs.vec3:
        """returns a vec3, a vector direction, related to which way the space object is oriented"""
    @property
    def pos (self) -> sbs.vec3:
        """vec3, position in space"""
    @pos.setter
    def pos (self, arg0: sbs.vec3) -> None:
        """vec3, position in space"""
    def right_vector(self) -> sbs.vec3:
        """returns a vec3, a vector direction, related to which way the space object is oriented"""
    @property
    def rot_quat (self) -> sbs.quaternion:
        """quaternion, heading and orientation of this object"""
    @rot_quat.setter
    def rot_quat (self, arg0: sbs.quaternion) -> None:
        """quaternion, heading and orientation of this object"""
    def set_behavior(self, arg0: str) -> None:
        """set name of behavior module
        current available behavior modules : nebula, npcship, asteroid, playership, station"""
    @property
    def side (self) -> str:
        """string, friendly to other objects on this same side; leave empty for 'no side'"""
    @side.setter
    def side (self, arg0: str) -> None:
        """string, friendly to other objects on this same side; leave empty for 'no side'"""
    @property
    def steer_pitch (self) -> float:
        """float, continuing change to heading and orientation of this object, over time"""
    @steer_pitch.setter
    def steer_pitch (self, arg0: float) -> None:
        """float, continuing change to heading and orientation of this object, over time"""
    @property
    def steer_roll (self) -> float:
        """float, continuing change to heading and orientation of this object, over time"""
    @steer_roll.setter
    def steer_roll (self, arg0: float) -> None:
        """float, continuing change to heading and orientation of this object, over time"""
    @property
    def steer_yaw (self) -> float:
        """float, continuing change to heading and orientation of this object, over time"""
    @steer_yaw.setter
    def steer_yaw (self, arg0: float) -> None:
        """float, continuing change to heading and orientation of this object, over time"""
    @property
    def tick_type (self) -> str:
        """string, name of behavior module
        current available behavior modules : nebula, npcship, asteroid, playership, station"""
    @property
    def tick_type_ID (self) -> int:
        """int32, read only, internal representation of tick_type"""
    @property
    def type (self) -> int:
        """int, 0=passive, 1=active, 2=playerShip"""
    @property
    def unique_ID (self) -> int:
        """uint64, read only, id of this particular object"""
    def up_vector(self) -> sbs.vec3:
        """returns a vec3, a vector direction, related to which way the space object is oriented"""