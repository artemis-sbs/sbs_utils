import unittest
from sbs_utils.cards.card import maps_deck_create, maps_tile_map_create, shuffle_string

class TestMapCards(unittest.TestCase):

    
    def test_deck(self):
        asteroid_deck = maps_deck_create()
        asteroid_deck.add_card("card_terrain_asteroid")

        nebula_deck = maps_deck_create()
        nebula_deck.add_card("card_terrain_nebula")

        station_deck = maps_deck_create()
        station_deck.add_card("card_station_command")

        tile_map = maps_tile_map_create(-50_000, -50_000, 10_000)
        tile_map.map_deck("a", asteroid_deck)
        tile_map.map_deck("n", nebula_deck)
        tile_map.map_deck("s", station_deck)
        fill = shuffle_string("."*50 +"a" * 50)
        tile_map.fill(fill, x_count=10)
        # A 25 by 25 grid on the same area
        # This should deal 5 stations 10 asteroids and 10 noops 
        fill = shuffle_string("s"*5 + "a" * 6 + "."*5 )
        #
        tile_map.fill(fill, x_count=4, scale_tile=2, x_offset=10_000)

    def test_auto_shuffle(self):
        station_deck = maps_deck_create()
        station_deck.add_card("card_station_command")
        station_deck.add_card("card_station_industry")
        station_deck.add_card("card_station_science")
        station_deck.add_card("card_station_civil")
        station_deck.always_shuffle = True
        station_deck.discard_deals = False
        assert(len(station_deck.cards)==4)
        assert(len(station_deck.discards)==0)
        station_deck.deal()
        assert(len(station_deck.cards)==4)
        assert(len(station_deck.discards)==0)

    def test_auto_discard(self):
        station_deck = maps_deck_create()
        station_deck.add_card("card_station_command")
        station_deck.add_card("card_station_industry")
        station_deck.add_card("card_station_science")
        station_deck.add_card("card_station_civil")
        station_deck.always_shuffle = False
        station_deck.discard_deals = True
        assert(len(station_deck.cards)==4)
        assert(len(station_deck.discards)==0)
        station_deck.deal()
        assert(len(station_deck.cards)==3)
        assert(len(station_deck.discards)==1)

    def test_auto_discard_reshuffle_empty(self):
        station_deck = maps_deck_create()
        station_deck.add_card("card_station_command")
        station_deck.add_card("card_station_industry")
        station_deck.add_card("card_station_science")
        station_deck.add_card("card_station_civil")
        station_deck.always_shuffle = False
        station_deck.discard_deals = True
        assert(station_deck.suffle_when_empty)
        assert(len(station_deck.cards)==4)
        assert(len(station_deck.discards)==0)
        station_deck.deal()
        station_deck.deal()
        station_deck.deal()
        assert(len(station_deck.cards)==1)
        assert(len(station_deck.discards)==3)
        station_deck.deal()
        assert(len(station_deck.cards)==0)
        assert(len(station_deck.discards)==4)
        # This should rebuild and shuffle
        station_deck.deal()
        assert(len(station_deck.cards)==3)
        assert(len(station_deck.discards)==1)

    def test_budget(self):
        class Budget:
            def __init__(self, balance):
                self.balance = balance

            def buy(self, cost):
                if not self.can_afford:
                    return False
                self.balance -= cost
                return True

            def can_afford(self, cost):
                if cost> self.balance:
                    return False
                return True

        station_deck = maps_deck_create()
        station_deck.budget = Budget(1100)
        station_deck.add_card("card_station_command", cost=500)
        station_deck.add_card("card_station_industry", cost=300)
        station_deck.add_card("card_station_science", cost=100)
        station_deck.add_card("card_station_civil", cost=100)

        station_deck.always_shuffle = True
        station_deck.discard_deals = False
        assert(len(station_deck.cards)==4)
        assert(len(station_deck.discards)==0)
        station_deck.deal()
        assert(len(station_deck.cards)==4)
        assert(len(station_deck.discards)==0)
        while station_deck.budget.balance >0:
            station_deck.deal()
        assert(len(station_deck.cards)==0)