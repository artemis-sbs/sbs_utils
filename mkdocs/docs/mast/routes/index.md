# Route labels
The {{ab.ac}} engine and the sbs_utils library deal with events. The engine calls into python providing an event. sbs_utils has a number of dispatchers that receive the event and dispatch that event to interested listeners.

Within {{ab.m}} that results in special labels being executed call route labels or routes fo short. A route label does not run until the event and conditions are met for it to run. When a script is compiled, these labels are discovered and automatically registered with the dispatchers to get called appropriately.

??? note "not all {{ab.pm}} routes exist"
    {{ab.m}} routes are generally created first. {{ab.pm}} lags behind in development and are not guaranteed to exist. Examples may include routes that have not been implemented and will be added overtime.

Routes general start with a double slash: e.g. //spawn 
Some routes are also used in the UI and include data used by the UI. These typically start with an @: e.g. @map.

In general // route labels related to sbs_utils event dispatchers, and @ route labels are discovered and used by other systems like the @map is discovered by the mission selection process and the label is scheduled when a map is selected to run.

Routes in {{ab.pm}} functions with a decorator. Decorators are python syntax and all decorator with the @.

With mast, routes also have a condition that is used to determine if the label should be run.

=== ":mast-icon: {{ab.m}}"

    ```
    //spawn if has_roles(SPAWNED_ID, "monster, typhon, classic")
    ```

This example the route label will get run when an object is spawned if that object has all the roles of "monster, typhon and classic."


## Spawn route labels

When object spawn script writers may want to add additional data or behavior to the object. The spawn route is also where AI logic is schedule to run.  

??? info "lifetime dispatcher" 
    The spawn route labels and other routes are connected to the sbs_utils lifetime dispatcher. The lifetime dispatcher dispatches events dealing with lifetime: spawn, deleted etc.

### Example spawn route
The following is the AI code for a typhon monster (as of version 1.0, located in LegendaryMissions)

[Code reference](https://github.com/artemis-sbs/LegendaryMissions/blob/main/ai/monster.mast)

The code will only run when a classic typhon monster is spawned. The code creates an AI loop when the monster looks for the closest thing to attack. If nothing is around it goes idle.

=== ":mast-icon: {{ab.m}}"
    ```
    //spawn if has_roles(SPAWNED_ID, "monster, typhon, classic")

    -- ai_loop
        ->END if  not object_exists(SPAWNED_ID)

        # The role "#" is an invisible e.g. admiral, operator
        _target = closest(SPAWNED_ID, broad_test_around(SPAWNED_ID, 6000,6000, 0xf0)-role("__terrain__")-role("monster")-role("#"))
        if _target is None:
            clear_target(SPAWNED_ID)
        else:
            #print("Typhon hunting")
            target(SPAWNED_ID, _target, True, 1.2)

        await delay_sim(seconds=5)

        jump ai_loop
    ```      

=== ":simple-python: {{ab.pm}}"

    ``` py
    @spawn
    def monster_ai():
        task = FrameContext.task
        SPAWNED_ID = task.get_variable("SPAWNED_ID")
        if not has_roles(SPAWNED_ID, "monster, typhon, classic"):
            yield PollResults.OK_FAIL
        if  not object_exists(SPAWNED_ID):
            yield POllResults.OK_END
        _target = closest(SPAWNED_ID, broad_test_around(
             SPAWNED_ID, 5000,5000, 0xf0)
             -role("__terrain__") -role("monster"))
        if _target is None:
            clear_target(SPAWNED_ID)
        else:
            #print("Typhon hunting")
            target(SPAWNED_ID, _target)
        yield AWAIT(delay_sim(seconds=5))
        yield jump(monster_ai)
    ```

