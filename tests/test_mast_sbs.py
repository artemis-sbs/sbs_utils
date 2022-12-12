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

have ship approach artemis
await ship near artemis 700:
-> Test
timeout 1m 1s:
-> Test
end_await


await self near player 700:
-> Test
timeout 1m 1s:
-> Test
end_await


await self comms player:
    * "Button one":
        -> JumpLabel
    + "Button Two":
        -> JumpLabel
    + "Button Jump":
timeout 1m 1s:
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
# wait until near D2
await self near ds2 700:
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
+ "Say main":
    -> main
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


"""
#have *PlayerShip broadcast "Hello, World"


have ds1 add roles  "Station, Active"
have ds2 remove roles  "Station, Active"

ships = all "Active"
ships = all "Station"

ships = all "Station" near artemis by 700  filter(lambda score: score >= 70)
ship = closest "Station" near artemis filter(lambda ship: ship >= 70)
ship = closest "Station" near artemis filter(pick_ship)

# Roles and links
have ds1 add roles  "Station, Active"
have ds2 add roles  "Station, Active"
have all "Station" add link  "Active" to artemis
have all "Station" add link  "Active" to "PlayerShip"


==== patrol_two ========
await any "Station" filter(lambda station: station.side(sim)=="tsn"):
start:
    have all "Station" add link "Active" to self

    await self near station = closest linked "Active" distance less than 700 :
        have self tell artemis "I'm off to {comms_id(station)}"
    cancel None:
        cancel
    timeout 30m:
        log("Timed out")
        cancel
    succeed:
        have self tell artemis "I have arrived at {comms_id(station)}"
        have self remove link "Active"
        await again
    finally:
        log("finally")
    end_await
   
cancel None:
    cancel
else:
    await again
end_await




=> friendly_think {"self: friendly_1}

========== friendly_think ======
brain:
   scratchpad:
       init:
            do link(self, "Active", all("Station"))

    # Selects are in priority order
    # if the select fails it tries the next one
    # If the select yields in yield and will pickup on the next line on the next tick
    # await can yield internally (or fail, or succeed)
    select "Have orders from artemis":
        if not ordered_target:
            fail
        end_if

        if not exists(ordered_target):
            ordered_target = None
            ->FAIL # fail allows it to move to the next choice
        end_if
        -> target_enemy {"enemy": ordered_target}

    select "Have close enemy":
        enemy = closest(self, role: "Raider" within: 4000)
        -> target_enemy {"enemy": enemy}
        
        
    select "No more stations":
        active = first(self, "Active")
        if active is not None:
            ->FAIL
        end_if
        do link(self, "Active", all("Station"))
        active = first(self, "Active")
        if active is not None:
            ->FAIL
        else:
            ->SUCCEED
        end_if

    select "Patrol":
        station = closest(self,link: "Active", within: 10000)
        if station is None:
            ->FAIL
        end_if
        have self tell artemis "I'm heading to {comms_id(station)}"
        have self approach station
        await self near station 700
        if not exist(station):
            ->FAIL
        end_if
        do unlink(self, "Active", station)
        delay sim 2s

end_brain
->END

====== target_enemy =========
have self tell artemis "Targeting to {comms_id(active)}"
for _ while exists(enemy):
    if distance(self, enemy, more: 6000):
        have self tell artemis "Enemy to {comms_id(enemy)} retreated"
        ->FAIL
    end_if
    ->YIELD # return OK_RUN_AGAIN from poll
next x
have self tell artemis "Enemy to {comms_id(enemy)} destroyed"
->FAIL


==== docking_two ========

try await any "Station" filter(lambda station: station.side(sim)=="tsn"):
    have all "Station" add link  "Active" to artemis

    except None:
        await break

    try await any "Active" to artemis:

        try await for station in closest "Active" near artemis 700:

            have cargo tell artemis "I'm off to {station.commms_id(sim)}"

            except for station in closest "Enemy" near artemis 3000:

            except None:
                await break
            except destroyed station:
                await break

            else:
                have cargo tell artemis "I have arrived at {station.commms_id(sim)}"
                have station remove role "Active"
                await continue
            finally:
        end_await

        except None:
            await break

    else:
        have cargo tell artemis "I have arrived at {station.commms_id(sim)}"
        have station remove role "Active"
        await continue
    finallY:
        pass    
    end_await
end_await

########################################
await cargo near station 700:
    

abort when cargo beyond station 3000:

abort when cargo near station2 2000:

end_await

==== docking ====

await as station closest "Station" near station 700:
await cargo near station 700:
    have artemis dock station
    await artemis docked station:

    end_await
abort when cargo beyond station 3000:

end_await
have artemis dock station
await artemis docked station:

end_await


await cargo near station 700:

abort when cargo takes damage:

end_await


await cargo takes damage:

end_await

await cargo causes damage:

end_await

#####################

===== sequential_version  ====
await => not_freezing
await => not_hungry
->END

===== parallel_version  ====
get_warm => not_freezing
eat => not_hungry
await all [get_warm, eat]

->END

======= not_freezing ==========

brain:
    scratchpad:
        freezing = True

    select "Not Freezing":
        if freezing:
            ->FAIL
        else:
            ->SUCCESS
        end_if

    select "Jacket":
        has_jacket = inventory.has("Jacket")
        if has_jacket:
            await => wear_jacket
            freezing = False
            ->SUCCESS
        else:
            ->FAIL
        end_if

    select "Door":
        brain:
            scratchpad:
                door_open = False

            select "Door Open:
                if door_open:
                    ->SUCCESS
                else:
                    ->FAIL
                end_if

            select "Person open door?":
                person = closest(self, role: "Person", less: 700)
                if not person:
                    ->FAIL
                end_if
                await => ask_person_to_open_door {"person": person}
                ->SUCCEED

            select "Has key":
                key = inventory.has("Key")
                if not key:
                    ->FAIL
                end_if
                await => open_door
                ->SUCCEED

            select "Under door mat":
                doormat = get_by_name("Doormat")
                if doormat:
                    ->FAIL
                end_if
                await => search_under_doormat
                ->SUCCEED

            select "Search Garden":
                await => search_garden
                ->SUCCEED
        end_brain
end_brain
->END

======== search_under_doormat   ======
delay sim 2s
inventory.add("Key", True)
->END

======== search_garden   ======
delay sim 3s
inventory.add("Key", True)
->END

======== open_door   ======
delay sim 2s
door_open = True
->END
        
======= not_hungry ==========

brain:
    scratchpad:
        hungry = True


    select "Not Hungry":
        if hungry:
            ->FAIL
        else:
            ->SUCCEED
        end_if

    select "Has apple":
        apple = inventory.has("Apple")
        if not apple:
            ->FAIL
        end_if
        await => eat_apple
        ->SUCCEED

    select "Has banana":
        banana = inventory.has("Banana")
        if not banana:
            ->FAIL
        end_if
        await => eat_banana
        ->SUCCEED
end_brain
->END

======== eat_apple   ======
delay sim 2s
inventory.Remove("Apple")
hungry = FALSE
->END


======== eat_banana   ======
delay sim 3s
inventory.Remove("Banana")
hungry = FALSE
->END



"""