import random 
import sys
import re
from sbs_utils.procedural.execution import task_schedule

class CardList:
    def __init__(self):
        self.card_limit = 1

    def deal():
        pass



        
class Card(CardList):
    """
    A card is not the space objects
    """
    def __init__(self, label, cost=0):
        super().__init__()
        self.label = label
        self.cost = cost


    def deal(self):
        # Allows the card to act like a deck
        # a deck that only deals this card
        return self

    def spawn(self, x,y,z, size_x, size_y, size_z):
        if self.label == None:
            return None
        
        #print(f"spawn {self.label} {x},{y}, {z}")
        # This should return something to 
        # Like the task 
        # A task should be executed
        # on the card label
        return task_schedule(self.label, data={"START_X": x, "START_Y": y, "START_Z": z,
                "SIZE_X": size_x, "SIZE_Y": size_y, "SIZE_Z": size_z})
    


card_no_op = Card(None)



class Deck(CardList):
    def __init__(self,  always_shuffle=False, budget=None):
        super().__init__()
        self.cards = []
        self.discards = []
        self.always_shuffle = always_shuffle
        self.discard_deals = True
        self.suffle_when_empty = True
        self.budget = budget


    def add_card(self, card, count=1, cost=0):
        for _ in range(0,count):
            if isinstance(card, Card):
                self.cards.append(card)
            else:
                self.cards.append(Card(card, cost))
                

    def shuffle(self):
        if len(self.cards)<2:
            return
        random.shuffle(self.cards)

    def deal(self):
        # Default deck always shuffles deck
        # on deal
        if self.suffle_when_empty and len(self.cards)==0:
            self.shuffle_in_discards()

        if len(self.cards)>0:
            card = self.cards[0]
            if self.discard_deals:
                self.cards = self.cards[1:]
                self.discard(card)
            if self.budget is not None:
                self.budget.buy(card.cost)
                self.discard_unaffordable()
            if self.always_shuffle:
                self.shuffle()
            return card
        else:
            return card_no_op

    def shuffle_in_discards(self):
        self.cards.extend(self.discards)
        self.discards = []
        self.shuffle()
        

    def draw_random(self):
        if len(self.cards) == 0:
            return
        
        if card is None:
            card = random.choice(self.cards)
            self.draw(card)



    def draw(self, card):
        """ Draws the card specified or picks one

        Args:
            card (_type_): The card to draw.

        Returns:
            _type_: card drawn
        """
        # Default deck always shuffles deck
        # on deal

        try:
            self.cards.remove()
            if self.discard_deals:
                self.discard(card)
            if self.manage_cost:
                self.budget -= card.cost
                self.discard_unaffordable()
        except:
            pass
        
        
    def discard(self, card):
        self.discards.append(card)

    def discard_unaffordable(self):
        new_deck = []
        discards = []
        for card in self.cards:
            if self.budget.can_afford(card.cost):
                new_deck.append(card)
            else:
                discards.append(card)

        self.discards.extend(discards)
        self.cards = new_deck


class Pile(CardList):
    def __init__(self):
        super().__init__()


class Hand(CardList):
    def __init__(self):
        super().__init__()


class Tilemap(CardList):
    def __init__(self, min_x, min_z, tile_size_x, tile_size_z=0, y=0):
        super().__init__()
        if tile_size_z == 0:
            tile_size_z = tile_size_x
        self.tile_size_x = tile_size_x
        self.tile_size_z = tile_size_z
        self.y = y
        self.min_x = min_x
        self.min_z = min_z
        self.deck_map = {".": card_no_op}
        self.layers = {"_": list()}


    def map_deck(self, char, deck):
        if len(char) != 1:
            print("map deck key should be a single char")
        if char in self.deck_map:
            print("map deck Duplicated key")

        self.deck_map[char]= deck


    def fill(self, tile_string, layer=None, x_count=0, scale_tile=1, x_offset=0, z_offset=0, shift=0):
        """_summary_

        Args:
            tile_string (_type_): _description_
            layer (_type_, optional): _description_. Defaults to None.
            x_count (int, optional): _description_. Defaults to 0.
            scale_tile (int, optional): _description_. Defaults to 1.
            x_offset (int, optional): _description_. Defaults to 0.
            z_offset (int, optional): _description_. Defaults to 0.
            shift (int, optional): Offset every n line by 1/2 width. Helps simulate hex like grid with n=2. Default = 0
        """
        # Convert to on long string
        # calculate the line length if needed
        # Replace spaces and tabs
        tile_string = re.sub(r' \t', '', tile_string)
        the_split = tile_string.split("\n")
        if len(the_split) >1 and x_count==0:
            x_count = len(the_split[0])
            
        tile_string = "".join(the_split)

        cur_count = 0
        # x going right is positive
        cur_x = self.min_x + x_offset
        # z going up is negative
        # so flip z
        cur_z = self.min_z -z_offset 
        cur_y = self.y
        line = 1

        for tile in tile_string:
            if tile in self.deck_map:
                deck = self.deck_map[tile]
                card = deck.deal()
                card.spawn(cur_x, cur_y, cur_z, self.tile_size_x*scale_tile, self.tile_size_x/10, self.tile_size_z*scale_tile)
            
            cur_count += 1
            line += 1
            cur_x += self.tile_size_x * scale_tile
            
            if cur_count>= x_count:
                cur_count=0
                # remember z is paint down, from the end to start
                cur_z -= self.tile_size_z * scale_tile
                cur_x = self.min_x
                if shift>1 and line % shift == 0:
                    cur_x += (self.tile_size_x * scale_tile)/2

    def fill_hex_rings(self, tile_string, layer=None):
        """fill_hex_rings creates a hex map
        
        Args:
            tile_string (_type_): The string of contents
            layer (_type_, optional): name of the layer
        """
        # Hex fill grabs 1, 6, 12, 18, 30, 48
        pass

def shuffle_string(s):
    l = list(s)
    random.shuffle(l)
    return "".join(l)




def maps_deck_create():
    return Deck()

def maps_card_create():
    return Deck()

def maps_tile_map_create(min_x, min_z, tile_size_x, tile_size_z=0, y=0):
    return Tilemap(min_x, min_z, tile_size_x, tile_size_z, y)

