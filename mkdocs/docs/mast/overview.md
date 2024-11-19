
## {{ab.m}} execution flow 

The goal of {{ab.m}} is to enable non-programmers to be productive in creating interactive narratives.

The {{ab.m}} language is a programming language that simplifies many of the programming language concepts to help make writing interactive narratives easier as well as provide an easier-to-follow syntax.

The intent is to be approachable to non-programmers. It is not intended to be 'structured' programming language like C++ or Python. 

The flow of {{ab.m}} is similar to the original BASIC programming language. The code executes moving forward, it can branch by jumping to new locations (labels). This can be called 'unstructured' programming. {{ab.m}} was also influenced by choice script, Inkle's Ink, and others.



=== ":mast-icon: {{ab.m}}"

    ``` {{ab.m}}
    ========= start =======
    log("Hello, world")
    -> goodbye
    ====== not_here =======
    log("I get jumped over")
    ======= goodbye =======
    log("Goodbye")
    ```
=== "Output"

    ``` text
    Hello, world
    Goodbye
    ```


## {{ab.m}} and {{ab.pm}}

{{ab.m}} is a standalone language running inside of the python system provided by Artemis Cosmos.

{{ab.pm}} is python code that runs using the {{ab.m}} execution flow. This gives python programmers the benefits of {{ab.m}}'s simple flow while enabling greater access to the native python.


=== ":mast-icon: {{ab.m}}"

    ```
    ========= start =======
    log("Hello, world")
    -> goodbye
    ====== not_here =======
    log("I get jumped over")
    ======= goodbye =======
    log("Goodbye")
    ```

=== ":simple-python: {{ab.pm}}"

    ```
    @label()
    def start():
        print("Hello, world")
        yield jump(goodbye)

    @label()
    def not_here():
        print("I get jumped over")

    @label()
    def goodbye():
        print("Goodbye")
    ```

=== "Output"

    ```
        Hello, world
        Goodbye
    ```        



## {{ab.m}} and pausing the flow

{{ab.m}} is running as part of a game engine. The engine only gives {{ab.m}} a small amount of time to run. If {{ab.m}} ran unconditionally it would not allow the engine to run and stall the game. However, there are times a story cannot continue until conditions are met. e.g. A comms button is press, a science scan it started etc.

{{ab.m}} can "pause" execution and yield control back to the engine. The engine keeps calling {{ab.m}} and it yields until the condition is met then the flow can continue.

This example prints "Hello, world" and five seconds later it prints "Goodbye". During that five seconds the engine is able to run because {{ab.m}} yields control back since it cannot move forward.

This ability to yield control back to the engine is a reason that {{ab.m}} flow can be enable users to focus on the flow of the story and not how to get the programming language to deal with this.


=== ":mast-icon: {{ab.m}}"

    ```      
    ========= start =======
    log("Hello, world")
    delay_app(5)
    log("Goodbye")
    ```

=== ":simple-python: {{ab.pm}}"
    ```
    @label()
    def start():
        log("Hello, world")
        yield delay_app(5)
        log("Goodbye")
    ```
=== "Output"
    ```
    |    Hello, world
    |    Goodbye
    ```    

Yielding control is handled by {{ab.m}}. If there ever is a time you need to force a yield you can us the {{ab.m}} 'yeild' command. In {{ab.pm}} the python keyword yield is used, however you must specify how to yield by providing a PollResults.OK_RUN_AGAIN. There are other types of yields in {{ab.pm}}. This is not the time to detail those uses. 


=== ":mast-icon: {{ab.m}}"
    ```
    ========= start =======
    log("Hello, world")
    yield
    log("Goodbye")
    ```      

=== ":simple-python: {{ab.pm}}"

    ```
    @label()
    def start():
        log("Hello, world")
        yield PollResults.OK_RUN_AGAIN
        log("Goodbye")
    ```

=== "Output"

    ```
    |    Hello, world
    |    Goodbye
    ```

In future topics there will be other times descibed when {{ab.m}} yields. Typically this is when {{ab.m}} is waiting for something to occur. For example:

* time (e.g. the delay used in the examples)
* awaiting a choice to be made in the gui 
* awaiting a comms button to be selected
* awaiting a science scan 


## Sub plots aka Tasks
{{ab.m}} is MULTI Agent Story Telling so each agent has their own story or event stories.

{{ab.m}} allows multiple storylines to run in "parallel". 

{{ab.m}} in Artemis Cosmos is inherently a single thread of execution. These storylines do not run exactly in parallel, but you can run multiple things and make sure they run at the same time. These are called Tasks, and tasks can be scheduled so that multiple tasks can run on the same tick. A 'tick' is a very short piece of time where the game engine checks for input from the clients, calculates how everything in the game is supposed to move, processes damage and other internal logic, and then sends updated information to the clients. 

For example a Player Ship can run a Task for handling Comms messages, another for Science scan. This player ship could in fact run multiple tasks for handling comms with different sets of ships.

These tasks themselves act as small side stories, They run as long as needed.

In {{ab.m}} tasks are scheduled in {{ab.m}} with a parallel jump, and in {{ab.pm}} with a task_schedule

If you have programmed Artemis 2.x scripts, tasks are similar to the <event> tags. Unlike the <event> tags, task only run when needed. They are scheduled, and when they end they are unscheduled they can also be canceled.

=== ":mast-icon: {{ab.m}}"

    ```
    ===== start ====
    # Run another task
    await task_schedule(count_to_ten)
    log("done")

    ===== count_to_ten ======
    for x in range(10):
        log("{x}")
        yield
    ```

=== ":simple-python: {{ab.pm}}"

    ```
    @label()
    def start():
        yield AWAIT(task_schedule(count_to_ten))
        log("done")

    @label()
    def count_to_ten():
        for x in range(10):
            print(x)
            yield PollResults.OK_RUN_AGAIN
    ```

=== "Output"

    ```
    
    |    1
    |    2
    |    3
    |    4
    |    5
    |    6
    |    7
    |    8
    |    9
    |    10
    |    done
    ```


## Schedulers
{{ab.m}} and {{ab.pm}} run all the tasks using schedulers. This process is mostly hidden to the writer of {{ab.m}} and {{ab.pm}} code.

Tasks are run on 'Schedulers' and to put it simply for now, the Server and each Console has a scheduler. Additional schedulers can be created but typically the Server runs most of the tasks and the Consoles run a few tasks associated with that particular Console.

For example, the Server runs a scheduler that may have a task for presenting its User Interface/GUI, and maybe have other tasks to manage the world creation, handling comms, science etc. Consoles typically have a scheduler as a single task for handling the User Interface/GUI.

The more complex the script, the more tasks that will run. And if the complexity warrants it, more schedulers can be created. e.g. schedulers for each player ships etc.

When Artemis Cosmos calls the scripting engine, {{ab.m}}/{{ab.pm}} will run al the Schedulers and each scheduler runs all of its Tasks. 

As tasks are finished, they are removed. If a scheduler runs and no longer has tasks it is removed.


### XML Events vs label, and tasks
If you ever programmed Artemis 2.x, Tasks are similar to events.
XML is NOT supported, but used as examples for those familiar with Artemis 2.x scripting.
 
* XML events 
    * are always scheduled
    * and always run
    * never stop

* Tasks 
    * need to be scheduled or they don't run
    * They can end
    * They can be canceled

 
=== "XML"
    ``` xml
    <event name="do_some_thing">
    </event>
    ```
 
=== ":mast-icon: {{ab.m}}"   
    ```
    # To schedule the task
    task_schedule(do_some_thing)
    # To end a task
    ->END


    ==== do_some_thing ====
    log("Hello")
    ```             
        

=== ":simple-python: {{ab.pm}}"

    ```
    @label()
    def start():
        task_schedule(do_some_thing)

    @label()
    def do_some_thing():
        log("Hello")
    ```


    
        

### Setting data vs. XML Variable

With {{ab.m}} you can set data that is shared by the server, all client consoles and all tasks.
You can scope variables or pass data to a specific task. This allows tasks to be scheduled multiple times.
{{ab.pm}} has the added ability to scope data to a label since it is a function in python.

In contrast to an XML event, every variable was always shared. Also, events did not have scoped data. Events could not be reused. This meant to schedule events multiple times, you had to copy and paste the event and create new variables. 


=== "XML"
    
    ``` xml
    <event name="do_some_thing">
        <set_variable name="some_data" value="1"/> 
        <set_variable name="some_data_one" value="1"/> 
        <set_variable name="some_data_two" value="1"/> 
    </event>
    ```


=== ":mast-icon: {{ab.m}}"
    ```  
    # create shared data
    shared say_what = "Hello"
    local_data = "I'm different"

    # When run outputs Hello, World So Long Goodbye
    task_schedule(do_some_thing, {"passed_data": "World"})
    # When run outputs Hello, Cosmos So Long Goodbye
    task_schedule(do_some_thing, {"passed_data": "Cosmos"})

    ->END

    ==== do_some_thing ====
    # set a local variable 
    local_data = "Goodbye"

    log(f"{say_what}, {passed_data}")
    log(f"{local_data}")
    ```            
        

=== ":simple-python: {{ab.pm}}"
    ```
    @label()
    def start():
        # Shared data is added to the story
        set_shared_variable("say_what", "Hello")

        # When run out puts Hello, World So Long Goodbye
        task_schedule(do_some_thing, {"passed_data": "World"})
        # When run out puts Hello, Cosmos So Long Goodbye
        task_schedule(do_some_thing, {"passed_data": "Cosmos"})

    @label()
    def do_some_thing():
        say_what = get_shared_variable("say_what")
        # To share with the task
        # so it can be used in other labels run by this task
        set_variable("local_data", "So Long")
        task_local_data = get_variable("local_data")
        # a label is a function in python so it can also have
        # data local to the function/label
        label_data = "Goodbye"

        
        log(f"{say_what}, {passed_data}")
        log(f"{task_local_data}")
        log(f"{label_data}")
    ```

            
### Delaying things and XML Timers


There are times that a delay is needed before the next thing happens.
There are multiple reasons for this:

- pause between steps e.g. showing credits, spawning different waves of enemies
- delay something to not overwhelm the users, periodically report game state


Example one delaying credits.

=== "XML"
    ``` xml
        <start>
            . . .
            <set_timer name="credits_timer"/>
            <set_variable name="credits" comparator="EQUALS" value="0"/>
        </start>

        <event name="Credits 1">
            <if_timer_finished name="credits_timer"/>
            <if_variable name="credits" comparator="EQUALS" value="0"/>
            <big_message title="This is the first page of credits" subtitle2=""/>
            <set_variable name="credits" value="1"/>
        </event>
        <event name="Credits 2">
            <if_timer_finished name="credits_timer"/>
            <if_variable name="credits" comparator="EQUALS" value="1"/>
            <big_message title="This is the second page of credits" subtitle2=""/>
            <set_variable name="credits" value="2"/>
        </event>
        <event name="Credits 3">
            <if_timer_finished name="credits_timer"/>
            <if_variable name="credits" comparator="EQUALS" value="2"/>
            <big_message title="This is the third page of credits" subtitle2=""/>
            <set_variable name="credits" value="999"/>
        </event>
    ```

=== ":mast-icon: {{ab.m}}"
    ```
    
    ==== show_credits ====
    
    """ This is the first page of credits"""
    await gui(timeout=delay_sim(10))
    """ This is the second page of credits"""
    await gui(timeout=delay_sim(10))
    """ This is the third page of credits"""
    await gui(timeout=delay_sim(10))
    ```
                  
        

=== ":simple-python: {{ab.pm}}"
    ```
    @label()
    def start():
        gui_text("this is the first page of credits")
        yield AWAIT(gui(timeout=delay_sim(10)))
        gui_text("this is the second page of credits")
        yield AWAIT(gui(timeout=delay_sim(10)))
        gui_text("this is the third page of credits")
        yield AWAIT(gui(timeout=delay_sim(10)))
    ```

Another use is to spawn enemy waves.
The XML for this would be very verbose.
        
=== "xml"                    
    ```
    <Skipping/>
    ```
        
=== ":mast-icon: {{ab.m}}"
    ```
    ==== spawn_wave ====
    enemyTypeNameList = ["kralien_dreadnaught","kralien_battleship","skaraan_defiler","cargo_ship","arvonian_carrier","torgoth_behemoth"]
    enemy_prefix = "KLMNQ"
    

    # this gets a radom span location just outside the view of the sctor 
    spawn_points = scatter_sphere(int(enemy_count), 0,0,0, 6000, 6000+250*enemy_count, ring=True)

    for v in spawn_points:
        r_type = random.choice(enemyTypeNameList)
        r_name = f"{random.choice(enemy_prefix)}_{enemy}"
        spawn_data = npc_spawn(v.x, v.y, v.z, r_name, "RAIDER", r_type, "behav_npcship")
        raider = spawn_data.py_object
        set_face(raider.id, random_kralien())
        add_role(raider.id, "Raider")
        enemy = enemy + 1
    

    delay_sim(minutes=8)
    ```            
        

=== ":simple-python: {{ab.pm}}"
    ```
    @label()
    def spawn_wave():
        enemyTypeNameList = ["kralien_dreadnaught","kralien_battleship","skaraan_defiler","cargo_ship","arvonian_carrier","torgoth_behemoth"]
        enemy_prefix = "KLMNQ"

        # this gets a radom span location just outside the view of the sector 
        spawn_points = scatter_sphere(int(enemy_count), 0,0,0, 6000, 6000+250*enemy_count, ring=True)

        for v in spawn_points:
            r_type = random.choice(enemyTypeNameList)
            r_name = f"{random.choice(enemy_prefix)}_{enemy}"
            spawn_data = npc_spawn(v.x, v.y, v.z, r_name, "RAIDER", r_type, "behav_npcship")
            raider = spawn_data.py_object
            set_face(raider.id, random_kralien())
            add_role(raider.id, "Raider")
            enemy = enemy + 1
        yield AWAIT(delay_sim(minutes=8))
    ```





