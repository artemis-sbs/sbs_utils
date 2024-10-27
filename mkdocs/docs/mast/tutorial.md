This tutorial 

## Mission structure

Missions in {{ab.ac}} are not just a single file. It takes several files. {{ab.m}} further adds a couple more files. {{ab.m}} scripts can be written once the file structure is in place.

### Mission required files

A mission script requires 

- script.py
- description.txt

The description.txt file holds information for displaying scenario select list. Which contains:

- A category when this list grows, future version will display or filter based on category. It is not used now.
- The description of the mission.
- a list of up to 6 icons and their color. {{ab.m}} missions for example show an acorn icon.

![select](../media/scenario_select.png)

The script.py file is how the {{ab.ac}} engine communicates with the scripting system.
The engine calls the function 

=== "python"

    ``` python
    def  cosmos_event_handler(sim, event):
        pass
    ```

Script writers can write there own entire from scratch python missions this way.

Libraries likes sbs_utils should help by providing reusable code to build off of.

sbs_utils can be used without {{ab.m}} and provides many low level systems to do so.

### {{ab.m}} Required files

A {{ab.m}} mission script requires a couple more files.

- description (like above)
- script.py (A specific common boilerplate version)
- story.mast
- story.json

It is recommended to start with the [script.py](https://github.com/artemis-sbs/LegendaryMissions/blob/main/script.py) from another {{ab.m}} mission like the one linked.

It provides all the code needed to load the sbs_utils library, provide a default cosmos_event_handler, and will bootstrap the {{ab.m}} runtime by running story.mast. It also provides a top level exception handler which help stop crashing the application from python and {{ab.m}} errors.

story.mast can be were your mission script is written. Later it is recommended to create a folder to hold most of mission script code.

story.json specifies the libraries and addons the mission is dependent on. Mission written using {{ab.m}} require and least the sbs_utils library. An many will also use items from the core addons created by LegendaryMissions.

To start a mission using the Secret Meeting [story.json](https://github.com/artemis-sbs/SecretMeeting/blob/main/story.json) is a good start. 

### A map

=== "{{ab.m}}"
    
    ```
    @map/first_map "Hello Cosmos"
    " This is my first map.
    ```



### {{ab.m}} Optional files

- README.md
- setup.json


### Creating a module within mission

Missions can become complex. Putting all code in story.mast is not the best method for larger projects.

On startup {{ab.m}} runtime as well as running story.mast will look for modules and load them. A module is a folder with a \__init__.mast file and any other .mast or .py files. To be included the files need to be imported by placing an import command in \__init__.mast.


See the [example folder](https://github.com/artemis-sbs/SecretMeeting/tree/main/SecretMaps) in the Secret Meeting mission.

Create a module for the mission.

- Create a folder in the mission folder
- create an \__init__.mast file
- create one or more {{ab.m}} files or python files in the folder
- add an import statement 

### Modules / Addon / Library Files

