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
            sys.stdout.write("..")
            return None
        
        #print(f"spawn {self.label} {x},{y}, {z}")
        sys.stdout.write(f"{self.label}")
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


    def fill(self, tile_string, layer=None, x_count=0, scale_tile=1, x_offset=0, z_offset=0):
        # Convert to on long string
        # calculate the line length if needed
        # Replace spaces and tabs
        tile_string = re.sub(r' \t', '', tile_string)
        the_split = tile_string.split("\n")
        if len(the_split) >1 and x_count==0:
            x_count = len(the_split[0])
            
        tile_string = "".join(the_split)

        cur_count = 0
        cur_x = self.min_x + x_offset
        cur_z = self.min_z + z_offset
        cur_y = self.y

        for tile in tile_string:
            if tile in self.deck_map:
                deck = self.deck_map[tile]
                card = deck.deal()
                card.spawn(cur_x, cur_y, cur_z, self.tile_size_x*scale_tile, self.tile_size_x/10, self.tile_size_z*scale_tile)
            
            cur_count += 1
            cur_x += self.tile_size_x * scale_tile
            if cur_count>= x_count:
                cur_count=0
                cur_z += self.tile_size_z * scale_tile
                cur_x = self.min_x
                sys.stdout.write("\n")


def shuffle_string(s):
    l = list(s)
    random.shuffle(l)
    return "".join(l)


def cmd_line_test():
    asteroid_deck = Deck()
    for x in range(0,6):
        asteroid_deck.add_card(Card(f"a{x+1}"))

    station_deck = Deck()
    for x in range(0,5):
        station_deck.add_card(Card(f"s{x+1}"))

    nebula_deck = Deck()
    for x in range(0,5):
        nebula_deck.add_card(Card(f"n{x+1}"))

    tile_map = Tilemap(-50_000, -50_000, 10000)
    tile_map.map_deck("a", asteroid_deck)
    tile_map.map_deck("s", station_deck)

    tile_map.map_deck("n", nebula_deck)



    from contextlib import redirect_stdout

    with open('out.txt', 'w') as f:
        with redirect_stdout(f):
            fill = shuffle_string("a"*45 + "s"*5 +"." * 50)
            tile_map.fill(fill, x_count=10)
            sys.stdout.write("\nNEBULA LAYER\n")
            fill = shuffle_string("n"*30 + "." * 70)
            tile_map.fill(fill, layer="Nebula", x_count=10)

            sys.stdout.write("\nHard coded\n")
            fill = """..........
    .a........
    .a........
    .....s....
    ..........
    ...a......
    ......a...
    ..........
    ..a..s....
    ..........
            """
            tile_map.fill(fill, x_count=10)
            


def maps_deck_create():
    return Deck()

def maps_card_create():
    return Deck()

def maps_tile_map_create(min_x, min_z, tile_size_x, tile_size_z=0, y=0):
    return Tilemap(min_x, min_z, tile_size_x, tile_size_z, y)

