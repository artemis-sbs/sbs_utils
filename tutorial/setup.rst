Setup
===================================
Setup includes step that you need to do once, and the steps when creating a new mission.


Create the fast way
*********************
The fastest way to create a new mission that use the sbs_utils library is to use the fetch batch.

in the Artemis Cosmos missions directory run:


.. tabs::
   .. code-tab:: shell mast

    .\fetch artemis-sbs mast_starter my-new-mission    


   .. code-tab:: shell PyMast
    
    .\fetch artemis-sbs pymast_starter my-new-mission    




Running this should retrieve the boilerplate mission and place it in the my-new-mission folder

Replacing my-new-mission with the name you desire for your mission.

That should be it. Open my-new-mission\\script.py in your editor and go.
You may need to also edit description.txt to reflect your mission name etc.

Create each file
*********************
The slower way is to create all the files one ny one. 

#. create a Mission folder
#. create a story file
#. create a script.py
#. create a description.txt
#. create a sbslib.txt
#. run all_libs.bat


Create mission folder
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
To create a mission from scratch, the first step is to create a mission folder.

in the Artemis Cosmos data\\missions folder create a new folder. 

.. code-block:: shell

    mkdir 

Create a story
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Mast and PyMast use a story. create a file for the story. 

* For Mast create "story.mast". 
* For pyMast create "story.py"

.. tabs::
   .. code-tab:: mast
      
        ==== start_server ====
        """Mast Mission"""

        await choice: 
        + "Start Mission": 
          -> start
        end_await

        ===== start ======
        simulation create
        # Create your content
        simulation resume
        
            
        

   .. code-tab:: py PyMast

        import sbslibs
        import sbs
        from sbs_utils.pymast.pymaststory import PyMastStory
        
        class Story(PyMastStory):
            def start_server(self):
                self.gui_text("PyMast Mission`")

                yield self.await_gui({
                    "Start Mission": self.start
                })

            def start(self):
                sbs.create_new_sim()
                # Create your world
                sbs.resume_sim()



Create script.py
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The next step is to create a script.py in the mission folder you created.

This can be empty at the start or the library code to allow the script to run without error can be placed in it. 
This code will not run until the library is added by following the next steps.

.. tabs::
   .. code-tab:: py mast
      
        import sbslibs
        from  sbs_utils.handlerhooks import *
        from sbs_utils.gui import Gui
        from sbs_utils.mast.maststoryscheduler import StoryPage


        class MyStoryPage(StoryPage):
            story_file = "story.mast"

        Gui.server_start_page_class(MyStoryPage)
        Gui.client_start_page_class(MyStoryPage)

        

   .. code-tab:: py PyMast

        import sbslibs
        import sbs
        from sbs_utils.handlerhooks import *
        from sbs_utils.gui import Gui
        from sbs_utils.pymast.pymaststorypage import PyMastStoryPage
        from .story import Story

        class StoryPage(PyMastStoryPage):
            story = Story()

        Gui.server_start_page_class(StoryPage)
        Gui.client_start_page_class(StoryPage)


This code will add functions that have default behavior for all the handler functions Artemis Cosmos calls.

Create description.txt
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The description.txt file is used by Artemis Cosmos. 

* The first line is a category
* The second line is the description
* remaining lines are an Icon and a color for the icon

.. code-block:: text

    Learning
    Basic Siege in MAST
    58 #48f


Create sbslib.txt
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The file sbslib.txt is a way to list libraries a project (i.e. mission) has.

.. code-block:: text

    artemis-sbs sbs_utils v0.6.7


Adding the above will reference a release of sbs_utils on github.
Check for the most relevant: https://github.com/artemis-sbs/sbs_utils/releases





