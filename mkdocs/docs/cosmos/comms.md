# Mast Communication syntax

The mast language provides labels an commands for processing communications.

This is a work in progress, currently it documenting the idea, and not what exists.


## Enabling comms for Agents


=== "Mast"
    ```
    //enable/comms if COMMS_SELECTED & "tsn, station"
    # Other code can be here to initialize data, add invemtory etc.
    # e.g. The station has three apples, three oranges
    #
    # Note this is a proposed simplified get_inventory_value(COMMS_SELECTED_ID, "Apples", 3)
    #
    COMMS_SELECTED["Apples"] =  3
    COMMS_SELECTED["Oranges"] = 3
    ```


## Providing Comms buttons

### Providing comms button to the root comms path

=== "Mast"
    ```
    //comms if COMMS_SELECTED_ID & "tsn, station"
    + "Buy" //comms/buy
    ```

### Providing comms button to the comms branch path
notice this branch the comms to the "buy" path

=== "Mast"
    ```
    //comms/buy if COMMS_SELECTED_ID & "tsn, station"
    + "Buy apple" if COMMS_SELECTED["Apples"] > 0:
        COMMS_SELECTED["Apples"] -= 1
    + "Buy orange" if COMMS_SELECTED["Apples"] > 0:
        COMMS_SELECTED["Oranges"] -= 1
    ```

### Providing choices of buttons

=== "Mast"
    ```
    //comms/buy if COMMS_SELECTED & "tsn, station"
    + if COMMS_SELECTED.inv["Apples"] > 0:
        % "Buy a tasty Apple"
        % "How about an Apple"
        COMMS_SELECTED["Apples"] -= 1
    + if COMMS_SELECTED["Apples"] > 0:
        % "Buy a sweet Orange"
        % "Need some vitamin C"
        COMMS_SELECTED["Oranges"] -= 1
    ```


### Providing choices of buttons based on reputation

=== "Mast"
    ```
    //comms/buy if COMMS_SELECTED & "tsn, station"
    + if COMMS_SELECTED.inv["Apples"] > 0:
        %+ "Free tasty Apple"
        %+ "How about a free Apple"
        %= "Buy a tasty Apple"
        %= "How about an Apple"
        %- "Buy a day old Apple"
        %- "How about half an Apple"
        . . .
    ```

### Providing choices of buttons based on reputation levels
Multiple reputation indicators create 'bands' 

=== "Mast"
    ```
    //comms/buy if COMMS_SELECTED & "tsn, station"
    + if COMMS_SELECTED.inv["Apples"] > 0:
        %+++ "Free tasty Apple"
        %+++ "How about a free Apple"
        %++ "Buy a tasty Apple"
        %++ "How about an Apple"
        %+ "Buy a day old Apple"
        %+ "How about half an Apple"
        . . .
    ```

### Providing choices of buttons based on reputation levels, weighting
Multiple reputation indicators create 'bands' 
Adding a weight number increases the chances

=== "Mast"
    ```
    //comms/buy if COMMS_SELECTED & "tsn, station"
    + if COMMS_SELECTED.inv["Apples"] > 0:
        %+++3 "Free tasty Apple"
        %+++ "How about a free Apple"
        %++3 "Buy a tasty Apple"
        %++ "How about an Apple"
        %+4 "Buy a day old Apple"
        %+ "How about half an Apple"
        . . .
    ```


### Providing choices of via data
What data is need tbd

=== "Mast"
    ```
    //comms/buy if COMMS_SELECTED & "tsn, station"
    + apple_options if COMMS_SELECTED["Apples"] > 0:
        COMMS_SELECTED["Apples"] -= 1
    + orange_options if COMMS_SELECTED["Apples"] > 0:
        COMMS_SELECTED["Oranges"] -= 1
    ```

### Providing via data with limits, and validity
What data is need tbd

You can provide a number to pick and the number of those that are valid
You can shuffle them once or every time

=== "Mast"
    ```
    //comms if COMMS_SELECTED & "tsn, station"
    + taunt_options choose once 3 validate 1 handle_taunt
    + complement_options choose once 3 validate 2 handle_complement
    + salutation_options choose always 3  handle_salutation
    ```


## comms messages

### Receive message

=== "Mast"
    ```
    <<[$info] Title
        " this is a multiline 
        " message
        " here
    ```

### Transmit message

=== "Mast"
    ```
    >>[$info] Title
        " this is a multiline 
        " message
        " here
    ```


### Speech Bubble message

=== "Mast"
    ```
    <>[$info] Title
        " this is a multiline 
        " message
        " here
    ```


### Message with options

=== "Mast"
    ```
    <<[$info] Title
        % option 1
        " message
        % option 2
        " here
    ```


### Message with options with rep

=== "Mast"
    ```
    <<[$info] Title
        %+ option good
        " message
        %= option neutral
        " here
        %- option neutral
        " here

    ```

### Message with options with rep level bands

=== "Mast"
    ```
    <<[$info] Title
        %+++ option good
        " message
        %++ option neutral
        " here
        %+ option neutral
        " here

    ```

### Message with options with rep level bands

=== "Mast"
    ```
    <<[$info] Title
        %+++3 option good most likely
        " message
        %+++3 option good most likely
        " message
        %+++2 option good more likely
        " message
        %+++2 option good more likely
        " message
        %+++ option good less likely
        " message
        %+++ option good less likely
        " message
        %++ option good etc.
        " message
        %++ option good etc.
        " message
        %+ option good etc.
        " message
        %+ option good etc.
        " message
    ```
