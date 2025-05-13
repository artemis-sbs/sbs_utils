# MAST Tutorial
A tutorial describing how to write a simple mission that utilizes many of the tools MAST has to offer.
## Tutorial Goals
### General Goals
Upon completion of this tutorial, you will have learned to:
1. Create a new mission from a template
2. Update the name and description of your mission
3. Understand what a 'label' is in MAST
3. Set an ambiance with a skybox and music
4. Spawn player ships
5. Utilize roles
5. Spawn terrain
6. Spawn enemies
7. Add science scans
8. Detect damage and destruction
9. Build comms buttons

### Specific Goals
For this tutorial, we are writing a mission about finding and recovering a lost treasure.  
The players will need to fight off scavengers while they search.  
They will need to scan asteroids to find the treasure.  
They will need to shoot at the asteroid to remove debris from the treasure.  
They will need to collect the treasure by giving instructions to a specialist team retrieve it.

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
`@map` is a label, which we will get into more later. It tells the game that this is a mission, and what its name is.
In our case we want to change the name of the map from "Hello Cosmos" to our chosen mission name - "Treasure Hunt". The `/first_map` part of the label is used internally by the MAST interpreter, but isn't relevant to us at the moment. You may choose to change this to whatever you want, but it cannot have spaces in it.
