from mock import sbs as sbs # not sure why I need this
import unittest

import  sbs_utils.procedural.data as prodecural_data


class TestProcedural(unittest.TestCase):

    def test_data_templates(self):

        taunt1 = { "data": {
                    "_thing": ["courage", "wardrobe", "money", "companions"],
                    "_amount": ["ten times", "so much more than"],
                    "_insult": ["Lepusian mud mouse", "whale spit"]
                    }
                }

        
        taunt = {
            "data":{
                "_gender": {"pronoun": ["he", "she", "they"],
                            "possessive": ["his", "her", "their", ],
                           },
                "_relationship": ["wife", "husband", "spouse", "children", "daughter", "son"],
                "_attack": ["crush your skull", "rip out your heart" ]
            },
            "button": "Taunt spouse",
            "transmit": "You are so ugly, your spouse will thank me for killing you.",
            "failure": "I'm not married, excrement face.",
            "success": "I shall crush your skull with my bare hands for insulting my spouse, {name}!",
            "science": "The captain and their spouse have a very stable, loving relationship."
        }

        result = prodecural_data.data_choose_value_from_template(taunt["data"])

        assert(result != taunt1)

        
        

        

