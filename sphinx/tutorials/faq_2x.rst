Frequently asked Questions
==================================




Artemis 2.x scripting 

----------------------------------------------------------------------------------------------------



<create type ="enemy" hullID="4001" x="50000" y="0" z="40000" angle="45" name="TB1"/>

----------------------------------------------------------------------------------------------------

COMMAND: create (the command that creates named objects in the game)

----------------------------------------------------------------------------------------------------

COMMAND: create (the command that creates UNnamed objects in the game)

----------------------------------------------------------------------------------------------------

COMMAND: destroy (the command that removes something named from the game)

----------------------------------------------------------------------------------------------------

COMMAND: destroy_near (the command that removes unnamed objects from the game, if near a point)

----------------------------------------------------------------------------------------------------

COMMAND: add_ai (the command that adds an AI decision to a neutral or enemy's brain stack, OR a monster's monster-brain stack)

----------------------------------------------------------------------------------------------------

COMMAND: clear_ai (removes all AI decision blocks from a neutral or enemy's brain stack)

----------------------------------------------------------------------------------------------------

COMMAND: direct (the command that tells a non-player ship to go somewhere or fight something)
                (also tells generics where to go)
                (this command can no longer work with ANYTHING except non-player shielded ships and generics)

----------------------------------------------------------------------------------------------------

COMMAND: set_variable (makes or sets a named value)

----------------------------------------------------------------------------------------------------

COMMAND: set_timer (makes or sets a named timer)

----------------------------------------------------------------------------------------------------

COMMAND: incoming_message (creates a Comms button to play a media file on the main screen)



----------------------------------------------------------------------------------------------------

COMMAND: big_message (creates a chapter title on main screen(s))


----------------------------------------------------------------------------------------------------

COMMAND: end_mission (stops the mission)




----------------------------------------------------------------------------------------------------

COMMAND: incoming_comms_text (sends a block of text to the Comms station)


----------------------------------------------------------------------------------------------------

COMMAND: log (sends text to the mission's log file)
			
			

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
