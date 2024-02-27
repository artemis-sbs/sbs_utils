Tutorial: Creating Basic Siege
################################


Chapter
********************
Blah Blah Blah

section
========================
Blah Blah Blah


Sub section
--------------------------------
Blah Blah Blah

.. tabs::
   .. code-tab:: mast
      
        ==== start_server ====
        
            
        

   .. code-tab:: py PyMast

        import sbslibs
        

.. tabs::
   .. code-tab:: mast
      
        ==== start_server ====
        
            
        

section
========================
Blah Blah Blah


Sub section
--------------------------------
Blah Blah Blah

.. tabs::
   .. code-tab:: mast
        
     enemy_count=5
     start_text = "Mission: Basic Siege written in Mast"

   .. code-tab:: py PyMast

     def __init__(self):
          super().__init__()
          self.start_text = "Mission: Basic Siege written in PyMast"
          self.enemy_count = 5
          self.player_count = 0

        

.. tabs::
   .. code-tab:: mast
      
     if IS_SERVER:
          ->start_server 
     else: 
          # client_main is in console_select
          -> client_main
     end_if

     ========== start_server ===============

     section style="area: 50, 10, 99, 90;"
     """""{start_text}"""""

     section style="area: 60, 75, 99, 89;"

     intslider enemy_count 1.0 50.0 5.0
     row
     """ Enemies: {int(enemy_count)} """


     await choice:
     + "Start Mission":
          simulation create
          simulation resume
          -> start
     end_await
     -> start_server

        
            


   .. code-tab:: py PyMast

     @label()
    def start_server(self):
        self.gui_section("area: 0, 10, 99, 90;")
        self.gui_text(self.start_text)
        self.gui_section("area: 60, 75, 99, 89;row-height: 30px")
        slider = self.gui_slider(self.enemy_count, 0, 20, False, None)
        self.gui_row()
        text = self.gui_text(f"Enemy count: {self.enemy_count}")
        
        def on_message(__,event ):
            if event.sub_tag==slider.tag:
                self.enemy_count = int(slider.value+0.4)
                text.value = f"Enemy count: {self.enemy_count}"
                slider.value = self.enemy_count
                return True
            return False

        yield self.await_gui({
            "Start Mission": self.start
        }, on_message=on_message)


Client Console
--------------------------------
Probably need to break each step out

.. tabs::
   .. code-tab:: mast
      
      ========= client_main ==========
     event change_console:
          ->select_console
     end_event
     console = "helm"
     ship = "artemis"

     ========== select_console ==========

     ship_list = ""
     for player_ship in to_object_list(role("__PLAYER__")):
          if len(ship_list) >0:
               ship_list = ship_list + ","
          end_if
          ship_list = ship_list + player_ship.name
     next player_ship


     section style="area: 60,50, 75,90;"
     vradio ship "{ship_list}"

     section style="area: 85,50, 99,90;"
     vradio console_select "helm,weapons, comms,science,engineering"
     blank
     row
     button "accept":
          ->console_selected
     end_button

     await gui

     ->END

     ====== console_selected ====

     for player_ship in to_object_list(role("__PLAYER__")):
     if player_ship.name == ship:
          do sbs.assign_client_to_ship(client_id, player_ship.id)
     end_if
     next player_ship

     console console_select
     await gui

        
            
        

   .. code-tab:: py PyMast

     def start_client(self):
          self.watch_event("client_change", self.client_change)
          players = []
          pick_player = None
          for player in query.to_object_list(query.role("__PLAYER__")):
               players.append(player.name)
          if self.player_count != players:
               if len(players):
                    player = players[0]
                    players = ",".join(players)
                    self.gui_section("area: 25, 65, 39, 90;row-height: 45px;")
                    pick_player = self.gui_radio(players, player, True)

          self.gui_section("area: 75, 65, 99, 90;")
          console = self.gui_radio("Helm, Weapons, Comms, Engineering, Science", "Helm", True)

          def console_selected():
               pass

          yield self.await_gui({
               "Accept": console_selected
          })

          if pick_player is None:
               yield self.jump(self.start_client)

          player_name = pick_player.value
          console_sel = console.value.lower()
          # Keep running the console
          while True:
               self.assign_player_ship(player_name)
               self.gui_console(console_sel)

               yield self.await_gui({
                    "Accept": console_selected
               })
               
        

.. tabs::
     .. code-tab:: mast
      
        ================= build_world ===================

          player_ships =  ~~[ (500,0,0, "Artemis", "tsn", "tsn_battle_cruiser"),
                         (200,0,0, "Hera", "tsn", "tsn_missile_cruiser"),
                         ( 900,0,0, "Atlas", "tsn", "tsn_missile_cruiser")
          ]~~

          first = True
          for player_args in player_ships:
          player_ship = to_id(player_spawn(*player_args))
          do set_face(player_ship, random_terran())
          if first:
               do assign_client_to_ship(0,player_ship)
               first = False
          end_if
          next player_args

          stations = [(0,0,0, "Alpha"),(2400,0,100, "Beta")]
          for station in stations:
          ds = to_id(npc_spawn(*station, "tsn", "starbase_command", "behav_station"))
          do add_role(ds, "Station")
          do set_face(ds, random_terran(civilian=True))
          next station 


          enemyTypeNameList = ["kralien_dreadnaught","kralien_battleship","skaraan_defiler","cargo_ship","arvonian_carrier","torgoth_behemoth"]
          enemy_prefix = "KLMNQ"


          enemy = 0
          spawn_points = scatter_sphere(int(enemy_count), 0,0,0, 6000, 6000+250*enemy_count, ring=True)

          for v in spawn_points:
          r_type = random.choice(enemyTypeNameList)
          r_name = f"{random.choice(enemy_prefix)}_{enemy}"
          spawn_data = npc_spawn(v.x, v.y, v.z, r_name, "RAIDER", r_type, "behav_npcship")
          raider = spawn_data.py_object
          do set_face(raider.id, random_kralien())
          do add_role(raider.id, "Raider")
          enemy = enemy + 1
          next v


          # make a few random clusters of nebula
          spawn_points = scatter_sphere(random.randint(2,7), 0,0,0, 1000, 4000, ring=True)
          for v in spawn_points:
          cluster_spawn_points = scatter_sphere(random.randint(10,20), v.x, 0,v.z, 100, 1000, ring=True)
          for v2 in cluster_spawn_points:
               do terrain_spawn(v2.x, v2.y, v2.z,None, None, "nebula", "behav_nebula")
          next v2
          next v

          # make a few random clusters of Asteroids
          spawn_points = scatter_sphere(random.randint(10,20), 0,0,0, 1000, 4000, ring=True)
          asteroid_types = ship_data_asteroid_keys()
          for v in spawn_points:
          cluster_spawn_points = scatter_sphere(random.randint(10,20), v.x, 0,v.z, 100, 1000, ring=False)
          for v2 in cluster_spawn_points:
               #keep value between -500 and 500??
               v2.y = abs(v2.y) % 500 * (v2.y/abs(v2.y))
               a_type = random.choice(asteroid_types)
               #a_type = "asteroid_crystal_blue"
               do terrain_spawn(v2.x, v2.y, v2.z,None, None, a_type, "behav_asteroid")
          next v2
          next v

          # I want candy
          spawn_points = scatter_sphere(random.randint(5,12), 0,0,0, 1000, 4000, ring=True)
          for v in spawn_points:
          cluster_spawn_points = scatter.sphere(random.randrange(10,20), v.x, 0,v.z, 100, 1000, ring=False)
          # Random type, but same for cluster
          a_type = f"danger_{random.randint(1,5)}{random.choice('abc')}"
          for v2 in cluster_spawn_points:
               #keep value between -500 and 500??
               v2.y = abs(v2.y) % 500 * (v2.y/abs(v2.y))
               do terrain_spawn(v2.x, v2.y, v2.z,None, None, a_type, "behav_mine")
          next v2
          next v
          <<-

     .. code-tab:: py PyMast
     
          @label()
          def  build_world(self):
               sim = self.sim
               ## Create the player ship
               ## Returns a spawn_data so you have easy access to all data to set values
               # class SpawnData:
               # 	id: int
               # 	engine_object: any
               # 	blob: any
               # 	py_object: EngineObject
               player_ship = PlayerShip().spawn(sim,1200,0,200, "Artemis", "tsn", "tsn_battle_cruiser")
               faces.set_face(player_ship.id, faces.random_terran())
               sbs.assign_client_to_ship(0, player_ship.id)
               # Mark this as a player that does basic docking
               player_ship.py_object.add_role("basic_docking")
          
               
               stations = [(0,0,0, "Alpha"),(2400,0,100, "Beta")]
               for station in stations:
                    ds = Npc().spawn(sim, *station, "tsn", "starbase_command", "behav_station")
                    ds.py_object.add_role("Station")
                    # Mark this as a station that does builing
                    ds.py_object.add_role("station_builder")
                    faces.set_face(ds.id, faces.random_terran(civilian=True))

               
               
               enemyTypeNameList = ["kralien_dreadnaught","kralien_battleship","skaraan_defiler","cargo_ship","arvonian_carrier","torgoth_behemoth"]
               enemy_prefix = "KLMNQ"

               enemy = 0
               enemy_count = self.enemy_count
               if enemy_count <1:
                    enemy_count = 1

               spawn_points = scatter.sphere(int(enemy_count), 0,0,0, 6000, 6000+250*enemy_count, ring=True)
               
               
               for v in spawn_points:
                    r_type = random.choice(enemyTypeNameList)
                    r_name = f"{random.choice(enemy_prefix)}_{enemy}"
                    spawn_data = Npc().spawn(sim, v.x, v.y, v.z, r_name, "RAIDER", r_type, "behav_npcship")
                    raider = spawn_data.py_object
                    faces.set_face(raider.id, faces.random_kralien())
                    raider.add_role("Raider")
                    enemy = enemy + 1
                    # for player in to_object_list(role("__PLAYER__")):
                    # 	do raider.start_task("NPC_Comms", {"player": player})
                    # next player
               
               ####################
               # MAP TERRAIN	
               # make a few random clusters of nebula
               spawn_points = scatter.sphere(random.randint(2,7), 0,0,0, 1000, 4000, ring=True)
               for v in spawn_points:
                    cluster_spawn_points = scatter.sphere(random.randint(10,20), v.x, 0,v.z, 100, 1000, ring=True)
                    for v2 in cluster_spawn_points:
                         Terrain().spawn(sim, v2.x, v2.y, v2.z,None, None, "nebula", "behav_nebula")

               # make a few random clusters of Asteroids
               spawn_points = scatter.sphere(random.randint(10,20), 0,0,0, 1000, 4000, ring=True)
               asteroid_types = ship_data.asteroid_keys()
               for v in spawn_points:
                    cluster_spawn_points = scatter.sphere(random.randint(10,20), v.x, 0,v.z, 100, 1000, ring=False)
                    for v2 in cluster_spawn_points:
                         #keep value between -500 and 500??
                         v2.y = abs(v2.y) % 500 * (v2.y/abs(v2.y))
                         a_type = random.choice(asteroid_types)
                         Terrain().spawn(sim, v2.x, v2.y, v2.z,None, None, a_type, "behav_asteroid")

               # I want candy
               spawn_points = scatter.sphere(random.randint(5,12), 0,0,0, 1000, 4000, ring=True)
               for v in spawn_points:
                    cluster_spawn_points = scatter.sphere(random.randrange(10,20), v.x, 0,v.z, 100, 1000, ring=False)
                    # Random type, but same for cluster
                    a_type = f"danger_{random.randint(1,5)}{random.choice('abc')}"
                    for v2 in cluster_spawn_points:
                         #keep value between -500 and 500??
                         v2.y = abs(v2.y) % 500 * (v2.y/abs(v2.y))
                         Terrain().spawn(sim, v2.x, v2.y, v2.z,None, None, a_type, "behav_mine")


.. tabs::

     .. code-tab:: mast

          ===== start ======
          # Build the world
          ->> build_world

          log "comms"

          => task_player_docking
          #### Handled different handled in station comms
          # => task_station_building
          # Start task to watch state
          => task_end_game
          => task_npc_targeting
          => task_comms

          # This tasks ends
          ->END
                         
     .. code-tab:: py PyMast                              

          def start(self):
               sbs.create_new_sim()
               self.build_world()
               sbs.resume_sim()
               
               # Example story functions define inside the story
               self.schedule_task(self.task_end_game)
               self.schedule_task(self.task_npc_targeting)
               self.schedule_task(self.task_science_scan)
               self.schedule_task(self.task_comms)

               # Example story functions define outside the story
               self.schedule_task(task_station_building)
               self.schedule_task(task_player_docking)



.. tabs::

     .. code-tab:: mast

          ============ task_end_game ======= 
          players = role('PlayerShip')
          if len(players)==0:
               start_text = "Mission is lost!  All yer base are belong to us, dammit."
               -> start_server
          end_if

          raiders = role('Raider')
          if len(raiders)==0:
               start_text = "Mission is won!  All the enemies have been destroyed."
               -> start_server
          end_if

          delay sim 4s
          -> task_end_game


     .. code-tab:: py PyMast
                                  
          def task_end_game(self):
               #print(self.__class__)
               #-------------------------------------------------------------------------------
               if len(query.role("Raider")) <= 0:
                    # no enemy ships left in list!
                    self.start_text = "You have won!^All enemies have been destroyed."
                    sbs.pause_sim()
                    yield self.jump(self.start_server)
                    return

               #-------------------------------------------------------------------------------
               if len(query.role("__PLAYER__")) <= 0:
                    self.start_text = "All your base are belong to us. All PLayer ships have been lost!"
                    sbs.pause_sim()
                    yield self.jump(self.start_server)
                    return

               
               yield self.delay(5)
               yield self.jump(self.task_end_game)


.. tabs::

     .. code-tab:: mast

          ========== task_npc_targeting === 
          for raider in role('Raider'):
               the_target = closest(raider, role("PlayerShip"), 2000)
               if the_target is None:
                    the_target = closest(raider, role("Station"))
               end_if
               if the_target is not None:
                    do target(sim, raider, the_target, True)
               end_if
          next raider

          delay sim 5s
          -> task_npc_targeting


     .. code-tab:: py PyMast

          def task_npc_targeting(self):
          raiders = query.role('Raider')
          if len(raiders)==0:
               return

          for raider in raiders:
               the_target = query.closest(raider, query.role("__PLAYER__"), 2000)
               if the_target is None:
                    the_target = query.closest(raider, query.role("Station"))
               if the_target is not None:
                    query.target(self.sim, raider, the_target, True)

          yield self.delay(5)
          yield self.jump(self.task_npc_targeting)



.. tabs::

     .. code-tab:: mast

          =========== task_comms  ========
          # start the comms for the players and stations
          # Each ship will have its of thread for comms
          # this enables them to have a unique path
          for player in to_object_list(role('PlayerShip')):
               for ds in to_object_list(role('Station')):
                    => station_comms {"self": ds, "player": player, "torpedo_build_type": "nothing"}
               next ds
               for raider in to_object_list(role("Raider")):
                    => npc_comms {"self": raider, "player": player}
               next raider
          next player
          ->END


     .. code-tab:: py PyMast

          def task_comms(self):
               #task, player_id, npc_id_or_filter, scans ) -> None:
               players = query.role('__PLAYER__')
               for player in players:
                    self.schedule_comms(player, lambda id: query.has_role(id, "Station"), {
                         "Hail": self.comms_station_hail,
                         "Build Homing": self.comms_build_homing,
                         "Build Nuke": self.comms_build_nuke,
                         "Build EMP": self.comms_build_emp,
                         "Build Mine": self.comms_build_mine,
                    })

                    self.schedule_comms(player, lambda id: query.has_role(id, "Raider"), {
                         "Hail": self.comms_raider_hail,
                         "Taunt": ("red", self.comms_raider_taunt),
                         "Surrender": ("yellow", self.comms_raider_surrender),
                    })




.. tabs::

     .. code-tab:: mast

          ================ npc_comms ==================
          comms_id = player.comms_id #(sim)
          await self comms player:
               + "Hail":
                    have self tell player "{comms_id}! We will destroy you, disgusting Terran scum!"
               + "You're Ugly":
                    have self tell player  """You are a foolish Terran, {comms_id}.  We know that the taunt functionality is not currently implemented.^"""
               + "Surrender now":
                    have self tell player """OK we give up, {comms_id}."""
          end_await
          -> npc_comms



     .. code-tab:: py PyMast

          def comms_raider_hail(self, comms):
               comms.have_other_tell_player("We will destroy you, disgusting Terran scum!")

          def comms_raider_taunt(self, comms):
               player = comms.get_player()
               if player is None:
                    return
               text_line = f"You are a foolish Terran, { player.comms_id}.  We know that the taunt functionality is not currently implemented.^"
               comms.have_other_tell_player(text_line)

          def comms_raider_surrender(self, comms):
               comms.have_other_tell_player("We will never surrender, disgusting Terran scum!")


.. tabs::

     .. code-tab:: mast
          =============== station_comms ===============
          comms_id = player.comms_id

          await self comms player:
               + "Hail":
                    homing = self.get_engine_data(sim, "torpedo_count", sbs.TORPEDO.HOMING)
                    nuke = self.get_engine_data(sim, "torpedo_count", sbs.TORPEDO.NUKE)
                    emp = self.get_engine_data(sim, "torpedo_count", sbs.TORPEDO.EMP)
                    mine = self.get_engine_data(sim, "torpedo_count", sbs.TORPEDO.MINE)
                    have self tell player """
               Hello, {comms_id}.  We stand ready to assist.
               You have full docking privileges.
               {homing} Homing ready
               {nuke} Nuke ready
               {emp} EMP ready
               {mine} Mine ready
               {torpedo_build_type} in production.
               """
               + "Now Docking":
                    have self tell player  """We read you, {comms_id}.  We're standing by for expedited docking.^"""

               + "Hello, world":
                    have self tell player  """Hello, World"""

               + "Build Homing": 
                    have self tell player  """We read you, {comms_id}.  We will focus on homing production.^"""
                    torpedo_build_type = sbs.TORPEDO.HOMING
                    cancel build_task
                    build_task => task_station_building

               + "Build Nuke":
                    have self tell player  """We read you, {comms_id}.  We will focus on nuke production.^"""
                    torpedo_build_type= sbs.TORPEDO.NUKE
                    cancel build_task
                    build_task => task_station_building

               + "Build Emp":
                    have self tell player  """We read you, {comms_id}.  We will focus on EMP production.^"""
                    torpedo_build_type= sbs.TORPEDO.EMP
                    cancel build_task
                    build_task => task_station_building
               + "Build Mine":
                    have self tell player  """We read you, {comms_id}.  We will focus on MINE production.^"""
                    torpedo_build_type = sbs.TORPEDO.MINE
                    cancel build_task
                    build_task => task_station_building
          end_await

          -> station_comms




     .. code-tab:: py PyMast

          

          def comms_station_hail(self, comms):
               player = comms.get_player()
               other = comms.get_other()
               torpedo_type_text_name = [ "HOMING",	"NUKE",	"EMP",	"MINE" ]
               if player is None or other is None:
                    return
               blob2 = other.get_engine_data_set(self.sim)
               text_line = "Hello, " + player.comms_id + ".  We stand ready to assist.^"
               text_line += "You have full docking priviledges.^"
               text_line += "   {} Homing ready^".format(blob2.get("torpedo_count", sbs.TORPEDO.HOMING))
               text_line += "   {} Nuclear ready^".format(blob2.get("torpedo_count", sbs.TORPEDO.NUKE))
               text_line += "   {} EMP ready^".format(blob2.get("torpedo_count", sbs.TORPEDO.EMP))
               text_line += "   {} Mine ready^".format(blob2.get("torpedo_count", sbs.TORPEDO.MINE))

               torp_type = blob2.get("torpedo_build_type",0)
               if torp_type is None:
                    text_line += "We have nothing in production^"
               else:
                    text_line += "{} in production^".format(torpedo_type_text_name[torp_type])

               comms.have_other_tell_player(text_line)

          def comms_build_homing(self, comms):
               player = comms.get_player()
               other = comms.get_other()
               if player is None or other is None:
                    return
               blob2 = other.get_engine_data_set(self.sim)
          
               text_line = f"We read you, {player.comms_id}.  We will focus on homing production.^"
               blob2.set("torpedo_build_type",sbs.TORPEDO.HOMING)
               comms.have_other_tell_player(text_line)

          def comms_build_nuke(self, comms):
               player = comms.get_player()
               other = comms.get_other()
               if player is None or other is None:
                    return
               blob2 = other.get_engine_data_set(self.sim)
          
               text_line = f"We read you, {player.comms_id}.  We will focus on nuke production.^"
               blob2.set("torpedo_build_type",sbs.TORPEDO.NUKE)
               comms.have_other_tell_player(text_line)

          def comms_build_emp(self, comms):
               player = comms.get_player()
               other = comms.get_other()
               if player is None or other is None:
                    return
               blob2 = other.get_engine_data_set(self.sim)
          
               text_line = f"We read you, {player.comms_id}.  We will focus on EMP production.^"
               blob2.set("torpedo_build_type",sbs.TORPEDO.EMP)
               comms.have_other_tell_player(text_line)

          def comms_build_mine(self, comms):
               player = comms.get_player()
               other = comms.get_other()
               if player is None or other is None:
                    return
               blob2 = other.get_engine_data_set(self.sim)
          
               text_line = f"We read you, {player.comms_id}.  We will focus on mine production.^"
               blob2.set("torpedo_build_type",sbs.TORPEDO.MINE)
               comms.have_other_tell_player(text_line)



.. tabs::

     .. code-tab:: mast

          === task_station_building ===
          delay sim 10s
          ~~
          cur_count = self.get_engine_data(sim, "torpedo_count", torpedo_build_type)
          self.set_engine_data(sim, "torpedo_count", cur_count+1, torpedo_build_type)
          ~~
          have self tell player  """{comms_id}. {torpedo_build_type} Production complete."""
          ->task_station_building


     .. code-tab:: py PyMast

          def task_station_building(story):
               torpedo_type_name_list = ["Homing","Nuclear","EMP","Mine"]
               while True:
                    delay_time = 5
                    stations = query.role("station_builder")
                    # Unschedule task if no more stations
                    if len(stations) == 0:
                         break
                    #print("Station building")
                    for station_id in stations:
                         blob = query.get_engine_data_set(story.sim, station_id)
                         if blob is None:
                              continue
                    
                         station_name = blob.get("name_tag",0);

                         # check and set timer for building the current torpedo
                         torp_build_time = blob.get("torp_build_ready_time",0)
                         if None == torp_build_time: # never built a torp before
                              torp_build_time = story.sim.time_tick_counter + 30 * 10 # 10 seconds?
                              blob.set("torp_build_ready_time",torp_build_time,0)

                         if torp_build_time <= story.sim.time_tick_counter: # done building!
                              torp_type = blob.get("torpedo_build_type",0)
                              cur_count = blob.get("torpedo_count", torp_type)
                              blob.set("torpedo_count", cur_count+1, torp_type)

                              face_desc =faces.get_face(station_id)

                              text_line = "We have produced another " + torpedo_type_name_list[torp_type] + " torpedo.  We will begin work on another."
                              sbs.send_comms_message_to_player_ship(0, station_id, "green", face_desc, 
                                   station_name,  text_line)

                              torp_build_time = story.sim.time_tick_counter + 30 * 60 * 4 #-------------  4 minutes
                              blob.set("torp_build_ready_time",torp_build_time,0)
                    yield story.delay(delay_time)




.. tabs::

     .. code-tab:: mast

          ========== task_player_docking ===============
          for player in to_object_list(role("__PLAYER__")):
               do to_object(player).start_task("player_docking")
          next player
          ->END



.. tabs::

     .. code-tab:: mast

          ======== player_docking  ===================

          if not object_exists(sim, self):
               log "Docking ship died"
               ->END
          end_if
          # log "Docking ship {self.id}"

          player_blob = get_engine_data_set(sim, self)
          dock_state_string = get_data_set_value(player_blob,"dock_state", 0)

          if "undocked" == dock_state_string:
               ~~set_data_set_value(player_blob, "dock_base_id", 0)~~
               dock_rng = 600
               station = closest(self, role("Station"), 600)
               if station is not None:
                    ~~set_data_set_value(player_blob, "dock_base_id", to_id(station))~~
               end_if
          end_if

          dock_stationID = get_data_set_value(player_blob, "dock_base_id", 0)
          dock_station = to_object(dock_stationID)
          if dock_station is not None:
               if "docking" == dock_state_string:
                    
                    # check to see if the player ship is close enough to be docked
                    distanceValue = ~~sbs.distance_id(dock_station.id, self.id)~~
                    closeEnough = ~~dock_station.get_space_object(sim).exclusion_radius + self.get_space_object(sim).exclusion_radius~~
                    closeEnough = closeEnough * 1.1
                    if distanceValue <= closeEnough:
                         ~~set_data_set_value(player_blob, "dock_state", "docked")~~
                    end_if
               end_if
          end_if


          if "docked" == dock_state_string:
               dock_station_blob = get_engine_data_set(sim, dock_station)
               # refuel
               fuel_value = get_data_set_value(player_blob, "energy",0)
               fuel_value = fuel_value + 20
               if fuel_value > 1000:
                    fuel_value = 1000
               end_if
               ~~set_data_set_value(player_blob, "energy", int(fuel_value))~~

               # resupply torps
               for torps in range(sbs.TORPEDO.MINE):
                    tLeft = ~~ get_data_set_value(dock_station_blob,"torpedo_count", torps)~~
                    if tLeft > 0:
                         torp_max = get_data_set_value(player_blob,"torpedo_max", torps)
                         torp_now = get_data_set_value(player_blob,"torpedo_count", torps)
                         if torp_now < torp_max:
                              torp_now = torp_now + 1
                              ~~set_data_set_value(player_blob,"torpedo_count", torp_now,torps)~~
                              ~~set_data_set_value(dock_station_blob,"torpedo_count", tLeft-1, torps)~~
                         end_if
                    end_if
               next torps


               #repair shields (more than normal)
               shieldCoeff = ~~get_data_set_value(player_blob,"repair_rate_shields",0)~~
               systemCoeff = ~~get_data_set_value(player_blob,"repair_rate_systems",0)~~

               sCount = get_data_set_value(player_blob,"shield_count",0)
               for shield in range(sCount-1):
                    sVal = get_data_set_value(player_blob,"shield_val", shield)
                    sValMax = get_data_set_value(player_blob,"shield_max_val", shield)
                    changed = (sVal < sValMax)
                    sVal = max(0.0, min(sVal + shieldCoeff, sValMax)) # clamp the value
                    if changed:
                         ~~set_data_set_value(player_blob,"shield_val", sVal, shield)~~
                    end_if
               next shield
               #repair systems (more than normal)
               for system in range(sbs.SHPSYS.SHIELDS):
                    damage = get_data_set_value(player_blob,"system_damage", system)
                    maxDamage = get_data_set_value(player_blob,"system_max_damage", system)
                    changed = (damage > 0.0)
                    damage = max(0.0, min(damage - systemCoeff, maxDamage)) # clamp the value
                    if changed:
                         ~~set_data_set_value(player_blob,"system_damage", damage, system)~~
                    end_if
               next system
          end_if
          delay sim 5s
          -> player_docking


     .. code-tab:: py PyMast

          def task_player_docking(story):
               # self is the async story
               task_delay = 5
               while True:
                    yield story.delay(task_delay)
                    player_ships = query.role("basic_docking")
                    if len(player_ships)==0:
                         return PollResults.OK_END
                    
                    for player_ship_id in player_ships:
                         if story.sim.space_object_exists(player_ship_id):

                              player = story.sim.get_space_object(player_ship_id)
                              blob = query.get_engine_data_set(story.sim, player_ship_id)
                              
                              dock_state_string = blob.get("dock_state", 0)
                              if "undocked" == dock_state_string:
                                   #####################################
                                   ## Have task run slower
                                   
                                   blob.set("dock_base_id", 0) # clear the dock-able id

                                   dock_rng = 600

                                   closest = query.closest(player_ship_id, query.role("Station") & query.broad_test(-dock_rng + player.pos.x, -dock_rng + player.pos.z, dock_rng + player.pos.x, dock_rng + player.pos.z, 1))
                                   if closest is not None:
                                   blob.set("dock_base_id", query.to_id(closest)) # set the dock-able id of the player to this station

                              dock_station_id = blob.get("dock_base_id", 0)
                              if story.sim.space_object_exists(dock_station_id):
                                   dock_station = story.sim.get_space_object(dock_station_id)
                                   station_blob = dock_station.data_set

                                   if "docking" == dock_state_string:
                                        # check to see if the player ship is close enough to be docked
                                        distance_value = sbs.distance(dock_station, player)
                                        close_enough = dock_station.exclusion_radius + player.exclusion_radius
                                        close_enough *= 1.1
                                        if distance_value <= close_enough:
                                             blob.set("dock_state", "docked")
                                        else:
                                             print("Docking dist: " + str(distance_value) + ",       close_enough: " + str(close_enough))


                                   if "docked" == dock_state_string:
                                        ################
                                        ## Make task faster
                                        task_delay = 1
                                        # refuel
                                        fuel_value = blob.get("energy", 0)
                                        fuel_value += 20
                                        if fuel_value > 1000:
                                             fuel_value = 1000
                                        blob.set("energy", fuel_value)

                                   # resupply torps
                                   for g in range(sbs.TORPEDO.MINE):
                                        tLeft = station_blob.get("torpedo_count", g)
                                        if tLeft > 0:
                                             torp_max = blob.get("torpedo_max", g)
                                             torp_now = blob.get("torpedo_count", g)
                                             if torp_now < torp_max:
                                                  torp_now = torp_now + 1
                                                  blob.set("torpedo_count", torp_now,g)
                                                  station_blob.set("torpedo_count", tLeft-1, g)


                                   #repair shields (more than normal)
                                   shield_coeff = blob.get("repair_rate_shields",0)
                                   system_coeff = blob.get("repair_rate_systems",0)

                                   s_count = blob.get("shield_count",0)
                                   for g in range(s_count-1):
                                        s_val = blob.get("shield_val", g)
                                        s_val_max = blob.get("shield_max_val", g)
                                        changed = (s_val < s_val_max)
                                        s_val = max(0.0, min(s_val + shield_coeff, s_val_max)) # clamp the value
                                        if changed:
                                             blob.set("shield_val", s_val, g);

                                   #repair systems (more than normal)
                                   for g in range(sbs.SHPSYS.SHIELDS):
                                        damage = blob.get("system_damage", g)
                                        max_damage = blob.get("system_max_damage", g)
                                        changed = (damage > 0.0)
                                        damage = max(0.0, min(damage - system_coeff, max_damage)) # clamp the value
                                        if changed:
                                             blob.set("system_damage", damage, g)
                    yield PollResults.OK_RUN_AGAIN

