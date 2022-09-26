shared barkeep = faces.random_torgoth()
shared alisa = "ter #6d8b01 3 0;ter #6d8b01 4 1;ter #6d8b01 4 3;ter #CC9966 8 4 6 -2;ter #fff 13 0 14 -2;ter #fff 3 6;"
shared frank = "ter #f2efee 0 0;ter #f2efee 2 0;ter #f2efee 0 3;ter #fff 12 1 14 -2;ter #fff 2 6;ter #3d0463 9 0 12 4;"

shared martinis = 10
shared beer = 10
shared vodka = 8

learn = True


->Briefing





== Briefing == 

bounds 20 10 60 90


face alisa
text """Welcome to the TSN
I'm Captain Alisa. I've been running things in this sector for 10 years. We run a tight sector.
I don't take any crap and I do not like people who lie and disobey orders out of a matter of principle.
"""

row

text """
Hi, I'm Captain frank. Alisa isn't that bad once you get to know her.

You're in for an adventure

Have you ever flown a spaceship?
"""

face frank

section
bounds 60 10 100 90

separate
row
ship Battle Cruiser
row
separate
text """This is your first ship"""
separate

choices
    + "Yes.." -> YouLied if learn == True
    + "Yes.." -> YouTrained if learn == False
    + "Ready to learn" -> Learn
    + "Not interested" ->> GotoBar
    + "Exit" ->END


== YouLied == 

bounds 20 10 100 90
face alisa

text """
I will not tolerate those who are untruthful.

You should board the next shuttle and get the hell out of my sector
"""

choices
    + "Exit" ->END


== YouTrained == 

bounds 20 10 100 90

face alisa

text """
Congratulations!

Your training is complete

You're ready to command your own ship.

Good luck
"""

choices
    + "Exit" -> StartMission

== StartMission ==
simulation create
simulation resume

== GotoBar ==

face barkeep
text """
Thirsty?
I have 
    {martinis} Martinis
    {beer} beer
    and {vodka} vodka
"""

choices
    + "Martini"-> Martinis if martinis > 0
    + "Beer" -> Beer if beer > 0
    + "Vodka" -> Vodka if vodka > 0
    + "Had enough" <<-

==Vodka==
shared vodka = vodka-1
refresh GotoBar
->GotoBar

==Beer==
shared beer = beer-1
refresh GotoBar
->GotoBar

==Martinis==
shared martinis = martinis-1
refresh GotoBar
->GotoBar


== Learn ==
x = 0
bounds 20 20 100 40

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

== NoChoice ==
->END
