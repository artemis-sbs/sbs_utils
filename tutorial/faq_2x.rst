Frequently asked Questions
==================================

.. tabs::
   .. code-tab:: mast mast
      :emphasize-lines: 3
      
      # Create a space station
      ds1 = npc_spawn(1000,0,1000, "DS1", "tsn", "starbase_command", "behav_station")
      ds2 = npc_spawn(1000,0,-1000, "DS2", "tsn", "starbase_command", "behav_station")




   .. code-tab:: py PyMast
      :emphasize-lines: 3

      # Create a space station
      ds1 = Npc().spawn(self.sim, 1000,0,1000, "DS1", "tsn", "starbase_command", "behav_station")
      ds2 = Npc().spawn(self.sim, -1000,0,1000, "DS2", "tsn", "starbase_command", "behav_station")
      




Artemis 2.x scripting 
----------------------------------------------------------------------------------------------------

create (the command that creates named objects in the game)
<create type ="enemy" hullID="4001" x="50000" y="0" z="40000" angle="45" name="TB1"/>

It is Important that there is no AI in the engine or behavior string. It is all done in script by setting data in the engine data set.
e.g. 

.. tabs::
   .. code-tab:: mast mast
      :emphasize-lines: 3

      player1 = player_spawn(1000,0,1000, "Artemis", "tsn", "battle_cruiser") # behav_player is provided in spawn
	  # this next example shows how to do 'generic' objects which can be any object in cosmos
	  # mork_egg is a key in your extraShipData.json in your mission folder
	  # that points to the appropriate art files
	  # and that can be done with any of the spawns
	  player1 = player_spawn(1000,0,1000, "Artemis", "tsn", "mork_egg") 
      # Create a space station
      ds1 = npc_spawn(1000,0,1000, "DS1", "tsn", "starbase_command", "behav_station")
	  # Create an enemy
      bad_guy = npc_spawn(1000,0,-1000, "bad guy", "raider", "skaraan_enforcer", "behav_npcship")



   .. code-tab:: py PyMast
      :emphasize-lines: 3

	  player1 = Player().spawn(1000,0,1000, "Artemis", "tsn", "battle_cruiser") # behav_player is provided in spawn
      # Create a space station
      ds1 = Npc().spawn(self.sim, 1000,0,1000, "DS1", "tsn", "starbase_command", "behav_station")
	  # Create an enemy
      ds2 = Npc().spawn(self.sim, -1000,0,1000, "DS2", "tsn", "starbase_command", "behav_station")


----------------------------------------------------------------------------------------------------

create (the command that creates UNnamed objects in the game)

Create Asteroid, Nebula, mines etc.

----------------------------------------------------------------------------------------------------

destroy (the command that removes named objects from the game)

.. tabs::
   .. code-tab:: mast mast
      :emphasize-lines: 3

	  # Create an shuttle
      shuttle = npc_spawn(1000,0,-1000, "galileo", "tsn", "cargo_ship", "behav_npcship")
      
	  # delete_object removes items by id
	  # delete using variable shuttle, convert it to the
	  sbs.delete_object(to_id(shuttle))


   .. code-tab:: py PyMast
      :emphasize-lines: 3

      sbs.delete_object(to_id(some_object))



----------------------------------------------------------------------------------------------------

destroy_near (the command that removes unnamed objects from the game, if near a point)

.. tabs::
   .. code-tab:: mast mast
      :emphasize-lines: 3
      
	  id_set = broad_test(100,200,300, 400)
      for id in id_set:
	  	sbs.delete_object(id)
	  next id

	  # use roles remove only certain types
	  id_set = broad_test(100,200,300, 400) & role("Asteroid")
      for id in id_set:
	  	sbs.delete_object(id)
	  next id

	  # or use if statements
	  id_set = broad_test(100,200,300, 400)
      for id in id_set:
	    obj = to_object(id)
		if object.name == "Artemis":
	  		sbs.delete_object(id)
		end_if
	  next id

   .. code-tab:: py PyMast
      :emphasize-lines: 3

      id_set = broad_test(100,200,300, 400)
      for id in id_set:
	  	sbs.delete_object(id)

	  # use roles remove only certain types
	  id_set = broad_test(100,200,300, 400) & role("Asteroid")
      for id in id_set:
	  	sbs.delete_object(id)

	  # or use if statements
	  id_set = broad_test(100,200,300, 400)
      for id in id_set:
	    obj = to_object(id)
		if object.name == "Artemis":
	  		sbs.delete_object(id)

----------------------------------------------------------------------------------------------------

COMMAND: add_ai (the command that adds an AI decision to a neutral or enemy's brain stack, OR a monster's monster-brain stack)

NO equivalent AI is done in scripting

This should point to behavior trees etc. 



----------------------------------------------------------------------------------------------------

COMMAND: clear_ai (removes all AI decision blocks from a neutral or enemy's brain stack)

NO equivalent AI is done in scripting


----------------------------------------------------------------------------------------------------

COMMAND: direct (the command that tells a non-player ship to go somewhere or fight something)
                (also tells generics where to go)
                (this command can no longer work with ANYTHING except non-player shielded ships and generics)

NO equivalent AI is done in scripting

This should point to behavior trees etc. 


----------------------------------------------------------------------------------------------------

COMMAND: set_variable (makes or sets a named value)

Use python / mast variables

----------------------------------------------------------------------------------------------------

COMMAND: set_timer (makes or sets a named timer)

Use delay

.. tabs::
   .. code-tab:: mast mast
      :emphasize-lines: 3
      
	  	# delay 10 seconds in simulation time before doing the next command
		delay sim 10s


		# delay 10 seconds in gui time before doing the next command
		delay gui 10s



   .. code-tab:: py PyMast
      :emphasize-lines: 3

        # delay 10 seconds in simulation time before doing the next command
		yield delay(seconds=10, sim=True)
		# delay 10 seconds in gui time before doing the next command
		yield delay(seconds=10)

      


----------------------------------------------------------------------------------------------------
incoming_message (creates a Comms button to play a media file on the main screen)


Route comms to a label that eventually calls await comms

use an await comms command.

.. tabs::
   .. code-tab:: mast mast
      :emphasize-lines: 3



		comms_id = COMMS_ORIGIN.comms_id
		await comms:
			+ "Hail":
				sbs.play_music_file(arg0: str, arg1: int, arg2: int) -> None:
    	end_await
		



   .. code-tab:: py PyMast
      :emphasize-lines: 3

		TBD






big_message (creates a chapter title on main screen(s))
------------------------------------------------------------------

Use a gui or a send_story_dialog

.. tabs::
   .. code-tab:: mast mast
      :emphasize-lines: 3
      
      section style="area: 10,10,90,90;"

	  """This is the text to display"""

	  await choice:
	  	+ "Start":
	       jump start
	  end_await

	  # or a story dialog
	  sbs.send_story_dialog(client_id, "Admiral", "Ready...", face, "#333")
	  


   .. code-tab:: py PyMast
      :emphasize-lines: 3

		self.gui_section("area: 10, 10, 90, 90;")
        self.gui_text("This is the text to display")

        yield self.await_gui({
            "Start Mission": self.start
        })

		# or a story dialog
	    sbs.send_story_dialog(client_id, "Admiral", "Ready...", face, "#333")

      
      




----------------------------------------------------------------------------------------------------

end_mission (stops the mission)


gui jump present_game_screen


----------------------------------------------------------------------------------------------------

COMMAND: incoming_comms_text (sends a block of text to the Comms station)

.. tabs::
   .. code-tab:: mast mast
      :emphasize-lines: 3
      
		transmit "A Message" 
		receive  "A Message"

		# to override the face shown add a face argument
		transmit "A Message" face "..." color="white" comms_id="..."
		receive  "A Message" face "..."


		have some_object tell another_object "Message"



   .. code-tab:: py PyMast
      :emphasize-lines: 3

         def my_button(story, comms):
		     comms.transmit("A message ")
			 comms.receive("A message ")

		 
		 self.comms_message(id1, id2, "Message")






----------------------------------------------------------------------------------------------------

COMMAND: log (sends text to the mission's log file)


.. tabs::
   .. code-tab:: mast mast
      :emphasize-lines: 3
      
		logger
		logger string variable_name
		logger file "Filename"

		logger name another
		logger name another string variable_name
		logger name another file "filename"

		log "Stuff to log"
		log name another "Stuff to log"



   .. code-tab:: py PyMast
      :emphasize-lines: 3

         self.logger()
		 variable_name = self.string_logger()
		 self.file_logger("filename")

		 self.logger("another")
		 variable_name = self.string_logger("another")
		 self.file_logger("filename", "another")

		 self.log("Stuff to log")
		 self.log("Stuff to log", "another")


			

----------------------------------------------------------------------------------------------------

COMMAND: set_object_property (sets a named space object's named property to a value)



----------------------------------------------------------------------------------------------------

COMMAND: get_object_property (copies a named space object's named property to a variable)



----------------------------------------------------------------------------------------------------

COMMAND: set_fleet_property (sets a numbered enemy fleet's named property to a value)

----------------------------------------------------------------------------------------------------

COMMAND: addto_object_property (adds a value to a named space object's named property)


----------------------------------------------------------------------------------------------------

COMMAND: copy_object_property (copies a named property from one named space object to another, name1 to name2)

----------------------------------------------------------------------------------------------------

COMMAND: set_relative_position (moves one named space object (name2) to a point near another (name1), relative to name1's heading)

----------------------------------------------------------------------------------------------------

COMMAND: set_to_gm_position (moves one named space object (name) to the point specified by clicking on the game master console screen)


----------------------------------------------------------------------------------------------------

COMMAND: set_skybox_index (sets the skybox of the main screen to 0-29)


----------------------------------------------------------------------------------------------------

COMMAND: warning_popup_message (sends a very short message to the screens specified)


----------------------------------------------------------------------------------------------------

COMMAND: set_difficulty_level (overrides the difficulty level set on the server control screen)


----------------------------------------------------------------------------------------------------

COMMAND: set_player_grid_damage (changes the damage value of a ship system in the 3D grid)



----------------------------------------------------------------------------------------------------

COMMAND: play_sound_now


----------------------------------------------------------------------------------------------------

COMMAND: set_damcon_members (changes the count of team members in a specific damcon team)


----------------------------------------------------------------------------------------------------

COMMAND: set_ship_text 



----------------------------------------------------------------------------------------------------

COMMAND: start_getting_keypresses_from (sets a client console to key-active; it sends key press messages to the server)

----------------------------------------------------------------------------------------------------

COMMAND: end_getting_keypresses_from (sets a client console to NOT key-active)


----------------------------------------------------------------------------------------------------

COMMAND: set_special (changes the "specialCaptainType" and "specialShipType" variables of an AIShip, and rebuilds the scan text for the ship; also adjusts the special abilities of an AIShip)


----------------------------------------------------------------------------------------------------

COMMAND: set_side_value (changes the sideValue of a game object)


----------------------------------------------------------------------------------------------------

COMMAND: set_gm_button (adds a button to the current GM console)



----------------------------------------------------------------------------------------------------

COMMAND: set_comms_button (adds a button to all relavent comms consoles)

Route comms to a label that eventually calls await comms

use an await comms command.

.. tabs::
   .. code-tab:: mast mast
      :emphasize-lines: 3



		comms_id = COMMS_ORIGIN.comms_id
		await comms:
			+ "Hail":
				receive "{comms_id}! We will destroy you, disgusting Terran scum!"
			+ "You're Ugly":
				receive  """You are a foolish Terran, {comms_id}.  We know that the taunt functionality is not currently implemented.^"""
			+ "Surrender now":
				receive """OK we give up, {comms_id}."""
		end_await



   .. code-tab:: py PyMast
      :emphasize-lines: 3

		TBD




----------------------------------------------------------------------------------------------------

COMMAND: clear_gm_button (removes a button from the current GM console)


----------------------------------------------------------------------------------------------------

COMMAND: clear_comms_button (removes a button from all relavent comms consoles)

----------------------------------------------------------------------------------------------------

COMMAND: set_player_carried_type (defines a singleseat ship to be carried inside another PLAYER ship)



----------------------------------------------------------------------------------------------------

COMMAND: set_monster_tag_data (defines tag text for a monster)



----------------------------------------------------------------------------------------------------

COMMAND: set_named_object_tag_state (defines tag info for a named object)





----------------------------------------------------------------------------------------------------

CONDITION: if_inside_box (tests if named object is inside a rectangle in space)

----------------------------------------------------------------------------------------------------

CONDITION: if_outside_box (tests if named object is outside a rectangle in space)

----------------------------------------------------------------------------------------------------

CONDITION: if_inside_sphere (tests if named object is inside a sphere in space)

----------------------------------------------------------------------------------------------------

CONDITION: if_outside_sphere (tests if named object is outside a sphere in space)

----------------------------------------------------------------------------------------------------

CONDITION: if_distance (tests the distance between two named objects against a condition)

----------------------------------------------------------------------------------------------------

CONDITION: if_variable (tests a named variable against a condition)

----------------------------------------------------------------------------------------------------

CONDITION: if_damcon_members (tests the count of team members in a specific damcon team on a specific player ship against a condition)

----------------------------------------------------------------------------------------------------

CONDITION: if_fleet_count (tests an indexed fleet's membership count against a condition)

----------------------------------------------------------------------------------------------------

CONDITION: if_difficulty (tests the current game's difficulty level against a condition)

----------------------------------------------------------------------------------------------------

CONDITION: if_docked (tests if a player is docked with a named station)


----------------------------------------------------------------------------------------------------

CONDITION: if_player_is_targeting (tests if a player ship's weapons officer has a lock on the named object)


----------------------------------------------------------------------------------------------------

CONDITION: if_timer_finished (tests if a timer has counted down to zero yet)


----------------------------------------------------------------------------------------------------

CONDITION: if_exists (tests if named object exists right now)



----------------------------------------------------------------------------------------------------

CONDITION: if_not_exists (tests if named object does NOT exist right now)


----------------------------------------------------------------------------------------------------

CONDITION: if_object_property (tests a named space object's named property against a condition)


----------------------------------------------------------------------------------------------------

CONDITION: if_scan_level (tests a named space object's scan level (side-based) against a condition)


----------------------------------------------------------------------------------------------------

CONDITION: if_gm_key (triggers when a key is pressed on a game master console)


----------------------------------------------------------------------------------------------------

CONDITION: if_client_key (triggers when a key is pressed on a key-activated console)


----------------------------------------------------------------------------------------------------

CONDITION: if_gm_button (triggers when a button from the current GM console is clicked)

----------------------------------------------------------------------------------------------------

CONDITION: if_comms_button (triggers when a specal button from a comms console is clicked)
	

----------------------------------------------------------------------------------------------------

CONDITION: if_monster_tag_matches (tests the tags attached to a monster)

----------------------------------------------------------------------------------------------------

CONDITION: if_object_tag_matches (tests the tag source name attached to a named object)

----------------------------------------------------------------------------------------------------

CONDITION: if_in_nebula (tests a named space object's current state regarding nebulas)


----------------------------------------------------------------------------------------------------

	NOTE: Properties you can set, add, or test against:

		// values that are in the game, not actually attached to an object.  To use these, do not name the object when using "if_object_property" or similar commands.

		nebulaIsOpaque
		sensorSetting
		gameTimeLimit
		networkTickSpeed
		nonPlayerSpeed
		nonPlayerShield
		nonPlayerWeapon
		playerWeapon
		playerShields
		coopAdjustmentValue

		// new for 2.5.104; these sound volume values should range from 0.0 - 1.0
		musicObjectMasterVolume
		commsObjectMasterVolume
		soundFXVolume
	
	
			// values for everything
			positionX
			positionY
			positionZ
			deltaX
			deltaY
			deltaZ
			angle    --these 3 values will be in radians (0-2*PI), NOT degrees like every other angle in the scripting parser
			pitch 
			roll  
			
			sideValue       0 = no side, 1 = enemy (normally), 2+ = player side (normally)

			// values for GenericMeshs
				blocksShotFlag
				pushRadius 
				pitchDelta    
				rollDelta    
				angleDelta
				artScale
			
			// values for Stations
				shieldState
				canBuild
				canShoot
				canLaunchFighters
				
				missileStoresHoming
				missileStoresNuke
				missileStoresMine
				missileStoresEMP 
				missileStoresPShock
				missileStoresBeacon
				missileStoresProbe
				missileStoresTag 

			// values for ShieldedShips
				throttle
				steering
				topSpeed
				turnRate
				shieldStateFront
				shieldMaxStateFront
				shieldStateBack
				shieldMaxStateBack
				shieldsOn
				triggersMines
				systemDamageBeam
				systemDamageTorpedo
				systemDamageTactical
				systemDamageTurning
				systemDamageImpulse
				systemDamageWarp
				systemDamageFrontShield
				systemDamageBackShield
				shieldBandStrength0
				shieldBandStrength1
				shieldBandStrength2
				shieldBandStrength3
				shieldBandStrength4

			// values for Enemys
				targetPointX
				targetPointY
				targetPointZ
				hasSurrendered
				eliteAIType
				eliteAbilityBits
				eliteAbilityState
				surrenderChance (0-100)
				tauntImmunityIndex (0,1, or 2)
				
			// values for Neutrals
				exitPointX
				exitPointY
				exitPointZ

			// values for Monsters
				speed    
				health   
				maxHealth
				turnRate 
				age      
				size     

			// values for Players
				countHoming
				countNuke 
				countMine
				countECM
				energy
				warpState
				currentRealSpeed (read only)
				totalCoolant
				
				pirateRepWithStations  (if the player is a pirate, >0 means you can dock)
				
				systemCurCoolantBeam        
				systemCurCoolantTorpedo     
				systemCurCoolantTactical    
				systemCurCoolantTurning     

				systemCurCoolantImpulse    
				systemCurCoolantWarp       
				systemCurCoolantFrontShield
				systemCurCoolantBackShield 


				systemCurHeatBeam       
				systemCurHeatTorpedo    
				systemCurHeatTactical   
				systemCurHeatTurning    

				systemCurHeatImpulse    
				systemCurHeatWarp       
				systemCurHeatFrontShield
				systemCurHeatBackShield 


				systemCurEnergyBeam          
				systemCurEnergyTorpedo       
				systemCurEnergyTactical      
				systemCurEnergyTurning       

				systemCurEnergyImpulse    
				systemCurEnergyWarp       
				systemCurEnergyFrontShield
				systemCurEnergyBackShield 
