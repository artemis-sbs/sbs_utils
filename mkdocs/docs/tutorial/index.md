# MAST Tutorial
A tutorial describing how to write a simple mission that utilizes many of the tools MAST has to offer.
## Tutorial Goals
### General Goals
Upon completion of this tutorial, you will have learned to:
1. [Create a new mission from a template](#1-setting-up-your-first-mission)
2. [Update the name and description of your mission](#2-whats-in-a-name)
3. [Understand what a 'label' is in MAST](#3-a-brief-overview-of-labels)
4. [Spawn player ships](#4-spawning-player-ships)
5. [Spawn terrain](#5-spawning-terrain)
6. [Spawn enemies](#6-spawning-enemies)
7. [Utilizing Roles]
8. [Add science scans[
9. [Detect damage and destruction[
10. [Build comms buttons[

### Specific Goals
For this tutorial, we are writing a mission about finding and recovering a lost treasure.  
The players will need to fight off scavengers while they search.  
They will need to scan asteroids to find the treasure.  
They will need to shoot at the asteroid to remove debris from the treasure.  
They will need to collect the treasure by giving instructions to a specialist team retrieve it.

### What you will NOT learn
MAST is loosely based on, and for Cosmos is compiled by, Python. Python is a popular programming language which integrates with the Cosmos game engine to allow for flexible mission scripting. This tutorial is not a python tutorial, and we will touch on some aspects of the language, but if you want a more thorough understanding of python there are loads of resources online.

## 1. Setting up your first mission

### Fetch or Download mast_starter
To download the basic template documents for any mission, start with the mast_starter mission from the [mast_starter Github Repository](https://github.com/artemis-sbs/mast_starter)


For a mission that already has some very basic functionality included, you could also use [Secret Meeting](https://github.com/artemis-sbs/SecretMeeting). This mission is packaged with Cosmos by default, but there may be an updated version on GitHub, and it is always recommended that the most recent version be used.

For this tutorial, we will assume that you are using mast_starter as a template.  


## 2. What's in a name?
The name of your mission is, of course, a pretty important part of the mission.  
Fortunately, it's easy to set the name and description of the mission.  
Name the mission folder to reflect the name you've chosen for your mission. We will be calling our mission "Treasure Hunt".  
Now, open `description.txt` in your mission folder. There are at least three lines in this text file.
You will see something like this:
```
Standard
Mast Mission Template
116 #F0D56E 
147 #9da36c
```
The first line is the name of your mission, as it appears in the mission selection button.  
The second line is the mission's description, as it appears in the mission selection button.  
The third line and onwards describe icons that appear on the mission selection button.  
The number at the start of the line is one of the icons from `grid_icon_sheet.png`, located in the `/data/graphics/` folder of the artemis cosmos directory. From left to right, top to bottom, the icon's number increments from 1 onwards. 
The second set of seemingly random characters is a hexidecimal color code. You can find hex codes online easily.

Once you've changed these to fit what you want, we can close `description.txt` and open `story.mast` instead:
```python
# Use for startup logic
@map/first_map "Hello Cosmos"
" This is my first map.
```
`story.mast` is where the bulk of your mission will eventually go, but right now, we're only concerned with the line that starts with `@map`.  
A line starting with `@map` defines a label, which we will get into more later. It tells the game that this is a mission, and what its name is.
In our case we want to change the name of the map from "Hello Cosmos" to our chosen mission name - "Treasure Hunt". Note that this is displayed separately from the information in `description.txt`. The name and description in `information.txt` are displayed on the button to select the mission. The name and description shown in the UI after selecting the mission are defined here in `story.mast`.  
The `/first_map` part of the label is used internally by the MAST interpreter, but isn't relevant to us at the moment. You may choose to change this to whatever you want, but it cannot have spaces or special characters in it.  
The line following the label definition is the label description:
```python
" This is my first map.
```
This line, and any subsequent lines that begin with a double quote, comprise the description.
For our example we will replace the existing description with this:
```python
" Find the treasure, if you can! Many have sought this long-lost piece of history.
" None have succeeded. Some say it is only a myth. But recent archaeological finds have
" given clues regarding the location of this mysterious artifact.
```
Now if you open Cosmos and select the Treasure Hunt mission, you will see the mission title and description.  

## 3. A brief overview of Labels
A label, at its most basic, is a _reusable_ and _schedulable_ section of code. A label is used by MAST to create at task, and that task can be scheduled to run at a particular time, under specific conditions, and more than once, if desired. This gives mission writers a great deal of flexibility.  
### Label Types
There are multiple kinds of labels:
    - Media Labels
    - Map Labels
    - Route Labels
    - Main Labels
    - Inline Labels (also known as sublabels)
We've already encountered a map label - `@map/first_map "Treasure Hunt"` Media labels are very similar in syntax and meaning. They start with `@media`, followed by the type of media, followed by the desired filename or directory. Note that the name at the end, unlike that of a map label, currently has no bearing on the mission.
```
@media/music/default "Cosmos Default Music"
@media/skybox/sky1-bored-alice "borealis"
```
This will set the mission's music and skybox to whichever you specify. If you use more than one, a random skybox or music will be used.
We will cover route labels in sections 7 and 8, so we will focus now on the last two types of labels.
Main labels (which will hereafter be referred to as just labels) are the mainstay of a mission. Let's dissect the following example:
````python
== Hello_Cosmos
" This is an example label
metadata: ```
some_data: 10
```
````
The first line defines a label's name. A label has two or more equals signs at the start of the line. It may have any number of spaces, followed by the name of the label. The name may contain any number, letter, or underscore, but may not begin with a number. It may then be followed by any number of spaces, and any number of equals signs at the end.
All of the following are valid label definitions, with the same name:
```
== Hello_Cosmos
======Hello_Cosmos==
===               Hello_Cosmos                 ==========
```
Though do note that labels must have unique names, so if you tried to include the above exactly, it would cause errors.
Sublabels have the same rules, but use a minus sign:
```
---- some_sublabel
```
The second line in our label example above you will recognize from the map labels - it is a description of the label. This is mostly used for documentation purposes, so that you (and any mission writer who might be trying to learn from your mission) can more easily follow the intent and use of the label.  
The third line and onwards defines the metadata associated with this label. Within the set of triple backticks, you can define keys, and set the default value for that key. This is very useful, because when you schedule a task, you can include different values for each key. This allows a label to not only run multiple times, but use different information while doing so.
For both main and sublabels, the description and metadata lines are optional.  
You might be able to guess what is special about sublabels. They are defined inside of a main label, and are only applicable to the their parent label. Sublabels with the same parent may not share a name, but if their parent labels are different, sublabel names can be reused.

## 4. Spawning Player Ships
Moving on from all that technical stuff, let's get into actual mission writing! … Which requires some technical stuff.  
You've learned that labels are used by MAST to create a task. Well, it turns out that it's time to do so.
```python
await task_schedule(spawn_players)
```
Wait, is it that simple? Yeah, it really is! But what does all this do? What does it mean?
Let's start with `task_schedule(spawn_players)`. `task_schedule()` is a python function (if you're not sure what a function is, do a google search). It takes a label as an argument, and builds a task from that label. "But, wait!" I hear you interrupt. "Where is `spawn_players` defined?"  
That's a great question. Let's take a brief detour and open `story.json` in your mission folder. You'll see something like this:
```json
{
    "sbslib": [
        "artemis-sbs.sbs_utils.v1.0.4.sbslib"
    ],
    "mastlib": [
        "artemis-sbs.LegendaryMissions.autoplay.v1.0.4.mastlib",
        "artemis-sbs.LegendaryMissions.ai.v1.0.4.mastlib",
        "artemis-sbs.LegendaryMissions.commerce.v1.0.4.mastlib",
        "artemis-sbs.LegendaryMissions.comms.v1.0.4.mastlib",
        "artemis-sbs.LegendaryMissions.consoles.v1.0.4.mastlib",
        "artemis-sbs.LegendaryMissions.damage.v1.0.4.mastlib",
        "artemis-sbs.LegendaryMissions.docking.v1.0.4.mastlib",
        "artemis-sbs.LegendaryMissions.fleets.v1.0.4.mastlib",
        "artemis-sbs.LegendaryMissions.grid_comms.v1.0.4.mastlib",
        "artemis-sbs.LegendaryMissions.hangar.v1.0.4.mastlib",
        "artemis-sbs.LegendaryMissions.internal_comms.v1.0.4.mastlib",
        "artemis-sbs.LegendaryMissions.operator.v1.0.4.mastlib",
        "artemis-sbs.LegendaryMissions.science_scans.v1.0.4.mastlib",
        "artemis-sbs.LegendaryMissions.side_missions.v1.0.4.mastlib",
        "artemis-sbs.LegendaryMissions.upgrades.v1.0.4.mastlib",
        "artemis-sbs.LegendaryMissions.zadmiral.v1.0.4.mastlib"
    ]
}
```
The sbslib file listed is the groundwork of MAST and is required for any mission.
The mastlib files, on the other hand, are entire optional. They contain, in this example, all of the contents of the LegendaryMissions mission folder, and are referred to as "addons". You can remove any of them, but until you've learned more about mission writing you should not. These files contain all the information about the different consoles, enemy and friendly AI, upgrades, and more, and as such they comprise the core of the default Cosmos gameplay experience. However, these are made up of MAST files, including labels that can be utilized by us, as mission writers. The `spawn_players` label is defined in [LegendaryMissions/fleets/map_common.mast](https://github.com/artemis-sbs/LegendaryMissions/blob/main/fleets/map_common.mast), if you want to take a look at it.  

But let's get back to our own mission. We've looked at task_schedule(spawn_players), but there's another part of this line that's important. The line begins with `await`. `await` tells MAST to pause the current task (our mission) until the completion of the `spawn_players` task. Without using `await`, the new task would run concurrently with our mission's current task. We want to make sure that the player ships have spawned before we continue with our task, and `await` does this quite handily.

## 5. Spawning Terrain
So we've got player ships and nothing else on the map right now. Let's add some terrain. For our mission, we want to have an asteroid field. One of these asteroids will contain the treasure.  
There's a couple of ways we could spawn a bunch of randomly placed asteroids. For now, we will utilize the same method used in the SecretMeeting mission.  
It starts by generating the locations:
```python
cluster_spawn_points = scatter_box(200,  0,0,0, 10000,1000,10000, True)
```
This generates 200 points in a random location between the location inside of a cube bounded by the points 0,0,0 and 10000,10000,10000. There are other functions that can be used, such as scatter_arc(), scatter_sphere(), and so on.

To spawn an asteroid, `terrain_spawn()` function.
```python
asteroid = terrain_spawn(point.x, point.y, point.z,None, "#,asteroid", a_type, "behav_asteroid")
```
Now, you'll notice there are some variables provided to this function that we haven't yet defined. The `point` variable is represents a 3-dimensional vector, or Vec3, that has `x`, `y`, and `z` attributes. We get these Vec3 objects from the `cluster_spawn_points` variable.  
`a_type` is the asteroid type. These can be found in `shipData.json`, but there's a simpler way:
```python
asteroid_types = ship_data_plain_asteroid_keys()
a_type = random.choice(asteroid_types)
```
Now we will need to iterate over these points and spawn an asteroid at each point. To do this, we will be utilizing a for loop. For loops in MAST work the same way that they do in Python.
```python
for point in cluster_spawn_points:
    # Here we spawn the asteroid
    asteroid = terrain_spawn(point.x, point.y, point.z,None, "#,asteroid", a_type, "behav_asteroid")
```
Now, we're missing an 