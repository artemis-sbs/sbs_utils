from sbs_utils.mast.mast import Mast
from sbs_utils.mast.mastsbs import MastSbs
import unittest

Mast.enable_logging()

"""
    Target,
    Tell,
    Comms,
    Button,
    Near,
    Simulation
"""

def mast_sbs_compile(code):
    mast = MastSbs()
    errors = mast.compile(code)
    return (errors, mast)


class TestMastSbsCompile(unittest.TestCase):
    
    
    def test_compile_no_err(self):
        (errors, mast) = mast_sbs_compile( code = """
have self tell player "Hello"
have self tell player "Hello" color "black"
have self approach player
have self target player
have self broadcast "Hello, World"
have self broadcast "Hello, RGB" color "#fff"


await self near player 700 timeout 1m 1s:
-> Test
timeout:
-> Test
end_await


await self comms player timeout 1m 1s:
    * "Button one":
        -> JumpLabel
    + "Button Two":
        -> JumpLabel
    + "Button Jump": 
    timeout:
        -> JumpSomeWhere
end_await


await self comms player:
* "Button one":
    await self comms player:
    * "Button one":
        await self comms player:
        * "Button one":
            -> JumpLabel
        end_await
    end_await
end_await


""")
        if len(errors)>0:
            for err in errors:
                print(err)
        assert(len(errors) == 0)

     
    def test_compile_no_err_2(self):
        (errors, mast) = mast_sbs_compile( code ="""
# Set the comms buttons to start the 'quest'

await self comms player:
+ "Start at DS1":
 -> One
+ "Start at DS2":
 -> Two
+ "Taunt":
 -> Taunt
 end_await


== Taunt ==

await self comms player:
    * "Your mother"  color "red":
        -> Taunt
    + "Kiss my Engine"  color "green":
        -> Taunt
    + "Skip me" color "white" if x > 54:
        -> Taunt 
    * "Don't Skip me" color "white" if x < 54:
     -> Taunt 
    + "Taunt" :
        -> Taunt
end_await


== One ==
await=>HeadToDS1
await=>HeadToDS2
->One

== Two ==
await=>HeadToDS2
await=>HeadToDS1
->Two

== HeadToDS1 ==
have self approach ds1                           # Goto DS1
await self near  ds1 700:
    have self tell player  "I have arrived at ds1"   # tell the player
end_await

== HeadToDS2 ==
have self approach ds2                           # goto DS2
await self near ds2 700:                           # wait until near D2
    have self tell player "I have arrived at ds2"    # tell the player
end_await


== Start ==

await self comms player:
+ "Say Hello" :
-> Hello
+ "Say Hi":
 -> Hi
+ "Shutup":
 -> Shutup
end_await


== skip ==
have self tell player "Come to pick the princess"
await self near player 300:
    have self tell player "You have the princess goto ds1"
end_await

await player near  station 700:
    have station tell player "the princess is on ds1"
end_await

== Hello ==
have self tell player "HELLO"

await self comms player:
+ "Say Blue":
-> Blue
+ "Say Yellow":
-> Yellow
+ "Say Cyan":
-> Cyan
end_await


== Hi ==
have self tell player  "Hi"
delay 10s
-> Start

== Chat ==
have self tell player "Blah, Blah"
delay 2s
-> Chat

== Shutup ==
cancel chat

== Blue ==
have self tell player "Blue"
delay 10s
-> Start

== Yellow ==
have self tell player "Yellow"
delay 10s
-> Start

== Cyan ==
have self tell player "Cyan"
await self comms player timeout 5s:
+ "Say main": -> main
timeout:
-> TooSlow
end_await


== TooSlow ==
have self tell player "Woh too slow"
delay 10s
-> Start

""")
        if len(errors)>0:
            for err in errors:
                print(err)
        assert(len(errors) == 0)


    def test_button_set_compile_no_err_2(self):
        (errors, mast) = mast_sbs_compile( code ="""

button_set fred:
    + "Test":

end_button_set

button_set barney:
    + "Test":
end_button_set

await self comms player timeout 5s:
    button_set use fred
    button_set use barney
end_await

""")
        if len(errors)>0:
            for err in errors:
                print(err)
        assert(len(errors) == 0)

#     def test_run_tell_no_err(self):
#           (errors, runner, mast) = mast_sbs_run( code = """
#  have self tell player "Hello"
#  have self tell player "Hello" color "black"
# """)
#           if len(errors)>0:
#               for err in errors:
#                   print(err)
#           assert(len(errors) == 0)


"""
--------await self near player 700 timeout 1m 1s:----------

----------timeout:-----------------

----------end_await-----------------


await self comms player timeout 1m 1s:
* "Button one": ******

+ "Button Two":
-> JumpLabel
+ "Button Jump": 
+ "Button Push":
->> PushLabel
+ "Button Pop":
<<-
+ "Button Await 1": ****
    await => par
++++++++++++ "Button Await 1":  ****
await => par {"S":1}
+++++++++++ "Button Await 1": ******
await => par ~~ {
    "S":1
    }~~
------------- timeout:---------------
-> JumpSomeWhere
---------------end_await ----------------
"""




if __name__ == '__main__':
    try:
        unittest.main(exit=False)
    except Exception as e:
        print(e.msg)

