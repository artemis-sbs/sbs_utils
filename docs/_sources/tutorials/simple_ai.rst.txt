Tutorial: Simple AI
############################



Create mission 
======================

Create the mission from using a starter mission.


.. tabs::
   .. code-tab:: shell mast

    .\fetch artemis-sbs mast_starter simple_ai    


   .. code-tab:: shell PyMast
    
    .\fetch artemis-sbs pymast_starter simple_ai


Add more stations
======================


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
      

Add role
===============

.. tabs::
   .. code-tab:: mast mast
      :emphasize-lines: 4
      
      # Create a space station
      ds1 = npc_spawn(1000,0,1000, "DS1", "tsn", "starbase_command", "behav_station")
      ds2 = npc_spawn(1000,0,-1000, "DS2", "tsn", "starbase_command", "behav_station")
      do add_role({ds1.id, ds2.id}, "Station")


   .. code-tab:: py PyMast
      :emphasize-lines: 4

      # Create a space station
      ds1 = Npc().spawn(self.sim, 1000,0,1000, "DS1", "tsn", "starbase_command", "behav_station")
      ds2 = Npc().spawn(self.sim, 1000,0,-1000, "DS2", "tsn", "starbase_command", "behav_station")
      query.add_role({ds1.id, ds2.id}, "Station")
      



Add a task to run AI
======================


.. tabs::
   .. code-tab:: mast mast
          :emphasize-lines: 1

      ========== task_npc_targeting =========



   .. code-tab:: py PyMast
    :emphasize-lines: 1-3

      @label()
      def task_npc_targeting(self):
         pass


Schedule the task
======================


.. tabs::
   .. code-tab:: mast mast
      :emphasize-lines: 13

      ======== start ======
      simulation resume
      # Create the world here

      # Create a space station
      ds1 = npc_spawn(1000,0,1000, "DS1", "tsn", "starbase_command", "behav_station")
      ds2 = npc_spawn(1000,0,-1000, "DS2", "tsn", "starbase_command", "behav_station")
      do add_role({ds1.id, ds2.id}, "Station")

      # Create an enemy
      k001 = npc_spawn(-1000,0,1000, "K001", "raider", "kralien_dreadnaught", "behav_npcship")

      schedule task_npc_targeting

      <<-



   .. code-tab:: py PyMast
    :emphasize-lines: 13

      @label()
      def start(self):
        # Create the world here

        # Create a space station
        ds1 = Npc().spawn(self.sim, 1000,0,1000, "DS1", "tsn", "starbase_command", "behav_station")
        ds2 = Npc().spawn(self.sim, 1000,0,-1000, "DS2", "tsn", "starbase_command", "behav_station")
        query.add_role({ds1.id, ds2.id}, "Station")

        # Create an enemy
        k001 = Npc().spawn(self.sim, -1000,0,1000, "K001", "raider", "kralien_dreadnaught", "behav_npcship")

        self.schedule_task(self.task_npc_targeting)

        sbs.resume_sim()
        yield self.jump(self.end_game)





Add a task to run AI
======================


.. tabs::
   .. code-tab:: mast mast
      :emphasize-lines: 2-5

      ========== task_npc_targeting =========
      raiders = role('raider')
      if len(raiders)==0:
         ->END
      end_if



   .. code-tab:: py PyMast
    :emphasize-lines: 3-5

      @label()
      def task_npc_targeting(self):
        raiders = query.role('raider')
        if len(raiders)==0:
            return



Add a task to run AI
======================


.. tabs::
   .. code-tab:: mast mast
      :emphasize-lines: 7-14

      ========== task_npc_targeting =========
      raiders = role('raider')
      if len(raiders)==0:
         ->END
      end_if

      for raider in raiders:
         the_target = closest(raider, role("__PLAYER__"), 2000)
         if the_target is None:
            the_target = closest(raider, role("Station"))
         end_if
         if the_target is not None:
            do target(sim, raider, the_target, True)
         end_if
      next raider

      delay sim 5s
      jump task_npc_targeting


   .. code-tab:: py PyMast
    :emphasize-lines: 7-12

      @label()
      def task_npc_targeting(self):
        raiders = query.role('raider')
        if len(raiders)==0:
            return

        for raider in raiders:
            the_target = query.closest(raider, query.role("__PLAYER__"), 2000)
            if the_target is None:
                the_target = query.closest(raider, query.role("Station"))
            if the_target is not None:
                query.target(self.sim, raider, the_target, True)



Have task run again
======================

.. tabs::
   .. code-tab:: mast mast
      :emphasize-lines: 17-18

      ========== task_npc_targeting =========
      raiders = role('raider')
      if len(raiders)==0:
         ->END
      end_if

      for raider in raiders:
         the_target = closest(raider, role("__PLAYER__"), 2000)
         if the_target is None:
            the_target = closest(raider, role("Station"))
         end_if
         if the_target is not None:
            do target(sim, raider, the_target, True)
         end_if
      next raider

      delay sim 5s
      jump task_npc_targeting


   .. code-tab:: py PyMast
      :emphasize-lines: 14-15
    
      @label()
      def task_npc_targeting(self):
        raiders = query.role('raider')
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
