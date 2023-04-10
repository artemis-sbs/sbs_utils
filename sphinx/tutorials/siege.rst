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