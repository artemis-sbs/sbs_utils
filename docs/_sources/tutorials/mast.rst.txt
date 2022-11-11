Adding MAST to you mission
===========================

Mast is a system Multi-Actor/Audience Story Telling.

Mast is build off of the sbs_utils library and is used in tandem with it.

Mast can be called from python script, and python can be called from Mast allowing scripters to decide when to use both.

Mast provides and new simple programming language that enables:

- Language that flows more like a narrative or film script
- Easy and rich GUIs for the pause scene and the Artemis Cosmos consoles
- a Task/State Driven system managing multiple tasks in parallel e.g. a quest with side quests
- I similar to Visual Novel systems e.g. RenPy, Inkle Ink, and Choice script

Creating a mission that uses MAST
---------------------------------

Lets create a bare bones project that will use MAST.
We will create a new mission that uses the sbs_utils library, and additionally add a file to hole the mast content.
You can break you python files into multiple py files.
Likewise, you can also have multiple mast files.
There are numerous ways to organize you can. You can do most in mast, use multiple mast 'stories', or split it across both python and mast.

This example will use one mast story in one file, and also write some code in python.


Create the basic mission files
------------------------------

Create a new mission folder

Create these files:
- script.py
- story.mast
- description.txt - This is for the cosmos menu add category, description and any icons
- sbslibs.txt - add a reference to sbs_utils to it e.g. "artemis-sbs sbs_utils v0.4"

Get sbs_utils
------------------------------
Retrieve the sbs_utils library. By using lib_install or getting the version from github


Calling lib_install
^^^^^^^^^^^^^^^^^^^^^
In the missions folder in a command line call the batch file lib_install

.\\lib_install <mission_folder> artemis-sbs sbs_utils <version>

<mission_folder> should be your mission folder e.g. first_mast
<version> should be the name of the release you use e.g. v0.4

From github
^^^^^^^^^^^^^^^^^^^^^
Navigate to https://github.com/artemis-sbs/sbs_utils/releases
download the sbs_utils_v?.sbslib for the version you wish to use.
Put the file in your mission's folder




Create the initial script
--------------------------

Create the initial script. 
This script will create a script that uses sbs_utils and its systems via hook handlers.


.. code-block:: python
    
    import sbslibs
    from  sbs_utils.handlerhooks import *
    

The script should be selectable in Artemis Cosmos. But does nothing.


Create a Mast Story GUI
------------------------
To used Mast with the Gui, derive a class from StoryPage.
This can be used as the mission class.

To make it as simple as possible, all that is needed is the class has an attribute story_file with the value that is the filename of the mast file you want to load.


.. code-block:: python

    MastStory.enable_logging()

    class MyStoryPage(StoryPage):
        story_file = "story.mast"

    Gui.server_start_page_class(MyStoryPage)
    Gui.client_start_page_class(MyStoryPage)

A lot of things are going on behind the scenes with this shot code.

1) The file story.mast is loaded and compiled
2) A Gui system for Mast content is create on the server and each of any connecting consoles
3) Each of these pages has a 'Scheduler' created that run their view of the mast content
4) The Schedulers can have 1 or more 'Task' running 

Since the mast file is empty, the scheduled task are empty and end immediately.

The mast file needs to have 



