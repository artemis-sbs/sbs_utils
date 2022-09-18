==main==
-> Start"

==Start==
comms @player @ship timeout 2m->NoResponse
   button "Your mother eats flies" -> Flies
   button "Your wife dances with wolves" -> Wolves

==NoFlies==
comms @player @ship timeout 2m->NoResponse
   button "Your wife dances with wolves" -> Wolves

==Flies==
tell @player @ship "{@player} I laugh in your face"
-> NoFlies"

==Wolves==
comms @player @ship
tell @player @ship "{@player} you task me"
delay 10s
tell @player @ship "{@player} ok you have me. I surrender"
->END

==NoResponse==
comms @player @ship
tell @player @ship "{@player} you have failed to get me"
delay 10s
tell @player @ship "{@player} I have won!!!"
->END

==Ask==
Tell cannot find @shop
Near cannot find @station
near @player @station 700 -> GotPrincess timeout 30s->Ask