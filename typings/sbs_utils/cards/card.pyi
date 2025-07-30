from sbs_utils.procedural.prefab import PrefabAll
from sbs_utils.vec import Vec3
def maps_card_create ():
    ...
def maps_deck_create ():
    ...
def maps_tile_map_create (min_x, min_z, tile_size_x, tile_size_z=0, y=0):
    ...
def prefab_spawn (*args, **kwargs):
    ...
def shuffle_string (s):
    ...
class Card(CardList):
    """A card is not the space objects"""
    def __init__ (self, label, data=None, cost=0):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def deal (self):
        ...
    def spawn (self, x, y, z, size_x, size_y, size_z):
        ...
class CardList(object):
    """class CardList"""
    def __init__ (self):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def deal ():
        ...
class Deck(CardList):
    """class Deck"""
    def __init__ (self, always_shuffle=False, budget=None):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def add_card (self, card, data=None, count=1, cost=0):
        ...
    def deal (self):
        ...
    def discard (self, card):
        ...
    def discard_unaffordable (self):
        ...
    def draw (self, card):
        """Draws the card specified or picks one
        
        Args:
            card (_type_): The card to draw.
        
        Returns:
            _type_: card drawn"""
    def draw_random (self):
        ...
    def shuffle (self):
        ...
    def shuffle_in_discards (self):
        ...
class Hand(CardList):
    """class Hand"""
    def __init__ (self):
        """Initialize self.  See help(type(self)) for accurate signature."""
class Pile(CardList):
    """class Pile"""
    def __init__ (self):
        """Initialize self.  See help(type(self)) for accurate signature."""
class Tilemap(CardList):
    """class Tilemap"""
    def __init__ (self, min_x, min_z, tile_size_x, tile_size_z=0, y=0):
        """Initialize self.  See help(type(self)) for accurate signature."""
    def calc_hex_points (center_x, center_z, rings, size):
        ...
    def fill (self, tile_string, layer=None, x_count=0, scale_tile=1, x_offset=0, z_offset=0, shift=0):
        """_summary_
        
        Args:
            tile_string (_type_): _description_
            layer (_type_, optional): _description_. Defaults to None.
            x_count (int, optional): _description_. Defaults to 0.
            scale_tile (int, optional): _description_. Defaults to 1.
            x_offset (int, optional): _description_. Defaults to 0.
            z_offset (int, optional): _description_. Defaults to 0.
            shift (int, optional): Offset every n line by 1/2 width. Helps simulate hex like grid with n=2. Default = 0"""
    def fill_hex_rings (self, tile_string, layer=None):
        """fill_hex_rings creates a hex map
        
        Args:
            tile_string (_type_): The string of contents
            layer (_type_, optional): name of the layer"""
    def map_deck (self, char, deck):
        ...
