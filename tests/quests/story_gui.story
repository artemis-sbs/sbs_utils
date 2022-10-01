import tests/quests/bar.story


shared alisa = "ter #6d8b01 3 0;ter #6d8b01 4 1;ter #6d8b01 4 3;ter #CC9966 8 4 6 -2;ter #fff 13 0 14 -2;ter #fff 3 6;"
shared frank = "ter #f2efee 0 0;ter #f2efee 2 0;ter #f2efee 0 3;ter #fff 12 1 14 -2;ter #fff 2 6;ter #3d0463 9 0 12 4;"


long_text = """  kjlkjkljll;jl

;jljlkkhkjhkhkj
"""

learn = True


->Briefing

================== Briefing ================

area 20 10 60 90


face alisa
"""""""""""""""""""""""""""""""""
Welcome to the TSN
I'm Captain Alisa. I've been running things in this sector for 10 years. We run a tight sector.
I don't take any crap and I do not like people who lie and disobey orders out of a matter of principle.
"""""""""""""""""""""""""""""""""


row

"""""""""""""""""""""""""""""""""
Hi, I'm Captain frank. Alisa isn't that bad once you get to know her.

You're in for an adventure

Have you ever flown a spaceship?
"""""""""""""""""""""""""""""""""

face frank

section
area 60 10 100 90

blank
row
ship Battle Cruiser
row
blank
"""""""""""""""""""""""""""""""""
This is your first ship
"""""""""""""""""""""""""""""""""
blank


choices
    + "Yes.." -> YouLied if learn == True
    + "Yes.." -> YouTrained if learn == False
    + "Ready to learn" -> Learn
    + "Not interested" ->> GotoBar
    + "Exit" ->END


=================== YouLied ========

area 20 10 100 90
face alisa

""""""""""""""""""""""""""""""""""""""""""""""
I will not tolerate those who are untruthful.

You should board the next shuttle and get the hell out of my sector
"""""""""""""""""""""""""""""""""""""""""""

choices
    + "Exit" ->END


============== YouTrained =========

area 20 10 100 90

face alisa

"""""""""""""""""""""""""""""""""
Congratulations!

Your training is complete

You're ready to command your own ship.

Good luck
"""""""""""""""""""""""""""""""""

choices
    + "Exit" -> StartMission

================= StartMission ==============================

simulation create
simulation resume
->>MapStuff


==================           Learn     ===========
x = 0
area 20 20 100 40

learn = False

* "Test 1" -> Learn
* "Test 2" ->Learn
* "Test 3" -> Learn
* "Test 4" ->Learn
row
* "Test 5" -> Learn
* "Test 6" ->Learn
* "Test 7" -> Learn
* "Test 8" ->Learn
row
* "Test 9" -> Briefing
* "Test 10" -> Briefing

choices
    + "exit" ->END

====================== NoChoice ======================

->END


====================== MapStuff ======================
shared player = PlayerShip().spawn(sim, 0, 0, 0,"Artemis", "tsn", "Battle Cruiser")
shared tsn =  [Npc().spawn(sim, 1000, 0, 1000, "TSN0", "tsn", "Battle Cruiser", "behav_npcship").obj,Npc().spawn(sim ,1200, 0, 1000, "TSN1", "tsn", "Battle Cruiser", "behav_npcship").obj,Npc().spawn(sim, 1400, 0, 1000, "TSN2", "tsn", "Battle Cruiser", "behav_npcship").obj]

<<-

